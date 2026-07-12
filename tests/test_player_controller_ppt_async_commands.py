#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
播放器 PPT 异步命令确认与取消测试。
@Project : SCP-cv
@File : test_player_controller_ppt_async_commands.py
@Author : Qintsg
@Date : 2026-07-11
'''
from __future__ import annotations

import pytest

from scp_cv.apps.playback.models import (
    ControlCommandStatus,
    ControlCommandTarget,
    PlaybackCommand,
)
from scp_cv.services.command_queue import CommandInput, enqueue, enqueue_batch
from scp_cv.services.playback import get_or_create_session
from tests.player_controller_ppt_async_test_support import (
    _AsyncPptAdapter,
    _make_controller,
)


@pytest.mark.django_db
def test_queued_ppt_open_is_confirmed_only_after_broker_callback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """持久化 OPEN 必须保持 executing，直到异步 PPT 回调实际完成。"""
    adapter = _AsyncPptAdapter(finish_immediately=False)
    controller, _window, _states, errors = _make_controller(monkeypatch, adapter)
    get_or_create_session(1)
    queued = enqueue(
        ControlCommandTarget.WINDOW_1,
        PlaybackCommand.OPEN,
        {
            "source_id": 7,
            "source_type": "ppt",
            "uri": "C:/demo/slow.pptx",
            "autoplay": True,
        },
    )

    controller._check_and_dispatch_command(1)
    queued.refresh_from_db()
    assert queued.status == ControlCommandStatus.EXECUTING

    assert adapter.on_finished is not None
    adapter.on_finished(None)

    queued.refresh_from_db()
    assert queued.status == ControlCommandStatus.SUCCEEDED
    assert errors == []


@pytest.mark.django_db
def test_persisted_close_cancels_async_open_before_result_is_accepted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """持久化 CLOSE 取代在途 OPEN 后，应先释放打开结果且不得写入 playing。"""
    adapter = _AsyncPptAdapter(finish_immediately=False)
    controller, _window, states, errors = _make_controller(monkeypatch, adapter)
    get_or_create_session(1)
    opening = enqueue(
        ControlCommandTarget.WINDOW_1,
        PlaybackCommand.OPEN,
        {
            "source_id": 7,
            "source_type": "ppt",
            "uri": "C:/demo/slow.pptx",
            "autoplay": True,
        },
    )
    controller._check_and_dispatch_command(1)
    closing = enqueue_batch(
        ControlCommandTarget.WINDOW_1,
        [CommandInput(PlaybackCommand.CLOSE)],
        cancel_pending=True,
    )[0]

    assert adapter.on_finished is not None
    adapter.on_finished(None)

    opening.refresh_from_db()
    closing.refresh_from_db()
    assert opening.status == ControlCommandStatus.CANCELLED
    assert adapter.closed is True
    assert controller._adapters == {}
    assert states == [(1, "loading")]
    assert errors == []
    assert closing.status == ControlCommandStatus.PENDING

    controller._check_and_dispatch_command(1)

    closing.refresh_from_db()
    assert closing.status == ControlCommandStatus.SUCCEEDED


@pytest.mark.django_db
def test_queued_ppt_open_failure_is_persisted_on_callback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Broker 异步打开失败必须把同一条持久化指令终结为 failed。"""
    adapter = _AsyncPptAdapter(finish_immediately=False)
    controller, _window, _states, errors = _make_controller(monkeypatch, adapter)
    get_or_create_session(1)
    queued = enqueue(
        ControlCommandTarget.WINDOW_1,
        PlaybackCommand.OPEN,
        {"source_type": "ppt", "uri": "C:/demo/broken.pptx"},
    )

    controller._check_and_dispatch_command(1)
    assert adapter.on_finished is not None
    adapter.on_finished(RuntimeError("PowerPoint Run rejected"))

    queued.refresh_from_db()
    assert queued.status == ControlCommandStatus.FAILED
    assert queued.error_message == "PowerPoint Run rejected"
    assert errors == [(1, "PowerPoint Run rejected")]
