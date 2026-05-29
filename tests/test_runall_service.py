#!/user/bin/env python
# -*- coding: UTF-8 -*-
"""
runall 后台服务启动测试。
覆盖 --service 二次拉起、终端脱离和日志重定向参数。
@Project : SCP-cv
@File : test_runall_service.py
@Author : Qintsg
@Date : 2026-05-12
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from scp_cv.apps.dashboard.management import runall_service
from scp_cv.apps.dashboard.management.runall_service import (
    _command_starts_player,
    _remove_service_flag,
    launch_runall_service,
)


def test_remove_service_flag_keeps_original_manage_command() -> None:
    """
    后台服务二次启动应只移除 --service，不应破坏 manage.py runall 命令。
    :return: None
    """
    command_args = [
        "C:/Python/python.exe",
        "manage.py",
        "runall",
        "--service",
        "--headless",
    ]

    assert _remove_service_flag(command_args) == [
        "C:/Python/python.exe",
        "manage.py",
        "runall",
        "--headless",
    ]


def test_command_starts_player_respects_skip_player() -> None:
    """
    只有会启动 PySide 播放器的 runall 服务才需要交互桌面。
    :return: None
    """
    assert _command_starts_player(["manage.py", "runall", "--headless"]) is True
    assert _command_starts_player(["manage.py", "runall", "--skip-player"]) is False


def test_launch_runall_service_detaches_and_writes_log(
    monkeypatch: Any, tmp_path: Path
) -> None:
    """
    --service 应以后台子进程重启 runall，并把输出重定向到日志文件。
    :param monkeypatch: pytest monkeypatch fixture
    :param tmp_path: pytest 临时目录 fixture
    :return: None
    """
    captured_popen: dict[str, Any] = {}

    class FakeServiceProcess:
        """后台服务进程替身。"""

        pid = 4321

    def fake_popen(command_args: list[str], **kwargs: Any) -> FakeServiceProcess:
        """
        捕获后台服务启动参数，避免测试真正拉起 runall。
        :param command_args: Popen 命令参数
        :param kwargs: Popen 关键字参数
        :return: 进程替身
        """
        captured_popen["command_args"] = command_args
        captured_popen["kwargs"] = kwargs
        return FakeServiceProcess()

    monkeypatch.setattr(runall_service.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(runall_service, "should_launch_via_interactive_task", lambda: False)
    monkeypatch.setattr(
        runall_service.subprocess, "DETACHED_PROCESS", 0x8, raising=False
    )
    monkeypatch.setattr(
        runall_service.subprocess,
        "CREATE_NEW_PROCESS_GROUP",
        0x200,
        raising=False,
    )
    monkeypatch.setattr(
        runall_service.subprocess, "CREATE_NO_WINDOW", 0x8000000, raising=False
    )
    monkeypatch.setattr("scp_cv.apps.dashboard.management.runall_service.os.name", "nt")
    monkeypatch.setattr("sys.executable", "C:/Python/python.exe")

    service_launch = launch_runall_service(
        ["manage.py", "runall", "--service", "--headless"],
        project_dir=tmp_path,
        log_dir=tmp_path,
    )

    assert service_launch.pid == 4321
    service_log_path = service_launch.log_path
    assert service_log_path.parent == tmp_path / "runall" / "service"
    assert service_log_path.name.startswith("runall-service-")
    assert service_log_path.name.endswith(".log")
    assert captured_popen["command_args"] == [
        "C:/Python/python.exe",
        "manage.py",
        "runall",
        "--headless",
    ]
    assert captured_popen["kwargs"]["cwd"] == str(tmp_path)
    assert captured_popen["kwargs"]["stdin"] is runall_service.subprocess.DEVNULL
    assert captured_popen["kwargs"]["stderr"] is runall_service.subprocess.STDOUT
    assert captured_popen["kwargs"]["close_fds"] is True
    assert captured_popen["kwargs"]["creationflags"] == 0x8000208
    assert captured_popen["kwargs"]["stdout"].closed is True


def test_launch_runall_service_uses_interactive_task_from_service_session(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    """
    Windows 服务/SSH 会话下 --service 应转交登录用户交互桌面启动。
    :param monkeypatch: pytest monkeypatch fixture
    :param tmp_path: pytest 临时目录 fixture
    :return: None
    """
    captured_run: dict[str, Any] = {}

    def fake_run(command_args: list[str], **kwargs: Any) -> None:
        """
        捕获计划任务注册命令，避免测试真正创建任务。
        :param command_args: subprocess.run 命令参数
        :param kwargs: subprocess.run 关键字参数
        :return: None
        """
        captured_run["command_args"] = command_args
        captured_run["kwargs"] = kwargs

    monkeypatch.setattr(runall_service, "should_launch_via_interactive_task", lambda: True)
    monkeypatch.setattr(runall_service.subprocess, "run", fake_run)
    monkeypatch.setattr("sys.executable", "C:/Python/python.exe")
    monkeypatch.setenv("USERNAME", "admin")

    service_launch = launch_runall_service(
        ["manage.py", "runall", "--service", "--headless"],
        project_dir=tmp_path,
        log_dir=tmp_path,
    )

    assert service_launch.pid is None
    assert service_launch.task_name == "SCP-cv-runall-service"
    assert service_launch.log_path.parent == tmp_path / "runall" / "service"
    assert service_launch.log_path.with_suffix(".cmd").is_file()
    launcher_content = service_launch.log_path.with_suffix(".cmd").read_text(encoding="utf-8")
    assert "C:/Python/python.exe manage.py runall --headless" in launcher_content
    assert str(service_launch.log_path) in launcher_content
    assert captured_run["command_args"][:3] == [
        "powershell.exe",
        "-NoProfile",
        "-NonInteractive",
    ]
    assert "New-ScheduledTaskPrincipal" in captured_run["command_args"][-1]
    assert "-LogonType Interactive" in captured_run["command_args"][-1]
    assert "-UserId 'admin'" in captured_run["command_args"][-1]
    assert captured_run["kwargs"]["cwd"] == str(tmp_path)
    assert captured_run["kwargs"]["check"] is True
