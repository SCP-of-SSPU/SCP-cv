#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
run_player 管理命令测试，覆盖启动器事件循环与播放器主循环的衔接。
@Project : SCP-cv
@File : test_run_player_command.py
@Author : Qintsg
@Date : 2026-05-27
'''
from __future__ import annotations

import sys
from types import ModuleType

from pytest import MonkeyPatch

from scp_cv.apps.dashboard.management.commands.run_player import Command


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


def test_collect_launcher_result_explicitly_quits_launcher_loop(
    monkeypatch: MonkeyPatch,
) -> None:
    """
    启动器完成选择后应显式退出第一段事件循环，并恢复 Qt 原设置。
    :param monkeypatch: pytest monkeypatch fixture
    :return: None
    """
    launch_result = object()
    qt_app = _QtAppStub()
    fake_module = _build_fake_launcher_module("launch", launch_result)
    monkeypatch.setitem(sys.modules, "scp_cv.player.launcher_gui", fake_module)

    collected_result = Command()._collect_launcher_result(qt_app, dev_mode=False)

    assert collected_result is launch_result
    assert qt_app.exec_calls == 1
    assert qt_app.quit_calls == 1
    assert qt_app.quit_on_last_window_values == [False, True]


def test_collect_launcher_result_returns_none_when_cancelled(
    monkeypatch: MonkeyPatch,
) -> None:
    """
    用户取消启动器时应退出启动器事件循环并返回 None。
    :param monkeypatch: pytest monkeypatch fixture
    :return: None
    """
    qt_app = _QtAppStub()
    fake_module = _build_fake_launcher_module("cancel", object())
    monkeypatch.setitem(sys.modules, "scp_cv.player.launcher_gui", fake_module)

    collected_result = Command()._collect_launcher_result(qt_app, dev_mode=True)

    assert collected_result is None
    assert qt_app.exec_calls == 1
    assert qt_app.quit_calls == 1
    assert qt_app.quit_on_last_window_values == [False, True]


def _build_fake_launcher_module(action: str, launch_result: object) -> ModuleType:
    """
    构造可控制启动或取消行为的 launcher_gui 替身模块。
    :param action: launch 或 cancel
    :param launch_result: 启动时发出的结果对象
    :return: 替身模块
    """
    fake_module = ModuleType("scp_cv.player.launcher_gui")

    class LauncherWindowStub:
        """最小启动器窗口替身。"""

        def __init__(self, debug_mode: bool = False) -> None:
            """
            初始化信号。
            :param debug_mode: 是否开发模式
            :return: None
            """
            self.debug_mode = debug_mode
            self.launch_requested = _SignalStub()
            self.launch_cancelled = _SignalStub()

        def show(self) -> None:
            """
            模拟用户在启动器中完成操作。
            :return: None
            """
            if action == "launch":
                self.launch_requested.emit(launch_result)
            else:
                self.launch_cancelled.emit()

    fake_module.LauncherResult = object
    fake_module.LauncherWindow = LauncherWindowStub
    return fake_module
