#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
播放器控制器测试，覆盖轮询线程与 Qt 主线程的状态上报边界。
@Project : SCP-cv
@File : test_player_controller.py
@Author : Qintsg
@Date : 2026-04-30
'''
from __future__ import annotations

from unittest.mock import patch

import pytest

from scp_cv.apps.playback.models import MediaSource, PlaybackState
from scp_cv.player.adapters.base import AdapterState
from scp_cv.player.controller import PlayerController
from scp_cv.services.playback import open_source


class _StateAdapter:
    """返回固定状态的 adapter 替身，用于验证状态写回保护。"""

    def __init__(self, adapter_state: AdapterState) -> None:
        """
        初始化 adapter 替身。
        :param adapter_state: get_state 要返回的状态快照
        :return: None
        """
        self.is_open = True
        self.adapter_state = adapter_state
        self.read_count = 0

    def get_state(self) -> AdapterState:
        """
        返回固定状态并记录读取次数。
        :return: 预置的 adapter 状态
        """
        self.read_count += 1
        return self.adapter_state


class _SingleLoopController(PlayerController):
    """只执行一轮轮询的控制器替身，用于验证线程边界调度。"""

    def __init__(self) -> None:
        """
        初始化测试控制器状态。
        :return: None
        """
        super().__init__()
        self.checked_windows: list[int] = []
        self.report_requested = False

    @property
    def registered_window_ids(self) -> list[int]:
        """返回固定窗口，避免依赖真实播放器窗口注册。"""
        return [1]

    def _check_and_dispatch_command(self, window_id: int) -> None:
        """
        记录被轮询的窗口。
        :param window_id: 窗口编号
        :return: None
        """
        self.checked_windows.append(window_id)

    def _request_adapter_state_report(self) -> None:
        """记录状态上报请求，并结束轮询。"""
        self.report_requested = True
        self._poll_running = False

    def _report_all_adapter_states(self) -> None:
        """轮询线程不应直接调用真实状态读取。"""
        raise AssertionError("adapter state must be reported through the Qt signal")


def test_poll_loop_requests_state_report_instead_of_reading_adapter_directly() -> None:
    """后台轮询应只发起状态上报请求，避免跨线程访问 PPT COM。"""
    controller = _SingleLoopController()
    controller._poll_running = True

    with patch("scp_cv.player.controller.time.sleep", return_value=None):
        controller._poll_loop(interval_seconds=0)

    assert controller.checked_windows == [1]
    assert controller.report_requested is True


@pytest.mark.django_db
def test_report_skips_stale_adapter_after_source_change(
    media_source_ppt: MediaSource,
    media_source_video: MediaSource,
) -> None:
    """切源后旧 adapter 的延迟错误状态不应覆盖新会话。"""
    open_source(1, media_source_ppt.pk)
    open_source(1, media_source_video.pk)

    controller = PlayerController()
    adapter = _StateAdapter(AdapterState(playback_state=PlaybackState.ERROR))
    controller._adapters[1] = adapter
    controller._adapter_source_ids[1] = media_source_ppt.pk

    controller._report_all_adapter_states()

    session = media_source_video.playback_sessions.get(window_id=1)
    assert session.playback_state == PlaybackState.LOADING
    assert adapter.read_count == 0
