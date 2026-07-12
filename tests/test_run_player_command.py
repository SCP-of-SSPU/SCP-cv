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
from scp_cv.player.gpu_detector import GPUInfo
from scp_cv.player.launcher_gui import LauncherResult
from scp_cv.services.display import DisplayTarget
from tests.run_player_test_support import _QtAppStub, _SignalStub


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




def test_run_isolated_window_players_spawns_one_process_per_window(
    monkeypatch: MonkeyPatch,
) -> None:
    """
    多窗口启动结果应被拆分成独立 run_player 进程。
    :param monkeypatch: pytest monkeypatch fixture
    :return: None
    """
    spawned_commands: list[list[str]] = []
    terminated: list[bool] = []

    class _ProcessStub:
        """记录独立播放器子进程的测试替身。"""

        pid = 100

        def __init__(self, command_args: list[str]) -> None:
            self.command_args = command_args

        def poll(self) -> int | None:
            return None

        def terminate(self) -> None:
            terminated.append(True)

        def wait(self, timeout: int) -> int:
            """
            模拟等待进程退出。
            :param timeout: 等待秒数
            :return: 退出码
            """
            return 0

    def fake_popen(command_args: list[str]) -> _ProcessStub:
        """
        记录 Popen 命令。
        :param command_args: 子进程命令
        :return: 子进程替身
        """
        spawned_commands.append(command_args)
        return _ProcessStub(command_args)

    displays = {
        window_id: DisplayTarget(
            index=window_id,
            name=f"显示器 {window_id}",
            width=1920,
            height=1080,
            x=0,
            y=0,
            is_primary=window_id == 1,
        )
        for window_id in (1, 2)
    }
    launch_result = LauncherResult(
        window_assignments=displays,
        selected_gpu=GPUInfo(index=2, name="NVIDIA", vendor="nvidia"),
    )
    command = Command()
    monkeypatch.setattr(
        "scp_cv.apps.dashboard.management.commands.run_player.subprocess.Popen",
        fake_popen,
    )
    monkeypatch.setattr(
        command,
        "_monitor_isolated_players",
        lambda processes, _shutdown: None,
    )

    command._run_isolated_window_players(
        launch_result,
        dev_mode=False,
        poll_interval=0.25,
        shutdown_requested={"value": False},
    )

    assert len(spawned_commands) == 2
    assert spawned_commands[0][-7:] == [
        "--headless",
        "--only-window",
        "1",
        "--window1",
        "1",
        "--gpu",
        "2",
    ]
    assert spawned_commands[1][-8:] == [
        "--headless",
        "--only-window",
        "2",
        "--window2",
        "2",
        "--gpu",
        "2",
        "--disable-background-audio",
    ]
    assert terminated == [True, True]


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
