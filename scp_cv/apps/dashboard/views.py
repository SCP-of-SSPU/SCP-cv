#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
播放控制台视图，承载主页面渲染与所有 HTTP 操作端点。
@Project : SCP-cv
@File : views.py
@Author : Qintsg
@Date : 2026-04-10
'''
from __future__ import annotations

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
from scp_cv.services.playback import (
    PlaybackError,
    get_or_create_session,
    get_session_snapshot,
    open_stream_source,
    select_display_target,
    stop_current_content,
)
from scp_cv.services.mediamtx import sync_stream_states
from scp_cv.services.sse import event_stream, publish_event

logger = logging.getLogger(__name__)


@require_GET
def home(request: HttpRequest) -> HttpResponse:
    """
    渲染播放控制台主页面，展示所有状态和控制组件。
    :param request: HTTP 请求
    :return: 渲染后的控制台页面
    """
    display_targets = list_display_targets()
    splice_target = build_left_right_splice_target(display_targets)
    session_snapshot = get_session_snapshot()

    # 获取 WebRTC 流列表
    from scp_cv.apps.streams.models import StreamSource
    stream_rows = list(StreamSource.objects.values(
        "id", "name", "stream_identifier", "is_online", "current_state",
        "last_connected_at",
    ))

    context = {
        # 会话状态
        "session": session_snapshot,
        "current_content_title": session_snapshot["stream_name"] if session_snapshot["content_kind"] == "stream" else "尚未打开资源",
        "current_content_kind": session_snapshot["content_kind_label"],
        "current_playback_state": session_snapshot["playback_state_label"],
        "current_display_mode": session_snapshot["display_mode_label"],
        # 显示器
        "display_targets": display_targets,
        "spliced_display": splice_target,
        # 流
        "stream_rows": stream_rows,
        # 外部组件
        "mediamtx_path": str(get_mediamtx_executable() or "未检测到"),
        "refresh_timestamp": timezone.localtime(timezone.now()).strftime("%Y-%m-%d %H:%M:%S"),
        "debug_mode_label": "DEBUG 模式" if settings.DEBUG else "生产模式",
    }
    return render(request, "dashboard/home.html", context)


@require_POST
def stop_playback(request: HttpRequest) -> HttpResponse:
    """
    停止当前播放内容。
    :param request: HTTP 请求
    :return: JSON 响应
    """
    try:
        stop_current_content()
    except PlaybackError as stop_error:
        return JsonResponse({"success": False, "error": str(stop_error)}, status=400)

    snapshot = get_session_snapshot()
    publish_event("playback_state", snapshot)
    return JsonResponse({"success": True, "session": snapshot})


@require_POST
def switch_display(request: HttpRequest) -> HttpResponse:
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


@require_POST
def open_stream(request: HttpRequest) -> HttpResponse:
    """
    打开指定 WebRTC 流到播放区域。
    :param request: HTTP 请求
    :return: JSON 响应
    """
    stream_id = request.POST.get("stream_id")
    if not stream_id:
        return JsonResponse({"success": False, "error": "缺少 stream_id"}, status=400)

    try:
        stream_id_int = int(stream_id)
    except (ValueError, TypeError):
        return JsonResponse({"success": False, "error": "stream_id 格式无效"}, status=400)

    try:
        open_stream_source(stream_id_int)
    except PlaybackError as open_error:
        return JsonResponse({"success": False, "error": str(open_error)}, status=400)

    snapshot = get_session_snapshot()
    publish_event("playback_state", snapshot)
    return JsonResponse({"success": True, "session": snapshot})


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


@require_GET
def api_streams(request: HttpRequest) -> JsonResponse:
    """
    同步 MediaMTX 流状态并返回最新流列表（含自动注册新发现的流）。
    前端定时轮询此端点以实现流自动发现与状态更新。
    :param request: HTTP 请求
    :return: JSON 格式的流列表与同步结果
    """
    sync_result = sync_stream_states()

    from scp_cv.apps.streams.models import StreamSource
    stream_rows = list(StreamSource.objects.values(
        "id", "name", "stream_identifier", "is_online", "current_state",
        "last_connected_at",
    ))

    return JsonResponse({
        "success": True,
        "streams": stream_rows,
        "sync_result": sync_result,
    }, json_dumps_params={"default": str})
