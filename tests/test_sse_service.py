#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
SSE 状态推送服务测试。
覆盖事件流生成器的锁释放行为，避免慢客户端阻塞状态发布。
@Project : SCP-cv
@File : test_sse_service.py
@Author : Qintsg
@Date : 2026-04-24
'''
from __future__ import annotations

import json
from collections.abc import Generator

import pytest

from scp_cv.apps.playback.models import (
    ControlCommandStatus,
    ControlCommandTarget,
    PlaybackState,
)
from scp_cv.services import sse as sse_service
from scp_cv.services.command_queue import claim_next, enqueue, finish
from scp_cv.services.playback import update_playback_progress


@pytest.fixture(autouse=True)
def reset_event_bus() -> Generator[None, None, None]:
    """
    重置模块级事件总线，保证测试之间没有序列号和事件残留。
    :return: pytest 生成器 fixture
    """
    with sse_service._event_condition:
        sse_service._latest_event_data.clear()
        sse_service._event_sequence = 0
    yield
    with sse_service._event_condition:
        sse_service._latest_event_data.clear()
        sse_service._event_sequence = 0


@pytest.mark.django_db
def test_event_stream_releases_lock_after_yield() -> None:
    """生成器产出消息后不应继续持有事件锁。"""
    sse_service.publish_event("playback_state", {"window_id": 1})

    stream_generator = sse_service.event_stream(0)
    first_message = next(stream_generator)
    assert "event: playback_state" in first_message

    lock_acquired = sse_service._event_lock.acquire(blocking=False)
    try:
        assert lock_acquired is True
    finally:
        if lock_acquired:
            sse_service._event_lock.release()
        stream_generator.close()


@pytest.mark.django_db
def test_published_playback_state_uses_complete_command_projection() -> None:
    """即时 playback_state 事件应与轮询帧共享完整命令状态合同。"""
    first = enqueue(ControlCommandTarget.WINDOW_1, "open")
    second = enqueue(ControlCommandTarget.WINDOW_2, "open")
    sse_service.publish_event("playback_state", {
        "commands": [{"id": first.pk, "status": "pending"}],
    })

    stream_generator = sse_service.event_stream(0)
    first_message = next(stream_generator)
    payload = json.loads(next(
        line.removeprefix("data: ")
        for line in first_message.splitlines()
        if line.startswith("data: ")
    ))

    assert [command["id"] for command in payload["commands"]] == [
        first.pk,
        second.pk,
    ]
    stream_generator.close()


@pytest.mark.django_db
def test_event_stream_polls_database_state_without_publish() -> None:
    """播放器进程仅写数据库时，SSE 仍应推送最新播放快照。"""
    update_playback_progress(
        1,
        playback_state=PlaybackState.PLAYING,
        current_slide=2,
        total_slides=5,
    )

    stream_generator = sse_service.event_stream(0)
    first_message = next(stream_generator)

    assert "event: playback_state" in first_message
    assert '"current_slide": 2' in first_message
    assert '"total_slides": 5' in first_message
    stream_generator.close()


@pytest.mark.django_db
def test_event_stream_exposes_finished_control_command() -> None:
    """SSE 首帧应保留已快速失败命令的 ID、终态与错误信息。"""
    queued = enqueue(ControlCommandTarget.WINDOW_1, "open")
    claimed = claim_next(ControlCommandTarget.WINDOW_1, "player-1")
    assert claimed is not None
    assert finish(
        claimed.pk,
        "player-1",
        status=ControlCommandStatus.FAILED,
        error_message="PowerPoint 放映启动失败",
    ) is True

    stream_generator = sse_service.event_stream(0)
    first_message = next(stream_generator)

    assert f'"id": {queued.pk}' in first_message
    assert '"status": "failed"' in first_message
    assert '"error_message": "PowerPoint 放映启动失败"' in first_message
    stream_generator.close()


@pytest.mark.django_db
def test_event_stream_keeps_terminal_command_visible_after_newer_backlog() -> None:
    """旧 ID 刚进入终态时，不得被更新的待执行命令挤出 SSE 状态帧。"""
    queued = enqueue(ControlCommandTarget.WINDOW_1, "open")
    claimed = claim_next(ControlCommandTarget.WINDOW_1, "player-1")
    assert claimed is not None
    for _ in range(101):
        enqueue(ControlCommandTarget.WINDOW_1, "next")
    assert finish(
        claimed.pk,
        "player-1",
        status=ControlCommandStatus.FAILED,
        error_message="旧命令执行失败",
    ) is True

    stream_generator = sse_service.event_stream(0)
    first_message = next(stream_generator)
    payload = json.loads(next(
        line.removeprefix("data: ")
        for line in first_message.splitlines()
        if line.startswith("data: ")
    ))

    command = next(item for item in payload["commands"] if item["id"] == queued.pk)
    assert command["status"] == ControlCommandStatus.FAILED
    assert command["error_message"] == "旧命令执行失败"
    stream_generator.close()


@pytest.mark.django_db
def test_event_stream_polls_command_state_between_process_events() -> None:
    """持续的进程内事件不得饿死播放器仅写数据库的命令终态。"""
    queued = enqueue(ControlCommandTarget.WINDOW_1, "open")
    claimed = claim_next(ControlCommandTarget.WINDOW_1, "player-1")
    assert claimed is not None
    sse_service.publish_event("resource_updated", {"source_id": 1})
    stream_generator = sse_service.event_stream(0)
    assert "event: resource_updated" in next(stream_generator)

    assert finish(
        claimed.pk,
        "player-1",
        status=ControlCommandStatus.FAILED,
        error_message="播放器进程执行失败",
    ) is True
    sse_service.publish_event("resource_updated", {"source_id": 2})

    terminal_message = next(stream_generator)
    assert "event: playback_state" in terminal_message
    payload = json.loads(next(
        line.removeprefix("data: ")
        for line in terminal_message.splitlines()
        if line.startswith("data: ")
    ))
    command = next(item for item in payload["commands"] if item["id"] == queued.pk)
    assert command["status"] == ControlCommandStatus.FAILED
    stream_generator.close()
