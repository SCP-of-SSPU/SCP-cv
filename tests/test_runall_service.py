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

    service_pid, service_log_path = launch_runall_service(
        ["manage.py", "runall", "--service", "--headless"],
        project_dir=tmp_path,
        log_dir=tmp_path,
    )

    assert service_pid == 4321
    assert service_log_path == tmp_path / "runall-service.log"
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
