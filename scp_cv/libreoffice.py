#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
LibreOffice UNO 运行时工具，负责查找 soffice、启动隔离实例并建立 UNO 连接。
@Project : SCP-cv
@File : libreoffice.py
@Author : Qintsg
@Date : 2026-05-26
'''
from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class LibreOfficeError(RuntimeError):
    """LibreOffice 启动、连接或 UNO 调用失败。"""


@dataclass
class LibreOfficeSession:
    """
    LibreOffice 隔离进程和 UNO 上下文。
    :param process: soffice 子进程
    :param profile_dir: 独立 UserInstallation 目录
    :param pipe_name: UNO pipe 名称
    :param context: 远端 ComponentContext
    :param desktop: com.sun.star.frame.Desktop 实例
    :param uno: 已导入的 pyuno 模块
    """

    process: subprocess.Popen[bytes]
    profile_dir: Path
    pipe_name: str
    context: Any
    desktop: Any
    uno: Any

    def create_instance(self, service_name: str) -> Any:
        """
        在当前 UNO 上下文中创建服务实例。
        :param service_name: UNO 服务名称
        :return: 服务实例
        """
        return self.context.ServiceManager.createInstanceWithContext(
            service_name,
            self.context,
        )

    def property_value(self, name: str, value: object) -> Any:
        """
        创建 UNO PropertyValue。
        :param name: 属性名
        :param value: 属性值
        :return: com.sun.star.beans.PropertyValue
        """
        return create_property_value(self.uno, name, value)

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


def configured_libreoffice_bin_path() -> str:
    """
    获取配置的 LibreOffice 可执行文件路径。
    :return: 显式配置路径；未配置时返回空字符串
    """
    env_value = os.environ.get("LIBREOFFICE_BIN_PATH")
    if env_value is not None:
        return env_value.strip()
    settings_value = _settings_value("LIBREOFFICE_BIN_PATH", "")
    return str(settings_value or "").strip()


def configured_libreoffice_timeout() -> float:
    """
    获取 LibreOffice UNO 连接超时时间。
    :return: 超时秒数
    """
    raw_value = os.environ.get("LIBREOFFICE_CONNECT_TIMEOUT_SECONDS")
    if raw_value is None:
        raw_value = str(_settings_value("LIBREOFFICE_CONNECT_TIMEOUT_SECONDS", 10.0))
    try:
        return max(1.0, float(raw_value))
    except (TypeError, ValueError):
        return 10.0


def resolve_libreoffice_executable(bin_path: Optional[str] = None) -> Path:
    """
    查找 LibreOffice soffice 可执行文件。
    :param bin_path: 显式路径，可指向 soffice 文件或 LibreOffice 目录
    :return: soffice 可执行文件路径
    :raises LibreOfficeError: 未找到可执行文件时
    """
    configured_path = (bin_path if bin_path is not None else configured_libreoffice_bin_path()).strip()
    if configured_path:
        executable = _resolve_configured_path(Path(configured_path).expanduser())
        if executable is not None:
            return executable
        raise LibreOfficeError(f"未找到 LIBREOFFICE_BIN_PATH 指向的 soffice：{configured_path}")

    for executable_name in ("soffice.com", "soffice.exe", "soffice"):
        executable = shutil.which(executable_name)
        if executable:
            return Path(executable)

    for candidate in _common_libreoffice_candidates():
        if candidate.is_file():
            return candidate
    raise LibreOfficeError("未找到 LibreOffice soffice，可配置 LIBREOFFICE_BIN_PATH")


def resolve_libreoffice_python_executable(bin_path: Optional[str] = None) -> Path:
    """
    查找 LibreOffice 自带 Python 可执行文件。
    :param bin_path: 显式 soffice 或 LibreOffice 目录路径
    :return: LibreOffice program/python.exe 路径
    :raises LibreOfficeError: 未找到可执行文件时
    """
    soffice_executable = resolve_libreoffice_executable(bin_path)
    program_dir = soffice_executable.parent
    executable_names = ["python.exe", "python"] if os.name == "nt" else ["python", "python.exe"]
    for executable_name in executable_names:
        python_executable = program_dir / executable_name
        if python_executable.is_file():
            return python_executable
    raise LibreOfficeError(f"未找到 LibreOffice 自带 Python：{program_dir}")


def bootstrap_pyuno(program_dir: Path) -> Any:
    """
    将 LibreOffice program 目录加入 Python 搜索路径并导入 pyuno。
    :param program_dir: LibreOffice program 目录
    :return: uno 模块
    :raises LibreOfficeError: 无法导入 pyuno 时
    """
    program_dir_text = str(program_dir)
    if program_dir_text not in sys.path:
        sys.path.insert(0, program_dir_text)
    current_path = os.environ.get("PATH", "")
    path_parts = current_path.split(os.pathsep) if current_path else []
    if program_dir_text not in path_parts:
        os.environ["PATH"] = program_dir_text + os.pathsep + current_path

    fundamental_ini = program_dir / "fundamental.ini"
    if fundamental_ini.is_file() and not os.environ.get("URE_BOOTSTRAP"):
        os.environ["URE_BOOTSTRAP"] = f"vnd.sun.star.pathname:{fundamental_ini}"

    try:
        import uno  # type: ignore[import-not-found]
    except Exception as import_error:
        raise LibreOfficeError(f"无法导入 LibreOffice pyuno：{import_error}") from import_error
    return uno


def create_property_value(uno_module: Any, name: str, value: object) -> Any:
    """
    创建 UNO PropertyValue 结构。
    :param uno_module: pyuno 模块
    :param name: 属性名
    :param value: 属性值
    :return: PropertyValue
    """
    property_value = uno_module.createUnoStruct("com.sun.star.beans.PropertyValue")
    property_value.Name = name
    property_value.Value = value
    return property_value


def start_libreoffice_session(
    headless: bool = False,
    bin_path: Optional[str] = None,
    timeout_seconds: Optional[float] = None,
) -> LibreOfficeSession:
    """
    启动独立 LibreOffice 实例并连接 UNO pipe。
    :param headless: 是否使用无头模式
    :param bin_path: 可选 soffice 路径
    :param timeout_seconds: UNO 连接超时秒数
    :return: LibreOfficeSession
    :raises LibreOfficeError: 启动或连接失败时
    """
    executable = resolve_libreoffice_executable(bin_path)
    program_dir = executable.parent
    uno_module = bootstrap_pyuno(program_dir)
    timeout = timeout_seconds if timeout_seconds is not None else configured_libreoffice_timeout()
    pipe_name = f"scp_cv_{os.getpid()}_{uuid.uuid4().hex}"
    profile_dir = Path(tempfile.mkdtemp(prefix="scp-cv-lo-"))
    profile_url = uno_module.systemPathToFileUrl(str(profile_dir.resolve()))
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
        process = subprocess.Popen(
            args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError as start_error:
        shutil.rmtree(profile_dir, ignore_errors=True)
        raise LibreOfficeError(f"LibreOffice 启动失败：{start_error}") from start_error

    try:
        context, desktop = _connect_uno_pipe(uno_module, pipe_name, process, timeout)
    except Exception:
        _terminate_process(process)
        shutil.rmtree(profile_dir, ignore_errors=True)
        raise
    return LibreOfficeSession(process, profile_dir, pipe_name, context, desktop, uno_module)


def load_document(
    session: LibreOfficeSession,
    file_path: Path,
    hidden: bool,
    readonly: bool = True,
) -> Any:
    """
    通过 UNO Desktop 加载文档。
    :param session: LibreOffice 会话
    :param file_path: 待加载文件
    :param hidden: 是否隐藏编辑窗口
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


def close_document(document: object) -> None:
    """
    关闭 UNO 文档，失败时退回 dispose。
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


def _settings_value(name: str, default: object) -> object:
    """
    安全读取 Django settings，允许在非 Django 上下文中复用。
    :param name: settings 字段名
    :param default: 默认值
    :return: 配置值
    """
    try:
        from django.conf import settings
    except Exception:
        return default
    if not settings.configured:
        return default
    return getattr(settings, name, default)


def _resolve_configured_path(path: Path) -> Optional[Path]:
    """
    将用户配置路径解析为 soffice 可执行文件。
    :param path: 用户配置路径
    :return: 可执行文件路径；无法解析时返回 None
    """
    if path.is_file():
        return path
    candidates = [
        path / "soffice.com",
        path / "soffice.exe",
        path / "program" / "soffice.com",
        path / "program" / "soffice.exe",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def _common_libreoffice_candidates() -> list[Path]:
    """
    返回 Windows 常见 LibreOffice 安装路径。
    :return: 候选 soffice 路径列表
    """
    program_files = [
        os.environ.get("ProgramFiles", r"C:\Program Files"),
        os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
    ]
    candidates: list[Path] = []
    for base_dir in program_files:
        if not base_dir:
            continue
        candidates.extend(
            [
                Path(base_dir) / "LibreOffice" / "program" / "soffice.com",
                Path(base_dir) / "LibreOffice" / "program" / "soffice.exe",
            ]
        )
    return candidates


def _connect_uno_pipe(
    uno_module: Any,
    pipe_name: str,
    process: subprocess.Popen[bytes],
    timeout_seconds: float,
) -> tuple[Any, Any]:
    """
    等待 LibreOffice UNO pipe 可连接。
    :param uno_module: pyuno 模块
    :param pipe_name: pipe 名称
    :param process: LibreOffice 子进程
    :param timeout_seconds: 超时秒数
    :return: ComponentContext 和 Desktop
    :raises LibreOfficeError: 连接失败时
    """
    local_context = uno_module.getComponentContext()
    resolver = local_context.ServiceManager.createInstanceWithContext(
        "com.sun.star.bridge.UnoUrlResolver",
        local_context,
    )
    uno_url = f"uno:pipe,name={pipe_name};urp;StarOffice.ComponentContext"
    deadline = time.monotonic() + timeout_seconds
    last_error: Optional[Exception] = None
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise LibreOfficeError(f"LibreOffice 进程提前退出，退出码={process.returncode}")
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
    raise LibreOfficeError(f"连接 LibreOffice UNO 超时：{last_error}")


def _terminate_process(process: subprocess.Popen[bytes]) -> None:
    """
    尽力终止 LibreOffice 子进程。
    :param process: 待终止进程
    :return: None
    """
    if process.poll() is not None:
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
        logger.debug("LibreOffice 子进程强制结束失败", exc_info=True)
