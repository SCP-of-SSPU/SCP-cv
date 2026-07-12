#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PowerPoint Broker 的 Windows 命名、认证和就绪等待辅助。
@Project : SCP-cv
@File : runtime.py
@Author : Qintsg
@Date : 2026-07-11
'''
from __future__ import annotations

import base64
import ctypes
import getpass
import json
import os
import re
import secrets
import time
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from scp_cv.player.ppt_broker.contracts import BrokerHealth

if TYPE_CHECKING:
    from scp_cv.player.ppt_broker.transport import PptBrokerClient

_ERROR_ALREADY_EXISTS = 183


class BrokerAlreadyRunningError(RuntimeError):
    """当前用户 Session 已有 PowerPoint Broker。"""


def runtime_directory() -> Path:
    """返回不进入仓库的用户级 Broker 运行目录。"""
    local_app_data = os.environ.get("LOCALAPPDATA")
    base = Path(local_app_data) if local_app_data else Path.home() / "AppData" / "Local"
    return base / "SCP-cv" / "runtime"


def authkey_path() -> Path:
    """返回 AF_PIPE 认证密钥文件路径。"""
    return runtime_directory() / "ppt-broker.auth"


def metadata_path() -> Path:
    """返回 Broker PID/代次诊断元数据路径。"""
    return runtime_directory() / "ppt-broker.json"


def default_pipe_address() -> str:
    """按 Windows 用户和交互 Session 隔离默认命名管道。"""
    user = re.sub(r"[^a-zA-Z0-9_.-]", "-", getpass.getuser()) or "user"
    return rf"\\.\pipe\scp-cv-ppt-broker-{user}-{_windows_session_id()}"


def load_or_create_authkey(path: Path | None = None) -> bytes:
    """加载认证密钥；首次启动时以独占创建避免竞争覆盖。"""
    selected_path = path or authkey_path()
    selected_path.parent.mkdir(parents=True, exist_ok=True)
    if selected_path.exists():
        return _read_authkey(selected_path)
    authkey = secrets.token_bytes(32)
    encoded = base64.urlsafe_b64encode(authkey)
    try:
        descriptor = os.open(
            selected_path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o600,
        )
    except FileExistsError:
        return _read_authkey(selected_path)
    with os.fdopen(descriptor, "wb") as auth_file:
        auth_file.write(encoded)
    return authkey


def wait_for_broker(
    address: str | None = None,
    authkey: bytes | None = None,
    *,
    timeout_seconds: float = 10.0,
) -> BrokerHealth:
    """轮询到 Broker 就绪，超时统一抛 TimeoutError。"""
    from scp_cv.player.ppt_broker.transport import PptBrokerClient

    selected_address = address or default_pipe_address()
    selected_authkey = authkey or load_or_create_authkey()
    deadline = time.monotonic() + max(0.1, timeout_seconds)
    last_error: BaseException | None = None
    while time.monotonic() < deadline:
        remaining = max(0.1, deadline - time.monotonic())
        client = PptBrokerClient(
            selected_address,
            selected_authkey,
            timeout_seconds=min(0.5, remaining),
        )
        try:
            health = client.health()
            if health.ready:
                return health
        except Exception as health_error:
            last_error = health_error
        time.sleep(min(0.05, max(0.0, deadline - time.monotonic())))
    raise TimeoutError(
        f"等待 PowerPoint Broker 就绪超时：address={selected_address}, "
        f"timeout={timeout_seconds:.1f}s, last_error={last_error}"
    ) from last_error


def connect_or_start(
    start: Callable[[], object],
    address: str | None = None,
    authkey: bytes | None = None,
    *,
    timeout_seconds: float = 15.0,
) -> "PptBrokerClient":
    """复用健康 Broker；否则启动一个实例并保留启动对象所有权。"""
    from scp_cv.player.ppt_broker.transport import PptBrokerClient

    selected_address = address or default_pipe_address()
    selected_authkey = authkey or load_or_create_authkey()
    client = PptBrokerClient(
        selected_address,
        selected_authkey,
        timeout_seconds=min(1.0, max(0.1, timeout_seconds)),
    )
    try:
        if client.health().ready:
            return client
    except Exception:
        pass
    started_process = start()
    health = wait_for_broker(
        selected_address,
        selected_authkey,
        timeout_seconds=timeout_seconds,
    )
    client.timeout_seconds = max(0.1, timeout_seconds)
    # 两个播放器可能同时通过首次健康检查并各自尝试启动 Broker。
    # 只有健康 PID 属于本次 Popen（Windows venv 启动器本身或经命令行、
    # 创建时间验证的子进程）才能取得关闭所有权；互斥量竞争失败的一方
    # 必须复用赢家，退出时不得关闭赢家的 Broker。
    client.started_process = (
        started_process
        if _started_process_owns_broker(started_process, health.pid)
        else None
    )
    return client


def _started_process_owns_broker(
    started_process: object,
    broker_pid: int,
) -> bool:
    """验证健康响应 PID 是否确属本次 Broker 启动进程。"""
    started_pid = int(getattr(started_process, "pid", 0) or 0)
    if started_pid <= 0 or broker_pid <= 0:
        return False
    if started_pid == broker_pid:
        return True

    poll = getattr(started_process, "poll", None)
    try:
        if callable(poll) and poll() is not None:
            return False
        import psutil

        launcher_process = psutil.Process(started_pid)
        broker_process = psutil.Process(broker_pid)
        descendant_ids = {
            int(child.pid)
            for child in launcher_process.children(recursive=True)
        }
        if broker_pid not in descendant_ids:
            return False
        if broker_process.create_time() < launcher_process.create_time():
            return False
        command_parts = [
            str(command_part).strip().casefold()
            for command_part in broker_process.cmdline()
        ]
    except (OSError, ValueError, psutil.Error):
        return False

    has_manage_py = any(Path(command_part).name == "manage.py" for command_part in command_parts)
    return has_manage_py and "run_ppt_broker" in command_parts


class BrokerInstanceLock:
    """基于 Windows Local 命名互斥量的 Broker 单实例锁。"""

    def __init__(self, address: str) -> None:
        # Local 命名空间已按 Windows Session 隔离；传输地址不得改变实例身份。
        del address
        self._name = r"Local\SCP-CV-PPT-Broker"
        self._handle: int | None = None

    def __enter__(self) -> BrokerInstanceLock:
        if os.name != "nt":
            return self
        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        kernel32.CreateMutexW.restype = ctypes.c_void_p
        handle = kernel32.CreateMutexW(None, False, self._name)
        if not handle:
            raise ctypes.WinError()
        if kernel32.GetLastError() == _ERROR_ALREADY_EXISTS:
            kernel32.CloseHandle(handle)
            raise BrokerAlreadyRunningError(
                f"PowerPoint Broker 已在当前 Windows Session 运行：{self._name}"
            )
        self._handle = int(handle)
        return self

    def __exit__(self, *_exc_info: object) -> None:
        if self._handle is None or os.name != "nt":
            return
        ctypes.windll.kernel32.CloseHandle(self._handle)  # type: ignore[attr-defined]
        self._handle = None


def write_runtime_metadata(address: str, health: BrokerHealth) -> None:
    """写入不含认证密钥的 Broker 诊断元数据。"""
    target = metadata_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(
            {
                "address": address,
                "generation": health.generation,
                "pid": health.pid,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    temporary.replace(target)


def clear_runtime_metadata(generation: str) -> None:
    """仅删除仍属于当前 Broker 代次的元数据。"""
    target = metadata_path()
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, ValueError, TypeError):
        return
    if str(payload.get("generation", "")) != generation:
        return
    try:
        target.unlink()
    except FileNotFoundError:
        pass


def _windows_session_id() -> int:
    if os.name != "nt":
        return 0
    session_id = ctypes.c_uint32()
    succeeded = ctypes.windll.kernel32.ProcessIdToSessionId(  # type: ignore[attr-defined]
        os.getpid(),
        ctypes.byref(session_id),
    )
    return int(session_id.value) if succeeded else 0


def _decode_authkey(encoded: str, path: Path) -> bytes:
    try:
        authkey = base64.urlsafe_b64decode(encoded.strip().encode("ascii"))
    except Exception as decode_error:
        raise RuntimeError(_invalid_authkey_message(path, "内容无法解码")) from decode_error
    if len(authkey) < 16:
        raise RuntimeError(_invalid_authkey_message(path, "密钥长度不足"))
    return authkey


def _read_authkey(path: Path) -> bytes:
    try:
        encoded = path.read_text(encoding="ascii")
    except (OSError, UnicodeError) as read_error:
        raise RuntimeError(_invalid_authkey_message(path, "文件无法读取")) from read_error
    return _decode_authkey(encoded, path)


def _invalid_authkey_message(path: Path, reason: str) -> str:
    return (
        f"PowerPoint Broker 认证密钥文件无效（{reason}）：{path}。"
        "请先停止 runall、播放器和 PowerPoint Broker，删除该认证文件，"
        "再重新启动以生成新密钥。"
    )


__all__ = [
    "BrokerAlreadyRunningError",
    "BrokerInstanceLock",
    "authkey_path",
    "clear_runtime_metadata",
    "connect_or_start",
    "default_pipe_address",
    "load_or_create_authkey",
    "metadata_path",
    "runtime_directory",
    "wait_for_broker",
    "write_runtime_metadata",
]
