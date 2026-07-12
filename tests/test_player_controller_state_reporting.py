#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
播放器控制器适配器状态上报测试。
@Project : SCP-cv
@File : test_player_controller_state_reporting.py
@Author : Qintsg
@Date : 2026-07-12
'''
from __future__ import annotations

import pytest

from scp_cv.apps.playback.models import PlaybackState, SourceType
from scp_cv.player.adapters.base import AdapterState
from scp_cv.player.controller import PlayerController
from scp_cv.services.playback import get_or_create_session


class _FailingStateAdapter:
    """模拟 PowerPoint Broker 断开后的状态读取失败。"""

    is_open = True

    def get_state(self) -> AdapterState:
        """抛出稳定的 Broker 断开错误。"""
        raise ConnectionError("PowerPoint Broker pipe disconnected")


@pytest.mark.django_db
def test_ppt_state_read_failure_marks_session_error() -> None:
    """PowerPoint Broker 状态读取失败时活动 PPT 会话必须进入 error。"""
    session = get_or_create_session(1)
    controller = PlayerController()
    controller._adapters[1] = _FailingStateAdapter()  # type: ignore[assignment]
    controller._adapter_source_types[1] = SourceType.PPT

    controller._report_all_adapter_states()

    session.refresh_from_db()
    assert session.playback_state == PlaybackState.ERROR
    assert "PowerPoint Broker" in session.error_message
    assert "pipe disconnected" in session.error_message


@pytest.mark.django_db
def test_non_ppt_state_read_failure_remains_transient() -> None:
    """普通媒体的单次状态读取失败仍只告警，不应污染会话状态。"""
    session = get_or_create_session(1)
    controller = PlayerController()
    controller._adapters[1] = _FailingStateAdapter()  # type: ignore[assignment]
    controller._adapter_source_types[1] = SourceType.VIDEO

    controller._report_all_adapter_states()

    session.refresh_from_db()
    assert session.playback_state == PlaybackState.IDLE
    assert session.error_message == ""
