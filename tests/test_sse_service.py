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

from collections.abc import Generator

import pytest

from scp_cv.apps.playback.models import PlaybackState
from scp_cv.services import sse as sse_service
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
