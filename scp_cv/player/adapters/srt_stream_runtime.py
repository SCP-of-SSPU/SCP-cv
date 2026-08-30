#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''libVLC 运行时发现和低延迟参数配置。'''

from __future__ import annotations

import logging
import os
from pathlib import Path

from django.conf import settings

from scp_cv.player.gpu_detector import get_vlc_gpu_options

logger = logging.getLogger(__name__)
_VLC_RUNTIME_DIR = Path(__file__).resolve().parents[3] / "tools" / "third_party" / "vlc"
_VLC_DLL_DIRECTORY_HANDLES: list[object] = []


def _candidate_vlc_runtime_dirs() -> list[Path]:
    """枚举 libVLC 运行时目录候选位置。"""
    candidates = [_VLC_RUNTIME_DIR / "runtime", _VLC_RUNTIME_DIR]
    for env_name in ("ProgramFiles", "ProgramFiles(x86)"):
        root = os.environ.get(env_name)
        if root:
            candidates.append(Path(root) / "VideoLAN" / "VLC")
    return candidates


def configure_vlc_runtime_paths() -> Path | None:
    """将可用 libVLC 目录加入 DLL 搜索路径。"""
    for runtime_dir in _candidate_vlc_runtime_dirs():
        if not (runtime_dir / "libvlc.dll").is_file():
            continue
        runtime_path = str(runtime_dir)
        if os.name == "nt" and hasattr(os, "add_dll_directory"):
            _VLC_DLL_DIRECTORY_HANDLES.append(os.add_dll_directory(runtime_path))
        os.environ["PATH"] = runtime_path + os.pathsep + os.environ.get("PATH", "")
        plugin_dir = runtime_dir / "plugins"
        if plugin_dir.is_dir():
            os.environ.setdefault("VLC_PLUGIN_PATH", str(plugin_dir))
        logger.debug("已配置 libVLC 运行时目录：%s", runtime_dir)
        return runtime_dir
    logger.debug("未发现项目内置 libVLC，继续使用系统 PATH 查找")
    return None


def load_vlc() -> object | None:
    """加载 python-vlc，导入失败时返回 None。"""
    configure_vlc_runtime_paths()
    try:
        import vlc
    except (ImportError, OSError) as import_error:
        logger.debug("libVLC 不可用：%s", import_error)
        return None
    return vlc


def build_vlc_instance_args() -> list[str]:
    """生成 libVLC 实例级低延迟参数。"""
    args = [
        "--no-video-title-show", "--no-snapshot-preview",
        f"--network-caching={int(getattr(settings, 'STREAM_VLC_NETWORK_CACHING_MS', 50))}",
        f"--live-caching={int(getattr(settings, 'STREAM_VLC_LIVE_CACHING_MS', 50))}",
        f"--file-caching={int(getattr(settings, 'STREAM_VLC_FILE_CACHING_MS', 0))}",
        f"--clock-jitter={int(getattr(settings, 'STREAM_VLC_CLOCK_JITTER', 0))}",
        f"--clock-synchro={int(getattr(settings, 'STREAM_VLC_CLOCK_SYNCHRO', 0))}",
    ]
    if bool(getattr(settings, "STREAM_VLC_DROP_LATE_FRAMES", True)):
        args.append("--drop-late-frames")
    if bool(getattr(settings, "STREAM_VLC_SKIP_FRAMES", True)):
        args.append("--skip-frames")
    args.extend(get_vlc_gpu_options())
    return args


def build_srt_media_options() -> list[str]:
    """生成 SRT 直播源媒体级参数。"""
    options = [
        f":network-caching={int(getattr(settings, 'STREAM_VLC_NETWORK_CACHING_MS', 50))}",
        f":live-caching={int(getattr(settings, 'STREAM_VLC_LIVE_CACHING_MS', 50))}",
        f":clock-jitter={int(getattr(settings, 'STREAM_VLC_CLOCK_JITTER', 0))}",
        f":clock-synchro={int(getattr(settings, 'STREAM_VLC_CLOCK_SYNCHRO', 0))}",
    ]
    if bool(getattr(settings, "STREAM_VLC_DROP_LATE_FRAMES", True)):
        options.append(":drop-late-frames")
    if bool(getattr(settings, "STREAM_VLC_SKIP_FRAMES", True)):
        options.append(":skip-frames")
    transport = str(getattr(settings, "MEDIAMTX_RTSP_READ_TRANSPORT", "tcp") or "").strip().lower()
    if transport in {"tcp", "udp"}:
        options.append(f":rtsp-{transport}")
    return options


__all__ = ["build_srt_media_options", "build_vlc_instance_args", "configure_vlc_runtime_paths", "load_vlc"]
