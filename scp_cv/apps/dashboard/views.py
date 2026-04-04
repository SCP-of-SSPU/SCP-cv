from __future__ import annotations

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils import timezone

from scp_cv.services.display import build_left_right_splice_target, list_display_targets
from scp_cv.services.executables import get_libreoffice_executable, get_mediamtx_executable


def home(request: HttpRequest) -> HttpResponse:
    """Render the main control console with runtime placeholders."""

    display_targets = list_display_targets()
    splice_target = build_left_right_splice_target(display_targets)
    current_timestamp = timezone.localtime(timezone.now()).strftime("%Y-%m-%d %H:%M:%S")
    context = {
        "current_content_title": "尚未打开资源",
        "current_content_kind": "PPT / SRT 待命",
        "current_playback_state": "待机",
        "current_display_mode": "单屏模式" if len(display_targets) < 2 else "拼接候选已就绪",
        "ppt_page_progress": "1 / 1",
        "current_stream_state": "未连接",
        "display_targets": display_targets,
        "spliced_display": splice_target,
        "resource_rows": [],
        "stream_rows": [],
        "ppt_media_rows": [],
        "mediamtx_path": str(get_mediamtx_executable() or "未检测到"),
        "libreoffice_path": str(get_libreoffice_executable() or "未检测到"),
        "refresh_timestamp": current_timestamp,
        "debug_mode_label": "DEBUG 模式" if settings.DEBUG else "生产模式",
    }
    return render(request, "dashboard/home.html", context)
