#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
播放控制台视图，负责主页面渲染与所有 HTTP 操作端点。
包含三大功能区：统一源列表管理、播放控制、系统设置。
@Project : SCP-cv
@File : views.py
@Author : Qintsg
@Date : 2026-04-14
'''
from __future__ import annotations

import json
import logging

from django.conf import settings
from django.http import (
    HttpRequest,
    HttpResponse,
    JsonResponse,
    StreamingHttpResponse,
)
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from scp_cv.services.display import build_left_right_splice_target, list_display_targets
from scp_cv.services.executables import get_mediamtx_executable
from scp_cv.services.media import (
    MediaError,
    add_local_path,
    add_uploaded_file,
    delete_media_source,
    list_media_sources,
    sync_streams_to_media_sources,
)
from scp_cv.services.mediamtx import sync_stream_states
from scp_cv.services.playback import (
    PlaybackError,
    close_source,
    control_playback,
    get_or_create_session,
    get_session_snapshot,
    navigate_content,
    open_source,
    select_display_target,
    stop_current_content,
)
from scp_cv.services.sse import event_stream, publish_event

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════
# 页面渲染
# ══════════════════════════════════════════════════════════════

@require_GET
def home(request: HttpRequest) -> HttpResponse:
    """
    渲染播放控制台主页面，包含三个 Tab：源列表、播放控制、设置。
    :param request: HTTP 请求
    :return: 渲染后的控制台页面
    """
    display_targets = list_display_targets()
    splice_target = build_left_right_splice_target(display_targets)
    session_snapshot = get_session_snapshot()

    # 同步流状态并获取源列表
    sync_stream_states()
    sync_streams_to_media_sources()
    media_sources = list_media_sources()

    context = {
        # 会话状态
        "session": session_snapshot,
        "current_source_name": session_snapshot["source_name"],
        "current_source_type": session_snapshot["source_type_label"],
        "current_playback_state": session_snapshot["playback_state_label"],
        "current_display_mode": session_snapshot["display_mode_label"],
        # 显示器
        "display_targets": display_targets,
        "spliced_display": splice_target,
        # 媒体源
        "media_sources": media_sources,
        # 外部组件
        "mediamtx_path": str(get_mediamtx_executable() or "未检测到"),
        "refresh_timestamp": timezone.localtime(timezone.now()).strftime("%Y-%m-%d %H:%M:%S"),
        "debug_mode_label": "DEBUG 模式" if settings.DEBUG else "生产模式",
    }
    return render(request, "dashboard/home.html", context)


# ══════════════════════════════════════════════════════════════
# 源管理 API
# ══════════════════════════════════════════════════════════════

@require_POST
def upload_source(request: HttpRequest) -> JsonResponse:
    """
    通过文件上传添加媒体源。
    :param request: HTTP 请求（multipart/form-data，包含 file 字段）
    :return: JSON 响应
    """
    uploaded_file = request.FILES.get("file")
    if not uploaded_file:
        return JsonResponse({"success": False, "error": "缺少 file 字段"}, status=400)

    display_name = request.POST.get("name", "").strip() or None
    source_type = request.POST.get("source_type", "").strip() or None

    try:
        source = add_uploaded_file(uploaded_file, display_name, source_type)
    except MediaError as upload_err:
        return JsonResponse({"success": False, "error": str(upload_err)}, status=400)

    return JsonResponse({
        "success": True,
        "source": {
            "id": source.pk,
            "name": source.name,
            "source_type": source.source_type,
            "uri": source.uri,
        },
    })


@require_POST
def add_local_source(request: HttpRequest) -> JsonResponse:
    """
    通过本地路径注册媒体源。
    :param request: HTTP 请求（JSON body 或 POST form，包含 path 字段）
    :return: JSON 响应
    """
    # 支持 JSON body 和 form 两种提交方式
    local_path = request.POST.get("path", "").strip()
    display_name = request.POST.get("name", "").strip() or None
    source_type = request.POST.get("source_type", "").strip() or None

    if not local_path and request.content_type == "application/json":
        try:
            body = json.loads(request.body)
            local_path = body.get("path", "").strip()
            display_name = body.get("name", "").strip() or display_name
            source_type = body.get("source_type", "").strip() or source_type
        except (json.JSONDecodeError, AttributeError):
            pass

    if not local_path:
        return JsonResponse({"success": False, "error": "缺少 path 字段"}, status=400)

    try:
        source = add_local_path(local_path, display_name, source_type)
    except MediaError as path_err:
        return JsonResponse({"success": False, "error": str(path_err)}, status=400)

    return JsonResponse({
        "success": True,
        "source": {
            "id": source.pk,
            "name": source.name,
            "source_type": source.source_type,
            "uri": source.uri,
        },
    })


@require_POST
def remove_source(request: HttpRequest) -> JsonResponse:
    """
    删除指定媒体源。
    :param request: HTTP 请求（POST form，包含 source_id 字段）
    :return: JSON 响应
    """
    source_id = request.POST.get("source_id")
    if not source_id:
        return JsonResponse({"success": False, "error": "缺少 source_id"}, status=400)

    try:
        source_id_int = int(source_id)
    except (ValueError, TypeError):
        return JsonResponse({"success": False, "error": "source_id 格式无效"}, status=400)

    try:
        delete_media_source(source_id_int)
    except MediaError as delete_err:
        return JsonResponse({"success": False, "error": str(delete_err)}, status=400)

    return JsonResponse({"success": True})


@require_GET
def api_sources(request: HttpRequest) -> JsonResponse:
    """
    获取所有媒体源列表（含流同步）。
    :param request: HTTP 请求
    :return: JSON 格式的媒体源列表
    """
    # 先同步 MediaMTX 流状态
    sync_result = sync_stream_states()
    stream_sync = sync_streams_to_media_sources()

    source_type_filter = request.GET.get("source_type", "").strip() or None
    sources = list_media_sources(source_type_filter)

    return JsonResponse({
        "success": True,
        "sources": sources,
        "sync_result": {**sync_result, **stream_sync},
    }, json_dumps_params={"default": str})


# ══════════════════════════════════════════════════════════════
# 播放控制 API
# ══════════════════════════════════════════════════════════════

@require_POST
def open_media_source(request: HttpRequest) -> JsonResponse:
    """
    打开指定媒体源到播放区域。
    :param request: HTTP 请求（POST form，包含 source_id 字段）
    :return: JSON 响应
    """
    source_id = request.POST.get("source_id")
    if not source_id:
        return JsonResponse({"success": False, "error": "缺少 source_id"}, status=400)

    try:
        source_id_int = int(source_id)
    except (ValueError, TypeError):
        return JsonResponse({"success": False, "error": "source_id 格式无效"}, status=400)

    autoplay = request.POST.get("autoplay", "true").lower() in ("true", "1", "yes")

    try:
        open_source(source_id_int, autoplay=autoplay)
    except PlaybackError as open_err:
        return JsonResponse({"success": False, "error": str(open_err)}, status=400)

    snapshot = get_session_snapshot()
    publish_event("playback_state", snapshot)
    return JsonResponse({"success": True, "session": snapshot})


@require_POST
def playback_control(request: HttpRequest) -> JsonResponse:
    """
    播放控制（play / pause / stop）。
    :param request: HTTP 请求（POST form，包含 action 字段）
    :return: JSON 响应
    """
    action = request.POST.get("action", "").strip()
    if not action:
        return JsonResponse({"success": False, "error": "缺少 action 字段"}, status=400)

    try:
        control_playback(action)
    except PlaybackError as ctrl_err:
        return JsonResponse({"success": False, "error": str(ctrl_err)}, status=400)

    snapshot = get_session_snapshot()
    publish_event("playback_state", snapshot)
    return JsonResponse({"success": True, "session": snapshot})


@require_POST
def navigate(request: HttpRequest) -> JsonResponse:
    """
    内容导航（下一页/上一页/跳转/Seek）。
    :param request: HTTP 请求（POST form，包含 action 字段）
    :return: JSON 响应
    """
    action = request.POST.get("action", "").strip()
    if not action:
        return JsonResponse({"success": False, "error": "缺少 action 字段"}, status=400)

    target_index = 0
    position_ms = 0
    try:
        target_index = int(request.POST.get("target_index", "0"))
        position_ms = int(request.POST.get("position_ms", "0"))
    except (ValueError, TypeError):
        pass

    try:
        navigate_content(action, target_index=target_index, position_ms=position_ms)
    except PlaybackError as nav_err:
        return JsonResponse({"success": False, "error": str(nav_err)}, status=400)

    snapshot = get_session_snapshot()
    publish_event("playback_state", snapshot)
    return JsonResponse({"success": True, "session": snapshot})


@require_POST
def close_current(request: HttpRequest) -> JsonResponse:
    """
    关闭当前播放的源。
    :param request: HTTP 请求
    :return: JSON 响应
    """
    try:
        close_source()
    except PlaybackError as close_err:
        return JsonResponse({"success": False, "error": str(close_err)}, status=400)

    snapshot = get_session_snapshot()
    publish_event("playback_state", snapshot)
    return JsonResponse({"success": True, "session": snapshot})


# ══════════════════════════════════════════════════════════════
# 显示配置 API
# ══════════════════════════════════════════════════════════════

@require_POST
def switch_display(request: HttpRequest) -> JsonResponse:
    """
    切换显示模式或选择显示器。
    :param request: HTTP 请求
    :return: JSON 响应
    """
    display_mode = request.POST.get("display_mode", "")
    target_display_name = request.POST.get("target_display_name", "")

    try:
        select_display_target(display_mode, target_display_name)
    except PlaybackError as switch_error:
        return JsonResponse({"success": False, "error": str(switch_error)}, status=400)

    snapshot = get_session_snapshot()
    publish_event("playback_state", snapshot)
    return JsonResponse({"success": True, "session": snapshot})


# ══════════════════════════════════════════════════════════════
# 状态查询 & SSE
# ══════════════════════════════════════════════════════════════

@require_GET
def api_session_state(request: HttpRequest) -> JsonResponse:
    """
    获取当前播放会话状态的 JSON API。
    :param request: HTTP 请求
    :return: JSON 格式的会话快照
    """
    snapshot = get_session_snapshot()
    return JsonResponse({"success": True, "session": snapshot})


@require_GET
def sse_events(request: HttpRequest) -> StreamingHttpResponse:
    """
    SSE 事件流端点，客户端通过 EventSource 连接。
    :param request: HTTP 请求
    :return: 持续推送的 SSE 响应流
    """
    last_id = request.GET.get("last_id", "0")
    try:
        last_sequence = int(last_id)
    except (ValueError, TypeError):
        last_sequence = 0

    response = StreamingHttpResponse(
        event_stream(last_sequence),
        content_type="text/event-stream",
    )
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response
