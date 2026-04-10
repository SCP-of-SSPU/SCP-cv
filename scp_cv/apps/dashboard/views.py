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

import json
import logging

from django.conf import settings
from django.http import (
    HttpRequest,
    HttpResponse,
    JsonResponse,
    StreamingHttpResponse,
)
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from scp_cv.services.display import build_left_right_splice_target, list_display_targets
from scp_cv.services.executables import get_libreoffice_executable, get_mediamtx_executable
from scp_cv.services.playback import (
    PlaybackError,
    get_or_create_session,
    get_session_snapshot,
    navigate_page,
    open_ppt_resource,
    open_stream_source,
    select_display_target,
    stop_current_content,
)
from scp_cv.services.mediamtx import sync_stream_states
from scp_cv.services.ppt_processor import (
    PptProcessorError,
    get_page_media_list,
    parse_and_convert,
)
from scp_cv.services.resource_manager import (
    ResourceError,
    delete_resource,
    list_resources,
    upload_ppt_file,
)
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
    resource_rows = list_resources()

    # 获取当前 PPT 的媒体列表
    session = get_or_create_session()
    ppt_media_rows: list[dict[str, object]] = []
    if session.content_resource is not None:
        ppt_media_rows = get_page_media_list(
            session.content_resource.pk,
            session.current_page_number,
        )

    # 获取 SRT 流列表
    from scp_cv.apps.streams.models import StreamSource
    stream_rows = list(StreamSource.objects.values(
        "id", "name", "stream_identifier", "is_online", "current_state",
        "last_connected_at",
    ))

    context = {
        # 会话状态
        "session": session_snapshot,
        "current_content_title": session_snapshot["resource_title"] if session_snapshot["content_kind"] == "ppt" else session_snapshot["stream_name"] if session_snapshot["content_kind"] == "stream" else "尚未打开资源",
        "current_content_kind": session_snapshot["content_kind_label"],
        "current_playback_state": session_snapshot["playback_state_label"],
        "current_display_mode": session_snapshot["display_mode_label"],
        "ppt_page_progress": session_snapshot["page_progress"],
        # 显示器
        "display_targets": display_targets,
        "spliced_display": splice_target,
        # 资源与媒体
        "resource_rows": resource_rows,
        "ppt_media_rows": ppt_media_rows,
        "stream_rows": stream_rows,
        # 外部组件
        "mediamtx_path": str(get_mediamtx_executable() or "未检测到"),
        "libreoffice_path": str(get_libreoffice_executable() or "未检测到"),
        "refresh_timestamp": timezone.localtime(timezone.now()).strftime("%Y-%m-%d %H:%M:%S"),
        "debug_mode_label": "DEBUG 模式" if settings.DEBUG else "生产模式",
    }
    return render(request, "dashboard/home.html", context)


@require_POST
def upload_file(request: HttpRequest) -> HttpResponse:
    """
    处理 PPT/PPTX 文件上传请求。
    :param request: HTTP 请求（multipart/form-data）
    :return: 重定向到首页或返回错误信息
    """
    uploaded_file = request.FILES.get("ppt_file")
    if uploaded_file is None:
        return JsonResponse({"success": False, "error": "未选择文件"}, status=400)

    try:
        resource = upload_ppt_file(uploaded_file)
    except ResourceError as upload_error:
        return JsonResponse({"success": False, "error": str(upload_error)}, status=400)

    # 自动触发解析
    try:
        parse_and_convert(resource.pk)
    except PptProcessorError as parse_error:
        logger.warning("上传后自动解析失败（id=%d）：%s", resource.pk, parse_error)
        # 解析失败不阻止上传，资源仍保留

    # 发布资源更新事件
    publish_event("resource_updated", {"action": "upload", "resource_id": resource.pk})

    # 判断是否为 AJAX 请求
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({
            "success": True,
            "resource_id": resource.pk,
            "display_name": resource.display_name,
        })

    return redirect("dashboard:home")


