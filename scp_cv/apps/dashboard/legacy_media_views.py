#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
旧版表单媒体源管理视图。
@Project : SCP-cv
@File : legacy_media_views.py
@Author : Qintsg
@Date : 2026-07-11
'''
from __future__ import annotations

import json

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views.decorators.http import require_GET, require_POST

from scp_cv.services.command_status import (
    capture_enqueued_commands,
    control_command_payloads,
)
from scp_cv.services.media import (
    MediaError,
    add_local_path,
    add_uploaded_file,
    add_web_url,
    delete_media_source,
    list_media_sources,
    sync_streams_to_media_sources,
)
from scp_cv.services.mediamtx import sync_stream_states
from scp_cv.services.playback import get_all_sessions_snapshot
from scp_cv.services.sse import publish_event


@require_GET
def home(request: HttpRequest) -> HttpResponse:
    """
    返回前端分离后的后端服务提示。
    :param request: HTTP 请求
    :return: JSON 提示，Vue 控制台由 frontend/ 独立提供
    """
    return JsonResponse({
        "success": True,
        "service": "SCP-cv backend",
        "frontend": "frontend/ Vue application",
        "api": "/api/",
        "admin": "/admin/",
    })


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
def add_web_source(request: HttpRequest) -> JsonResponse:
    """
    通过 URL 添加网页类型媒体源。
    :param request: HTTP 请求（POST form，包含 url 字段）
    :return: JSON 响应
    """
    web_url = request.POST.get("url", "").strip()
    display_name = request.POST.get("name", "").strip() or None

    if not web_url:
        return JsonResponse({"success": False, "error": "缺少 url 字段"}, status=400)

    try:
        source = add_web_url(web_url, display_name)
    except MediaError as web_err:
        return JsonResponse({"success": False, "error": str(web_err)}, status=400)

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
        with capture_enqueued_commands() as accepted_commands:
            delete_media_source(source_id_int)
    except MediaError as delete_err:
        return JsonResponse({"success": False, "error": str(delete_err)}, status=400)

    command_payloads = control_command_payloads(accepted_commands)
    if command_payloads:
        publish_event("playback_state", {
            "sessions": get_all_sessions_snapshot(),
        })
    return JsonResponse({
        "success": True,
        "commands": command_payloads,
    })


@require_GET
def api_sources(request: HttpRequest) -> JsonResponse:
    """
    获取所有媒体源列表（含流同步）。
    :param request: HTTP 请求
    :return: JSON 格式的媒体源列表
    """
    sync_result = sync_stream_states()
    stream_sync = sync_streams_to_media_sources()
    source_type_filter = request.GET.get("source_type", "").strip() or None
    sources = list_media_sources(source_type_filter)
    return JsonResponse({
        "success": True,
        "sources": sources,
        "sync_result": {**sync_result, **stream_sync},
    }, json_dumps_params={"default": str})
