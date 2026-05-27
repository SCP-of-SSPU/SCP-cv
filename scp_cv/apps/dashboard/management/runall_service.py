#!/user/bin/env python
# -*- coding: UTF-8 -*-
"""
runall 后台服务启动辅助函数。
封装 Windows 脱离当前终端的子进程创建参数。
@Project : SCP-cv
@File : runall_service.py
@Author : Qintsg
@Date : 2026-05-12
"""

from __future__ import annotations

import os
import subprocess
from datetime import datetime
from pathlib import Path


def launch_runall_service(
    argv: list[str], project_dir: Path, log_dir: Path
) -> tuple[int, Path]:
    """
    以后台服务方式重新启动当前 runall 命令，并从参数中移除 --service。
    :param argv: 当前 Python 进程参数
    :param project_dir: 仓库根目录
    :param log_dir: 日志目录
    :return: 后台进程 PID 和日志路径
    """
    import sys

    service_command = [sys.executable, *argv]
    service_command = _remove_service_flag(service_command)
    service_log_path = _service_log_path(log_dir)
    service_env = os.environ.copy()
    service_env.setdefault("PYTHONUTF8", "1")
    service_env.setdefault("PYTHONIOENCODING", "utf-8")
    service_log = service_log_path.open("ab")
    try:
        service_process = subprocess.Popen(
            service_command,
            cwd=str(project_dir),
            env=service_env,
            stdin=subprocess.DEVNULL,
            stdout=service_log,
            stderr=subprocess.STDOUT,
            close_fds=True,
            creationflags=_detached_creation_flags(),
        )
    finally:
        service_log.close()
    return int(service_process.pid), service_log_path


def _service_log_path(log_dir: Path, started_at: datetime | None = None) -> Path:
    """
    返回后台 runall 服务启动日志路径。
    :param log_dir: 日志根目录
    :param started_at: 启动时间；未传时使用当前时间
    :return: 后台服务日志路径
    """
    timestamp = (started_at or datetime.now()).strftime("%Y%m%d-%H%M%S-%f")
    service_log_dir = log_dir / "runall" / "service"
    service_log_dir.mkdir(parents=True, exist_ok=True)
    return service_log_dir / f"runall-service-{timestamp}.log"


def _remove_service_flag(command_args: list[str]) -> list[str]:
    """
    移除 runall 命令中的 --service 标记，避免后台进程递归拉起自身。
    :param command_args: 待启动的命令参数
    :return: 已移除 --service 的命令参数
    """
    return [command_arg for command_arg in command_args if command_arg != "--service"]


def _detached_creation_flags() -> int:
    """
    返回 Windows 后台进程创建标志；非 Windows 平台返回 0。
    :return: subprocess creationflags 参数
    """
    if os.name != "nt":
        return 0
    return (
        subprocess.CREATE_NEW_PROCESS_GROUP
        | subprocess.DETACHED_PROCESS
        | subprocess.CREATE_NO_WINDOW
    )