@require_POST
def delete_file(request: HttpRequest) -> HttpResponse:
    """
    删除指定资源文件。
    :param request: HTTP 请求
    :return: JSON 响应
    """
    resource_id = request.POST.get("resource_id")
    if not resource_id:
        return JsonResponse({"success": False, "error": "缺少 resource_id"}, status=400)

    try:
        resource_id_int = int(resource_id)
    except (ValueError, TypeError):
        return JsonResponse({"success": False, "error": "resource_id 格式无效"}, status=400)

    try:
        # 如果正在播放，先停止
        session = get_or_create_session()
        if session.content_resource is not None and session.content_resource.pk == resource_id_int:
            stop_current_content()
            publish_event("playback_state", get_session_snapshot())

        delete_resource(resource_id_int)
    except ResourceError as delete_error:
        return JsonResponse({"success": False, "error": str(delete_error)}, status=400)

    publish_event("resource_updated", {"action": "delete", "resource_id": resource_id_int})
    return JsonResponse({"success": True})


@require_POST
def open_resource(request: HttpRequest) -> HttpResponse:
    """
    打开指定 PPT 资源到播放区域。
    :param request: HTTP 请求
    :return: JSON 响应
    """
    resource_id = request.POST.get("resource_id")
    if not resource_id:
        return JsonResponse({"success": False, "error": "缺少 resource_id"}, status=400)

    try:
        resource_id_int = int(resource_id)
    except (ValueError, TypeError):
        return JsonResponse({"success": False, "error": "resource_id 格式无效"}, status=400)

    try:
        open_ppt_resource(resource_id_int)
    except PlaybackError as open_error:
        return JsonResponse({"success": False, "error": str(open_error)}, status=400)

    snapshot = get_session_snapshot()
    publish_event("playback_state", snapshot)
    return JsonResponse({"success": True, "session": snapshot})


@require_POST
def ppt_navigate(request: HttpRequest) -> HttpResponse:
    """
    PPT 翻页控制：上一页、下一页、跳转指定页。
    :param request: HTTP 请求
    :return: JSON 响应
    """
    direction = request.POST.get("direction", "")
    target_page_str = request.POST.get("target_page", "")

    target_page = None
    if target_page_str:
        try:
            target_page = int(target_page_str)
        except (ValueError, TypeError):
            return JsonResponse({"success": False, "error": "页码格式无效"}, status=400)

    try:
        navigate_page(direction, target_page)
    except PlaybackError as nav_error:
        return JsonResponse({"success": False, "error": str(nav_error)}, status=400)

    snapshot = get_session_snapshot()
    publish_event("playback_state", snapshot)
    return JsonResponse({"success": True, "session": snapshot})


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
    打开指定 SRT 流到播放区域。
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
def api_resources(request: HttpRequest) -> JsonResponse:
    """
    获取资源列表的 JSON API。
    :param request: HTTP 请求
    :return: JSON 格式的资源列表
    """
    resources = list_resources()
    return JsonResponse({"success": True, "resources": resources}, json_dumps_params={"default": str})


@require_GET
def api_page_media(request: HttpRequest) -> JsonResponse:
    """
    获取当前页媒体列表的 JSON API。
    :param request: HTTP 请求
    :return: JSON 格式的媒体列表
    """
    session = get_or_create_session()
    if session.content_resource is None:
        return JsonResponse({"success": True, "media_items": []})

    media_items = get_page_media_list(
        session.content_resource.pk,
        session.current_page_number,
    )
    return JsonResponse({"success": True, "media_items": media_items})


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

    # 新流注册后通过 SSE 通知其他客户端刷新
    if sync_result["registered"] > 0:
        publish_event("stream_updated", {
            "action": "auto_register",
            "registered_count": sync_result["registered"],
        })

    return JsonResponse({
        "success": True,
        "streams": stream_rows,
        "sync_result": sync_result,
    }, json_dumps_params={"default": str})
