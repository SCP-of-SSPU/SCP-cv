#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
run_player 管理命令测试共用 Qt 替身。
@Project : SCP-cv
@File : run_player_test_support.py
@Author : Qintsg
@Date : 2026-07-11
'''
from __future__ import annotations


class _SignalStub:
    """最小 Qt Signal 替身。"""

    def __init__(self) -> None:
        """
        初始化回调列表。
        :return: None
        """
        self._callbacks: list[object] = []

    def connect(self, callback: object) -> None:
        """
        记录连接的回调。
        :param callback: 回调对象
        :return: None
        """
        self._callbacks.append(callback)

    def emit(self, *args: object) -> None:
        """
        触发所有已连接回调。
        :param args: 回调参数
        :return: None
        """
        for callback in list(self._callbacks):
            callback(*args)


class _QtAppStub:
    """最小 QApplication 替身。"""

    def __init__(self) -> None:
        """
        初始化事件循环状态。
        :return: None
        """
        self._quit_on_last_window_closed = True
        self.quit_calls = 0
        self.exec_calls = 0
        self.quit_on_last_window_values: list[bool] = []

    def quitOnLastWindowClosed(self) -> bool:
        """
        返回是否最后窗口关闭时退出。
        :return: 当前设置
        """
        return self._quit_on_last_window_closed

    def setQuitOnLastWindowClosed(self, enabled: bool) -> None:
        """
        设置最后窗口关闭退出行为。
        :param enabled: 是否启用
        :return: None
        """
        self._quit_on_last_window_closed = enabled
        self.quit_on_last_window_values.append(enabled)

    def quit(self) -> None:
        """
        记录退出请求。
        :return: None
        """
        self.quit_calls += 1

    def exec(self) -> int:
        """
        记录事件循环启动。
        :return: 退出码
        """
        self.exec_calls += 1
        return 0
