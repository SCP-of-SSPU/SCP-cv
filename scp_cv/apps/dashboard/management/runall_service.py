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

import ctypes
import getpass
import os
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class RunallServiceLaunch:
    """runall 后台启动结果。"""

    pid: int | None
    log_path: Path
    task_name: str = ""


def launch_runall_service(
    argv: list[str], project_dir: Path, log_dir: Path
) -> RunallServiceLaunch:
    """
    以后台服务方式重新启动当前 runall 命令，并从参数中移除 --service。
    :param argv: 当前 Python 进程参数
    :param project_dir: 仓库根目录
    :param log_dir: 日志目录
    :return: 后台启动结果
    """
    import sys

    service_command = [sys.executable, *argv]
    service_command = _remove_service_flag(service_command)
    service_log_path = _service_log_path(log_dir)
    if _command_starts_player(service_command) and should_launch_via_interactive_task():
        task_name = _launch_interactive_task(service_command, project_dir, service_log_path)
        return RunallServiceLaunch(pid=None, log_path=service_log_path, task_name=task_name)

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
    return RunallServiceLaunch(pid=int(service_process.pid), log_path=service_log_path)


def should_launch_via_interactive_task() -> bool:
    """
    判断 Windows 后台启动是否需要转交给登录用户交互桌面。
    :return: True 表示当前进程不在活动控制台会话
    """
    if os.name != "nt":
        return False
    current_session_id = current_process_session_id()
    active_session_id = active_console_session_id()
    if current_session_id is None or active_session_id is None:
        return False
    return current_session_id != active_session_id


def current_process_has_active_desktop() -> bool:
    """
    当前进程是否运行在 Windows 活动控制台桌面。
    :return: True 表示可直接枚举并使用控制台显示器
    """
    return not should_launch_via_interactive_task()


def current_process_session_id() -> int | None:
    """
    读取当前进程所属 Windows Session ID。
    :return: Session ID；非 Windows 或读取失败返回 None
    """
    if os.name != "nt":
        return None
    session_id = ctypes.c_ulong()
    success = ctypes.windll.kernel32.ProcessIdToSessionId(  # type: ignore[attr-defined]
        os.getpid(),
        ctypes.byref(session_id),
    )
    if not success:
        return None
    return int(session_id.value)


def active_console_session_id() -> int | None:
    """
    读取当前 Windows 活动控制台 Session ID。
    :return: Session ID；不存在或非 Windows 返回 None
    """
    if os.name != "nt":
        return None
    session_id = ctypes.windll.kernel32.WTSGetActiveConsoleSessionId()  # type: ignore[attr-defined]
    if int(session_id) == 0xFFFFFFFF:
        return None
    return int(session_id)


def _launch_interactive_task(
    service_command: list[str],
    project_dir: Path,
    service_log_path: Path,
) -> str:
    """
    通过 Windows 计划任务在登录用户交互桌面启动真实 runall。
    :param service_command: 已移除 --service 的 runall 命令
    :param project_dir: 仓库根目录
    :param service_log_path: 后台日志路径
    :return: 计划任务名称
    """
    task_name = "SCP-cv-runall-service"
    launcher_path = service_log_path.with_suffix(".cmd")
    launcher_path.write_text(
        _interactive_launcher_script(service_command, project_dir, service_log_path),
        encoding="utf-8",
    )
    powershell_script = _interactive_task_script(task_name, launcher_path)
    subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", powershell_script],
        cwd=str(project_dir),
        check=True,
    )
    return task_name


def _interactive_launcher_script(
    service_command: list[str],
    project_dir: Path,
    service_log_path: Path,
) -> str:
    """
    构造交互式计划任务实际执行的 cmd 脚本内容。
    :param service_command: runall 命令参数
    :param project_dir: 仓库根目录
    :param service_log_path: 日志路径
    :return: cmd 脚本文本
    """
    command_line = subprocess.list2cmdline(service_command)
    return "\n".join([
        "@echo off",
        "set CI=true",
        "set PYTHONUTF8=1",
        "set PYTHONIOENCODING=utf-8",
        "set npm_config_yes=true",
        "set PNPM_CONFIG_CONFIRM=true",
        f'cd /d "{project_dir}"',
        f'{command_line} >> "{service_log_path}" 2>&1',
        "",
    ])


def _interactive_task_script(task_name: str, launcher_path: Path) -> str:
    """
    构造注册并启动交互式计划任务的 PowerShell 脚本。
    :param task_name: 计划任务名称
    :param launcher_path: cmd 启动脚本路径
    :return: PowerShell 脚本文本
    """
    username = os.environ.get("USERNAME") or getpass.getuser()
    launcher_arg = f'/c ""{launcher_path}""'
    return "\n".join([
        "$ErrorActionPreference = 'Stop'",
        f"$taskName = {_ps_single_quoted(task_name)}",
        "Unregister-ScheduledTask "
        "-TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue",
        "$action = New-ScheduledTaskAction -Execute 'cmd.exe' "
        f"-Argument {_ps_single_quoted(launcher_arg)}",
        "$principal = New-ScheduledTaskPrincipal "
        f"-UserId {_ps_single_quoted(username)} -LogonType Interactive -RunLevel Limited",
        "Register-ScheduledTask "
        "-TaskName $taskName -Action $action -Principal $principal -Force | Out-Null",
        "Start-ScheduledTask -TaskName $taskName",
    ])


def _ps_single_quoted(value: str) -> str:
    """
    转义 PowerShell 单引号字符串。
    :param value: 原始字符串
    :return: PowerShell 单引号字符串
    """
    return "'" + value.replace("'", "''") + "'"


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


def _command_starts_player(command_args: list[str]) -> bool:
    """
    判断 runall 命令是否会启动 PySide 播放器。
    :param command_args: 已移除 --service 的命令参数
    :return: True 表示需要控制台桌面
    """
    return "--skip-player" not in command_args


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
