#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
播放器 PowerPoint 页面媒体命令错误传播测试。
@Project : SCP-cv
@File : test_player_controller_ppt_media_errors.py
@Author : Qintsg
@Date : 2026-07-12
'''
from __future__ import annotations

import pytest

from scp_cv.apps.playback.models import (
    ControlCommandStatus,
    ControlCommandTarget,
    PlaybackCommand,
    PlaybackState,
)
from scp_cv.player.adapters.ppt_broker import PptBrokerSourceAdapter
from scp_cv.player.controller import PlayerController
from scp_cv.player.ppt_broker import PptBrokerEngine
from scp_cv.player.ppt_broker.powerpoint import PowerPointComBackend
from scp_cv.services.command_queue import enqueue
from scp_cv.services.playback import get_or_create_session
from tests.ppt_broker_powerpoint_test_support import AnimatedPowerPoint, WindowPort


class _FailingMediaPlayer:
    """模拟已找到、但执行播放时失败的 PowerPoint Player。"""

    def __init__(self) -> None:
        self.play_calls = 0

    def Play(self) -> None:
        """抛出必须传播到持久命令终态的 COM 执行错误。"""
        self.play_calls += 1
        raise RuntimeError("PowerPoint media Play failed")


@pytest.mark.django_db
def test_ppt_media_com_failure_marks_command_and_session_error() -> None:
    """页面媒体真实执行失败必须穿过 Broker 和 Adapter 写入 failed。"""
    application = AnimatedPowerPoint()
    broker = PptBrokerEngine(
        PowerPointComBackend(
            application_factory=lambda: application,
            process_id_reader=lambda _application: 4242,
            window_port=WindowPort(),
            file_exists=lambda _uri: True,
            retry_delays=(),
        )
    )
    adapter = PptBrokerSourceAdapter(
        broker=broker,
        window_id=1,
        owner_prefix="player-media-error",
    )
    try:
        adapter.open("C:/slides/media-demo.pptx", window_handle=1001)
        presentation = application.Presentations.opened[0]
        media_player = _FailingMediaPlayer()

        def resolve_player(shape_id: int) -> object:
            assert shape_id == 501
            return media_player

        presentation.view.Player = resolve_player  # type: ignore[attr-defined]
        session = get_or_create_session(1)
        queued = enqueue(
            ControlCommandTarget.WINDOW_1,
            PlaybackCommand.PPT_MEDIA,
            {
                "media_id": "501",
                "media_action": PlaybackCommand.PLAY,
                "media_index": 0,
            },
        )
        controller = PlayerController(enable_background_audio=False)
        controller._adapters[1] = adapter
        controller._adapter_source_types[1] = "ppt"

        controller._check_and_dispatch_command(1)

        queued.refresh_from_db()
        session.refresh_from_db()
        assert media_player.play_calls == 1
        assert queued.status == ControlCommandStatus.FAILED
        assert queued.error_message == "PowerPoint media Play failed"
        assert session.playback_state == PlaybackState.ERROR
        assert session.error_message == "PowerPoint media Play failed"
    finally:
        adapter.close()
        broker.shutdown()


@pytest.mark.django_db
def test_missing_optional_ppt_media_remains_a_successful_noop() -> None:
    """当前页没有目标媒体时应保持既有 no-op 语义。"""
    application = AnimatedPowerPoint()
    broker = PptBrokerEngine(
        PowerPointComBackend(
            application_factory=lambda: application,
            process_id_reader=lambda _application: 4242,
            window_port=WindowPort(),
            file_exists=lambda _uri: True,
            retry_delays=(),
        )
    )
    adapter = PptBrokerSourceAdapter(
        broker=broker,
        window_id=1,
        owner_prefix="player-missing-media",
    )
    try:
        adapter.open("C:/slides/no-media-demo.pptx", window_handle=1001)
        presentation = application.Presentations.opened[0]

        def missing_player(_shape_id: int) -> object:
            raise LookupError("media shape is absent")

        presentation.view.Player = missing_player  # type: ignore[attr-defined]
        session = get_or_create_session(1)
        queued = enqueue(
            ControlCommandTarget.WINDOW_1,
            PlaybackCommand.PPT_MEDIA,
            {
                "media_id": "501",
                "media_action": PlaybackCommand.PLAY,
                "media_index": 0,
            },
        )
        controller = PlayerController(enable_background_audio=False)
        controller._adapters[1] = adapter
        controller._adapter_source_types[1] = "ppt"

        controller._check_and_dispatch_command(1)

        queued.refresh_from_db()
        session.refresh_from_db()
        assert queued.status == ControlCommandStatus.SUCCEEDED
        assert session.playback_state != PlaybackState.ERROR
        assert session.error_message == ""
    finally:
        adapter.close()
        broker.shutdown()
