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

from scp_cv.player.controller import PlayerController


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
