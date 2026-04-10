from __future__ import annotations

from pathlib import Path
from shutil import which

from django.conf import settings


def _resolve_executable_path(configured_path: str, fallback_names: tuple[str, ...]) -> Path | None:
    """优先使用环境变量，其次回退到系统 PATH 里的可执行文件。"""

    candidate_text = configured_path.strip()
    if candidate_text:
        candidate_path = Path(candidate_text).expanduser()
        if not candidate_path.is_absolute():
            candidate_path = Path(settings.BASE_DIR) / candidate_path
        if candidate_path.exists():
            return candidate_path

    for executable_name in fallback_names:
        resolved_name = which(executable_name)
        if resolved_name:
            return Path(resolved_name)

    return None


def get_mediamtx_executable() -> Path | None:
    """查找 MediaMTX 可执行文件。"""

    return _resolve_executable_path(settings.MEDIAMTX_BIN_PATH, ("mediamtx.exe", "mediamtx"))
