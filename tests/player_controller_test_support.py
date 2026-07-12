#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
播放器控制器轮询测试共用替身。
@Project : SCP-cv
@File : player_controller_test_support.py
@Author : Qintsg
@Date : 2026-07-11
'''
from __future__ import annotations

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
        self.checked_background_audio = False
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

    def _check_and_dispatch_background_audio_command(self) -> None:
        """记录背景音频轮询，避免该线程边界测试访问数据库。"""
        self.checked_background_audio = True

    def _request_adapter_state_report(self) -> None:
        """记录状态上报请求，并结束轮询。"""
        self.report_requested = True
        self._poll_running = False

    def _report_all_adapter_states(self) -> None:
        """轮询线程不应直接调用真实状态读取。"""
        raise AssertionError("adapter state must be reported through the Qt signal")
