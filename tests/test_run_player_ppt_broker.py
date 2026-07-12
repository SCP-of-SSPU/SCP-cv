#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
run_player PowerPoint Broker 连接与子进程生命周期测试。
@Project : SCP-cv
@File : test_run_player_ppt_broker.py
@Author : Qintsg
@Date : 2026-07-11
'''
from __future__ import annotations

import sys
from types import ModuleType

import pytest
from django.core.management.base import CommandError
from pytest import MonkeyPatch

from scp_cv.apps.dashboard.management.commands.run_player import Command
from scp_cv.player.launcher_gui import LauncherResult
from scp_cv.services.display import DisplayTarget
from tests.run_player_test_support import _QtAppStub


def test_independent_run_player_starts_and_owns_ppt_broker(
    monkeypatch: MonkeyPatch,
) -> None:
    """
    独立 run_player 应通过 runtime helper 拉起 Broker 并记录进程所有权。
    :param monkeypatch: pytest monkeypatch fixture
    :return: None
    """
    spawned_commands: list[list[str]] = []

    class _ProcessStub:
        """独立 Broker 子进程替身。"""

        def __init__(self, command_args: list[str]) -> None:
            self.command_args = command_args

    class _ClientStub:
        """runtime helper 返回的 Broker 客户端替身。"""

        def __init__(self, started_process: _ProcessStub) -> None:
            self.started_process = started_process

    def fake_popen(command_args: list[str]) -> _ProcessStub:
        spawned_commands.append(command_args)
        return _ProcessStub(command_args)

    def fake_connect_or_start(start: object, **_kwargs: object) -> _ClientStub:
        process = start()  # type: ignore[operator]
        return _ClientStub(process)

    fake_broker_module = ModuleType("scp_cv.player.ppt_broker")
    fake_broker_module.connect_or_start = fake_connect_or_start  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "scp_cv.player.ppt_broker", fake_broker_module)
    monkeypatch.setattr(
        "scp_cv.apps.dashboard.management.commands.run_player.subprocess.Popen",
        fake_popen,
    )
    command = Command()

    command._prepare_ppt_broker(only_window_id=0)

    assert spawned_commands == [
        [sys.executable, "manage.py", "run_ppt_broker"],
    ]
    assert command._owned_ppt_broker_process is not None


def test_only_window_requires_existing_ppt_broker(
    monkeypatch: MonkeyPatch,
) -> None:
    """
    --only-window 不得自行拉起 Broker，缺失时应给出明确启动指引。
    :param monkeypatch: pytest monkeypatch fixture
    :return: None
    """

    def fake_wait_for_broker(**_kwargs: object) -> None:
        raise TimeoutError("pipe unavailable")

    fake_broker_module = ModuleType("scp_cv.player.ppt_broker")
    fake_broker_module.wait_for_broker = fake_wait_for_broker  # type: ignore[attr-defined]
    fake_broker_module.PptBrokerClient = object  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "scp_cv.player.ppt_broker", fake_broker_module)

    with pytest.raises(CommandError) as raised_error:
        Command()._prepare_ppt_broker(only_window_id=2)

    error_message = str(raised_error.value)
    assert "--only-window 2" in error_message
    assert "run_ppt_broker" in error_message


def test_only_window_keeps_client_for_existing_ppt_broker(
    monkeypatch: MonkeyPatch,
) -> None:
    """--only-window 连接成功后必须把 Broker 客户端注入播放器控制器。"""

    class _HealthStub:
        """Broker 健康快照替身。"""

        pid = 4321
        generation = "generation-a"

    class _ClientStub:
        """既有 Broker 客户端替身。"""

    client = _ClientStub()
    fake_broker_module = ModuleType("scp_cv.player.ppt_broker")
    fake_broker_module.wait_for_broker = lambda **_kwargs: _HealthStub()  # type: ignore[attr-defined]
    fake_broker_module.PptBrokerClient = lambda: client  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "scp_cv.player.ppt_broker", fake_broker_module)
    command = Command()

    command._prepare_ppt_broker(only_window_id=3)

    assert command._ppt_broker_client is client
    assert command._owned_ppt_broker_process is None


def test_handle_prepares_broker_before_starting_window(
    monkeypatch: MonkeyPatch,
) -> None:
    """
    run_player 入口应在创建播放窗口前完成 Broker 准备。
    :param monkeypatch: pytest monkeypatch fixture
    :return: None
    """
    events: list[str] = []

    class _ApplicationStub(_QtAppStub):
        """支持 QApplication.instance 的入口测试替身。"""

        _instance: "_ApplicationStub | None" = None

        def __init__(self, _args: object = None) -> None:
            super().__init__()
            self.__class__._instance = self

        @classmethod
        def instance(cls) -> "_ApplicationStub | None":
            return cls._instance

    class _LaunchResultStub:
        """单窗口 headless 启动结果。"""

        window_assignments = {2: object()}
        selected_gpu = None

    fake_qt_widgets = ModuleType("PySide6.QtWidgets")
    fake_qt_widgets.QApplication = _ApplicationStub  # type: ignore[attr-defined]
    fake_launcher_module = ModuleType("scp_cv.player.launcher_gui")
    fake_launcher_module.LauncherResult = object  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "PySide6.QtWidgets", fake_qt_widgets)
    monkeypatch.setitem(
        sys.modules,
        "scp_cv.player.launcher_gui",
        fake_launcher_module,
    )
    monkeypatch.setattr(
        "scp_cv.apps.dashboard.management.commands.run_player.signal.signal",
        lambda *_args: None,
    )
    command = Command()
    monkeypatch.setattr(
        command,
        "_build_headless_result",
        lambda _options: _LaunchResultStub(),
    )
    monkeypatch.setattr(
        command,
        "_prepare_ppt_broker",
        lambda only_window_id: events.append(f"broker:{only_window_id}"),
    )
    monkeypatch.setattr(
        command,
        "_start_player",
        lambda *_args: events.append("player"),
    )
    monkeypatch.setattr(
        command,
        "_cleanup_owned_ppt_broker",
        lambda: events.append("cleanup"),
    )

    command.handle(
        dev=False,
        poll_interval=0.2,
        headless=True,
        only_window=2,
        disable_background_audio=False,
        gpu=-1,
    )

    assert events == ["broker:2", "player", "cleanup"]


def test_run_player_shuts_down_only_the_broker_it_started() -> None:
    """
    run_player 退出时应关闭自己拉起的 Broker，并等待子进程结束。
    :return: None
    """
    shutdown_calls: list[bool] = []
    wait_timeouts: list[int] = []

    class _ClientStub:
        """记录 shutdown 的 Broker 客户端替身。"""

        def shutdown(self) -> None:
            shutdown_calls.append(True)

    class _ProcessStub:
        """在 wait 后退出的 Broker 进程替身。"""

        def __init__(self) -> None:
            self._exit_code: int | None = None

        def poll(self) -> int | None:
            return self._exit_code

        def wait(self, timeout: int) -> int:
            wait_timeouts.append(timeout)
            self._exit_code = 0
            return 0

    command = Command()
    command._ppt_broker_client = _ClientStub()
    command._owned_ppt_broker_process = _ProcessStub()

    command._cleanup_owned_ppt_broker()

    assert shutdown_calls == [True]
    assert wait_timeouts == [5]
    assert command._ppt_broker_client is None
    assert command._owned_ppt_broker_process is None


def test_start_player_injects_prepared_broker_client(
    monkeypatch: MonkeyPatch,
) -> None:
    """播放器控制器必须复用已准备的 Broker 客户端，不得创建本地 COM worker。"""
    broker = object()
    controller_options: list[dict[str, object]] = []
    controller_events: list[str] = []

    class _ControllerStub:
        """记录控制器构造参数和生命周期。"""

        def __init__(self, **options: object) -> None:
            controller_options.append(options)

        def set_window_closed_callback(self, _callback: object) -> None:
            controller_events.append("close-callback")

        def register_window(self, _window_id: int, _window: object) -> None:
            controller_events.append("register")

        def apply_current_layout(self) -> None:
            controller_events.append("layout")

        def preheat_sources(self) -> None:
            controller_events.append("preheat")

        def start_polling(self, interval_seconds: float) -> None:
            controller_events.append(f"start:{interval_seconds}")

        def stop_polling(self) -> None:
            controller_events.append("stop")

    class _WindowStub:
        """最小播放窗口替身。"""

        def __init__(self, window_id: int, debug_mode: bool) -> None:
            self.window_id = window_id
            self.debug_mode = debug_mode

        def position_on_display(self, _rect: object) -> None:
            controller_events.append("position")

    class _SessionStub:
        """记录显示目标持久化。"""

        target_display_label = ""

        def save(self) -> None:
            controller_events.append("save-session")

    fake_controller_module = ModuleType("scp_cv.player.controller")
    fake_controller_module.PlayerController = _ControllerStub  # type: ignore[attr-defined]
    fake_window_module = ModuleType("scp_cv.player.window")
    fake_window_module.PlayerWindow = _WindowStub  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "scp_cv.player.controller", fake_controller_module)
    monkeypatch.setitem(sys.modules, "scp_cv.player.window", fake_window_module)
    monkeypatch.setattr(
        "scp_cv.services.playback.get_or_create_session",
        lambda _window_id: _SessionStub(),
    )
    monkeypatch.setattr(
        "scp_cv.apps.dashboard.management.commands.run_player.sys.exit",
        lambda code: (_ for _ in ()).throw(SystemExit(code)),
    )
    launch_result = LauncherResult(
        window_assignments={
            1: DisplayTarget(
                index=1,
                name="显示器 1",
                width=1920,
                height=1080,
                x=0,
                y=0,
                is_primary=True,
            )
        },
        selected_gpu=None,
    )
    command = Command()
    command._ppt_broker_client = broker
    qt_app = _QtAppStub()

    with pytest.raises(SystemExit, match="0"):
        command._start_player(
            qt_app,
            launch_result,
            dev_mode=False,
            poll_interval=0.25,
        )

    assert controller_options == [
        {
            "enable_background_audio": True,
            "ppt_broker": broker,
        }
    ]
    assert controller_events == [
        "close-callback",
        "register",
        "save-session",
        "position",
        "layout",
        "preheat",
        "start:0.25",
        "stop",
    ]
