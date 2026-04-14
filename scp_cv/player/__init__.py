#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
播放器包初始化：配置 GStreamer 运行时环境。
支持多种 GStreamer 安装变体，按优先级自动检测：
  1. MSVC x86_64（推荐，Complete 安装含 gobject-introspection）
  2. MinGW x86_64
  3. MSYS2 MinGW64
  4. MinGW（通用环境变量）
@Project : SCP-cv
@File : __init__.py
@Author : Qintsg
@Date : 2026-04-14
'''
from __future__ import annotations

import logging
import os
import sys
from typing import NamedTuple

logger = logging.getLogger(__name__)

# 模块级标记，避免重复初始化
_gstreamer_initialized: bool = False

# 支持的 GStreamer 安装变体（NamedTuple，便于打印与检索）
_SUPPORTED_VARIANTS_HELP: str = (
    "支持以下 GStreamer Windows 安装变体（按优先级排列）：\n"
    "  1. MSVC x86_64（推荐）— 环境变量 GSTREAMER_1_0_ROOT_MSVC_X86_64\n"
    "  2. MinGW x86_64 — 环境变量 GSTREAMER_1_0_ROOT_MINGW_X86_64\n"
    "  3. MSYS2 MinGW64 — 路径 C:\\msys64\\mingw64\n"
    "  4. 通用 x86_64 — 环境变量 GSTREAMER_1_0_ROOT_X86_64\n"
    "任一变体均需 Complete 安装选项（包含开发文件和 gobject-introspection）。"
)


class _GstVariant(NamedTuple):
    """GStreamer 安装变体描述。"""
    label: str
    env_var: str
    fallback_paths: list[str]


# 按优先级排列的变体列表
_GST_VARIANTS: list[_GstVariant] = [
    _GstVariant(
        label="MSVC x86_64",
        env_var="GSTREAMER_1_0_ROOT_MSVC_X86_64",
        fallback_paths=[
            r"C:\Program Files\gstreamer\1.0\msvc_x86_64",
            r"C:\gstreamer\1.0\msvc_x86_64",
            r"D:\gstreamer\1.0\msvc_x86_64",
        ],
    ),
    _GstVariant(
        label="MinGW x86_64",
        env_var="GSTREAMER_1_0_ROOT_MINGW_X86_64",
        fallback_paths=[
            r"C:\Program Files\gstreamer\1.0\mingw_x86_64",
            r"C:\gstreamer\1.0\mingw_x86_64",
            r"D:\gstreamer\1.0\mingw_x86_64",
        ],
    ),
    _GstVariant(
        label="MSYS2 MinGW64",
        env_var="",
        fallback_paths=[
            r"C:\msys64\mingw64",
        ],
    ),
    _GstVariant(
        label="通用 x86_64",
        env_var="GSTREAMER_1_0_ROOT_X86_64",
        fallback_paths=[],
    ),
]


def _resolve_gst_root(variant: _GstVariant) -> str:
    """
    尝试从环境变量或回退路径解析 GStreamer 根目录。
    :param variant: 安装变体描述
    :return: 有效的根目录路径，未找到返回空字符串
    """
    # 优先使用环境变量
    if variant.env_var:
        env_value: str = os.environ.get(variant.env_var, "")
        if env_value and os.path.isdir(env_value):
            return env_value

    # 回退到常见安装路径
    for candidate in variant.fallback_paths:
        if os.path.isdir(candidate):
            return candidate

    return ""


def _setup_gstreamer_paths_windows() -> None:
    """
    在 Windows 上按优先级检测并配置 GStreamer 运行时路径。
    按 MSVC → MinGW x86_64 → MSYS2 MinGW64 → 通用 x86_64 顺序探测，
    使用第一个找到的可用安装。
    """
    gst_root: str = ""
    matched_label: str = ""

    for variant in _GST_VARIANTS:
        gst_root = _resolve_gst_root(variant)
        if gst_root:
            matched_label = variant.label
            break

    if not gst_root:
        logger.warning(
            "未找到 GStreamer 安装目录。%s\n"
            "下载地址：https://gstreamer.freedesktop.org/download/",
            _SUPPORTED_VARIANTS_HELP,
        )
        return

    gst_bin = os.path.join(gst_root, "bin")
    gst_lib = os.path.join(gst_root, "lib")
    gst_typelib_dir = os.path.join(gst_lib, "girepository-1.0")
    gst_plugin_dir = os.path.join(gst_lib, "gstreamer-1.0")

    # 添加 DLL 和可执行文件搜索路径
    current_path = os.environ.get("PATH", "")
    if gst_bin not in current_path:
        os.environ["PATH"] = gst_bin + os.pathsep + current_path

    # Python 3.8+ 需要显式添加 DLL 搜索目录
    if hasattr(os, "add_dll_directory"):
        os.add_dll_directory(gst_bin)

    # GObject Introspection 类型库路径
    os.environ["GI_TYPELIB_PATH"] = gst_typelib_dir

    # GStreamer 插件路径
    if "GST_PLUGIN_PATH" not in os.environ:
        os.environ["GST_PLUGIN_PATH"] = gst_plugin_dir

    # Python 绑定路径：GStreamer 安装器自带的 gi overrides
    gst_python_site = os.path.join(
        gst_lib,
        f"python{sys.version_info.major}.{sys.version_info.minor}",
        "site-packages",
    )
    if os.path.isdir(gst_python_site) and gst_python_site not in sys.path:
        sys.path.insert(0, gst_python_site)

    logger.info("GStreamer 路径已配置（variant=%s, root=%s）", matched_label, gst_root)


def init_gstreamer() -> bool:
    """
    初始化 GStreamer 运行时。在首次使用 GStreamer 前必须调用。
    Windows 上自动按优先级检测 GStreamer 安装（MSVC → MinGW → MSYS2）。
    :return: True 表示初始化成功
    """
    global _gstreamer_initialized

    if _gstreamer_initialized:
        return True

    # Windows 路径配置（必须在 import gi 之前完成）
    if sys.platform == "win32":
        _setup_gstreamer_paths_windows()

    try:
        import gi  # noqa: E402
        gi.require_version("Gst", "1.0")
        gi.require_version("GstWebRTC", "1.0")
        gi.require_version("GstSdp", "1.0")
        gi.require_version("GstVideo", "1.0")

        from gi.repository import Gst
        initialized, _argv = Gst.init_check(None)

        if not initialized:
            logger.error("Gst.init_check() 返回 False")
            return False

        _gstreamer_initialized = True
        gst_version = Gst.version_string()
        logger.info("GStreamer 已初始化：%s", gst_version)
        return True

    except ImportError as import_error:
        logger.error(
            "无法导入 GStreamer Python 绑定（gi）：%s。\n"
            "请安装 GStreamer（Complete 选项）并运行 "
            "python tools/install_pygobject.py 安装 PyGObject。\n"
            "%s",
            import_error,
            _SUPPORTED_VARIANTS_HELP,
        )
        return False
    except ValueError as version_error:
        logger.error(
            "GStreamer 组件版本不匹配：%s。"
            "请检查 GStreamer 是否以 Complete 选项安装。",
            version_error,
        )
        return False


def check_gstreamer_available() -> bool:
    """
    检查 GStreamer 是否已安装且可用（不执行初始化）。
    :return: True 表示 GStreamer 可用
    """
    if _gstreamer_initialized:
        return True

    try:
        import gi
        gi.require_version("Gst", "1.0")
        from gi.repository import Gst  # noqa: F401
        return True
    except (ImportError, ValueError):
        return False
