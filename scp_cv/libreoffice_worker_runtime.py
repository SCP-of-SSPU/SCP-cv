#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
LibreOffice worker 会话、进程和 UNO 运行时辅助函数。
@Project : SCP-cv
@File : libreoffice_worker_runtime.py
@Author : Qintsg
@Date : 2026-05-29
'''
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any


class WorkerError(RuntimeError):
    """LibreOffice worker 执行失败。"""


class LibreOfficeSession:
    """LibreOffice 隔离进程和 UNO 上下文。"""

    def __init__(
        self,
        process: subprocess.Popen[bytes],
        profile_dir: Path,
        context: Any,
        desktop: Any,
        uno: Any,
    ) -> None:
        """
        初始化 LibreOffice 会话。
        :param process: soffice 子进程
        :param profile_dir: 独立 UserInstallation 目录
        :param context: 远端 ComponentContext
        :param desktop: com.sun.star.frame.Desktop 实例
        :param uno: pyuno 模块
        :return: None
        """
        self.process = process
        self.profile_dir = profile_dir
        self.context = context
        self.desktop = desktop
        self.uno = uno

    def property_value(self, name: str, value: object) -> Any:
        """
        创建 UNO PropertyValue。
        :param name: 属性名
        :param value: 属性值
        :return: com.sun.star.beans.PropertyValue
        """
        property_value = self.uno.createUnoStruct("com.sun.star.beans.PropertyValue")
        property_value.Name = name
        property_value.Value = value
        return property_value

    def path_to_file_url(self, path: Path) -> str:
        """
        将系统路径转换为 UNO file URL。
        :param path: 本地路径
        :return: file URL
        """
        return self.uno.systemPathToFileUrl(str(path.resolve()))

    def close(self) -> None:
        """
        终止 LibreOffice 进程并清理隔离 profile。
        :return: None
        """
        try:
            self.desktop.terminate()
        except Exception:
            pass
        _terminate_process(self.process)
        shutil.rmtree(self.profile_dir, ignore_errors=True)


def _start_session(headless: bool) -> LibreOfficeSession:
    """
    启动隔离 LibreOffice 会话并连接 UNO pipe。
    :param headless: 是否以 headless 模式启动
    :return: LibreOffice 会话对象
    """
    uno = _import_uno()
    executable = _resolve_soffice_executable()
    pipe_name = f"scp_cv_{os.getpid()}_{uuid.uuid4().hex}"
    profile_dir = Path(tempfile.mkdtemp(prefix="scp-cv-lo-"))
    profile_url = uno.systemPathToFileUrl(str(profile_dir.resolve()))
    accept_arg = f"--accept=pipe,name={pipe_name};urp;StarOffice.ComponentContext"
    args = [
        str(executable),
        "--norestore",
        "--nodefault",
        "--nolockcheck",
        "--nofirststartwizard",
        "--nologo",
        f"-env:UserInstallation={profile_url}",
        accept_arg,
    ]
    if headless:
        args.insert(1, "--headless")
    try:
        process = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError as start_error:
        shutil.rmtree(profile_dir, ignore_errors=True)
        raise WorkerError(f"LibreOffice 启动失败：{start_error}") from start_error
    try:
        context, desktop = _connect_uno_pipe(uno, pipe_name, process)
    except Exception:
        _terminate_process(process)
        shutil.rmtree(profile_dir, ignore_errors=True)
        raise
    return LibreOfficeSession(process, profile_dir, context, desktop, uno)


def _load_document(
    session: LibreOfficeSession,
    file_path: Path,
    hidden: bool,
    readonly: bool,
) -> object:
    """
    加载 LibreOffice 文档。
    :param session: LibreOffice 会话
    :param file_path: 文档路径
    :param hidden: 是否隐藏文档窗口
    :param readonly: 是否只读打开
    :return: UNO 文档对象
    """
    properties = (
        session.property_value("Hidden", hidden),
        session.property_value("ReadOnly", readonly),
    )
    return session.desktop.loadComponentFromURL(
        session.path_to_file_url(file_path),
        "_blank",
        0,
        properties,
    )


def _close_document(document: object) -> None:
    """
    关闭 UNO 文档。
    :param document: UNO 文档对象
    :return: None
    """
    try:
        document.close(True)  # type: ignore[attr-defined]
        return
    except Exception:
        pass
    try:
        document.dispose()  # type: ignore[attr-defined]
    except Exception:
        pass


def _import_uno() -> Any:
    """
    导入 LibreOffice Python 的 uno 模块。
    :return: uno 模块
    """
    try:
        import uno  # type: ignore[import-not-found]
    except Exception as import_error:
        raise WorkerError(f"无法导入 LibreOffice pyuno：{import_error}") from import_error
    return uno


def _resolve_soffice_executable() -> Path:
    """
    从 LibreOffice Python 所在目录解析 soffice 可执行文件。
    :return: soffice 可执行文件路径
    """
    program_dir = Path(sys.executable).resolve().parent
    names = (
        ("soffice.com", "soffice.exe", "soffice")
        if os.name == "nt"
        else ("soffice", "soffice.com", "soffice.exe")
    )
    for name in names:
        candidate = program_dir / name
        if candidate.is_file():
            return candidate
    raise WorkerError(f"未找到 LibreOffice soffice：{program_dir}")


def _connect_uno_pipe(
    uno: Any,
    pipe_name: str,
    process: subprocess.Popen[bytes],
) -> tuple[object, object]:
    """
    等待 UNO pipe 连接。
    :param uno: pyuno 模块
    :param pipe_name: UNO pipe 名称
    :param process: soffice 启动进程
    :return: ComponentContext 与 Desktop
    """
    local_context = uno.getComponentContext()
    resolver = local_context.ServiceManager.createInstanceWithContext(
        "com.sun.star.bridge.UnoUrlResolver",
        local_context,
    )
    uno_url = f"uno:pipe,name={pipe_name};urp;StarOffice.ComponentContext"
    deadline = time.monotonic() + _timeout_seconds()
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise WorkerError(f"LibreOffice 进程提前退出，退出码={process.returncode}")
        try:
            context = resolver.resolve(uno_url)
            desktop = context.ServiceManager.createInstanceWithContext(
                "com.sun.star.frame.Desktop",
                context,
            )
            return context, desktop
        except Exception as connect_error:
            last_error = connect_error
            time.sleep(0.2)
    raise WorkerError(f"连接 LibreOffice UNO 超时：{last_error}")


def _timeout_seconds() -> float:
    """
    读取 worker 超时秒数。
    :return: 超时秒数
    """
    raw_value = os.environ.get("LIBREOFFICE_CONNECT_TIMEOUT_SECONDS", "10")
    try:
        return max(1.0, float(raw_value))
    except (TypeError, ValueError):
        return 10.0


def _bridge_command_timeout_seconds() -> float:
    """
    读取 bridge 命令超时秒数。
    :return: 超时秒数
    """
    raw_value = os.environ.get("LIBREOFFICE_BRIDGE_COMMAND_TIMEOUT_SECONDS", "120")
    try:
        return max(1.0, float(raw_value))
    except (TypeError, ValueError):
        return 120.0


def _recoverable_open_attempts() -> int:
    """
    读取 LibreOffice 可恢复打开错误的最大尝试次数。
    :return: 最大尝试次数
    """
    raw_value = os.environ.get("LIBREOFFICE_OPEN_RECOVERABLE_ATTEMPTS", "4")
    try:
        return max(1, int(raw_value))
    except (TypeError, ValueError):
        return 4


def _recoverable_open_retry_delay(attempt: int) -> float:
    """
    计算 LibreOffice 可恢复打开错误的退避等待秒数。
    :param attempt: 0-based 尝试序号
    :return: 等待秒数
    """
    base_delay = os.environ.get("LIBREOFFICE_OPEN_RECOVERABLE_RETRY_DELAY_SECONDS", "0.5")
    try:
        delay = max(0.0, float(base_delay))
    except (TypeError, ValueError):
        delay = 0.5
    return min(3.0, delay * (2 ** max(0, attempt)))


def _is_recoverable_bridge_dispose_error(error: BaseException) -> bool:
    """
    判断是否为 LibreOffice 冷启动后 UNO bridge 断开的可恢复错误。
    :param error: 捕获到的异常
    :return: True 表示可重建 session 后重试一次
    """
    error_text = f"{error.__class__.__name__}: {error}"
    return "DisposedException" in error_text or "Binary URP bridge disposed" in error_text


def _terminate_process(process: subprocess.Popen[bytes]) -> None:
    """
    尽力结束 LibreOffice 进程。
    :param process: soffice 启动进程
    :return: None
    """
    if process.poll() is not None:
        return
    if _terminate_process_tree(getattr(process, "pid", 0)):
        return
    try:
        process.terminate()
        process.wait(timeout=3)
        return
    except Exception:
        pass
    try:
        process.kill()
        process.wait(timeout=3)
    except Exception:
        pass


def _terminate_process_tree(process_id: int) -> bool:
    """
    结束 LibreOffice 启动器和其 soffice.bin 子进程。
    :param process_id: LibreOffice 启动器进程 ID
    :return: True 表示已通过进程树路径处理
    """
    if process_id <= 0:
        return False
    try:
        import psutil

        parent_process = psutil.Process(process_id)
        process_tree = parent_process.children(recursive=True)
        process_tree.append(parent_process)
        for child_process in process_tree:
            try:
                child_process.terminate()
            except Exception:
                pass
        _, alive_processes = psutil.wait_procs(process_tree, timeout=3)
        for alive_process in alive_processes:
            try:
                alive_process.kill()
            except Exception:
                pass
        if alive_processes:
            psutil.wait_procs(alive_processes, timeout=2)
        return True
    except Exception:
        return False
