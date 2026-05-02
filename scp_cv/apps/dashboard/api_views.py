#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
控制台 REST API 视图。
为 Vue 前端提供前后端分离调用入口，业务逻辑继续复用 services 层。
@Project : SCP-cv
@File : api_views.py
@Author : Qintsg
@Date : 2026-04-26
'''
from __future__ import annotations

import json
from typing import Any

from django.http import FileResponse, HttpRequest, JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods

from scp_cv.services.media import (
    MediaError,
    add_local_path,
    add_uploaded_file,
    add_web_url,
    create_folder,
    delete_media_source,
    delete_folder,
    get_source_download_info,
    list_folders,
    list_media_sources,
    list_ppt_resources,
    move_source,
    replace_ppt_resources,
    sync_streams_to_media_sources,
    update_folder,
)
from scp_cv.services.mediamtx import sync_stream_states
from scp_cv.services.device import (
    DeviceError,
    list_devices,
    power_off_device,
    power_on_device,
    toggle_device,
)
from scp_cv.services.sse import event_stream


def _json_response(payload: dict[str, Any], status: int = 200) -> JsonResponse:
    """
    返回统一 JSON 响应，允许 datetime 等对象转换为字符串。
    :param payload: 响应体
    :param status: HTTP 状态码
    :return: JsonResponse 实例
    """
    return JsonResponse(payload, status=status, json_dumps_params={"default": str})


def _error_response(message: str, code: str = "bad_request", status: int = 400) -> JsonResponse:
    """
    返回统一错误响应。
    :param message: 错误描述
    :param code: 稳定错误码
    :param status: HTTP 状态码
    :return: JsonResponse 实例
    """
    return _json_response({"detail": message, "code": code}, status=status)


def _parse_json_body(request: HttpRequest) -> dict[str, Any]:
    """
    解析 JSON 请求体；空请求体返回空字典。
    :param request: HTTP 请求
    :return: JSON 字典
    :raises ValueError: JSON 不是对象或格式错误时
    """
    if not request.body:
        return {}
    try:
        body = json.loads(request.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as parse_error:
        raise ValueError("请求体必须是合法 JSON") from parse_error
    if not isinstance(body, dict):
        raise ValueError("请求体必须是 JSON 对象")
    return body


def _body_or_error(request: HttpRequest) -> tuple[dict[str, Any] | None, JsonResponse | None]:
    """
    安全解析请求体，避免每个视图重复 try/except。
    :param request: HTTP 请求
    :return: (body, error_response)
    """
    try:
        return _parse_json_body(request), None
    except ValueError as body_error:
        return None, _error_response(str(body_error), code="invalid_json")


def _optional_int(raw_value: object, default: int | None = None) -> int | None:
    """
    将请求中的可选整数转换为 int。
    :param raw_value: 原始请求值
    :param default: 解析失败或空值时的默认值
    :return: 转换后的整数或默认值
    """
    if raw_value in (None, ""):
        return default
    try:
        return int(raw_value)
    except (TypeError, ValueError):
        return default


def _bool_value(raw_value: object, default: bool = False) -> bool:
    """
    兼容 JSON 和表单字符串的布尔值解析。
    :param raw_value: 原始请求值
    :param default: 缺省值
    :return: 布尔值
    """
    if raw_value is None:
        return default
    if isinstance(raw_value, bool):
        return raw_value
    return str(raw_value).strip().lower() in {"true", "1", "yes", "on"}


def _source_payload(source: object) -> dict[str, Any]:
    """
    将 MediaSource 实例序列化为 API 响应字段。
    :param source: MediaSource 实例
    :return: 媒体源字典
    """
    return {
        "id": source.pk,
        "source_type": source.source_type,
        "name": source.name,
        "uri": source.uri,
        "is_available": source.is_available,
        "stream_identifier": source.stream_identifier,
        "folder_id": source.folder_id,
        "original_filename": source.original_filename,
        "file_size": source.file_size,
        "mime_type": source.mime_type,
        "is_temporary": source.is_temporary,
        "expires_at": source.expires_at.isoformat() if source.expires_at else None,
        "metadata": source.metadata,
        "created_at": source.created_at.isoformat() if source.created_at else "",
    }


@require_GET
def list_sources_api(request: HttpRequest) -> JsonResponse:
    """
    获取媒体源列表，查询时同步外部流状态。
    :param request: HTTP 请求
    :return: 媒体源列表响应
    """
    sync_result = sync_stream_states()
    stream_sync = sync_streams_to_media_sources()
    source_type_filter = request.GET.get("source_type", "").strip() or None
    folder_id_filter = _optional_int(request.GET.get("folder_id"))
    return _json_response({
        "success": True,
        "sources": list_media_sources(source_type_filter, folder_id_filter),
        "sync_result": {**sync_result, **stream_sync},
    })


@csrf_exempt
@require_http_methods(["GET", "POST"])
def folders_api(request: HttpRequest) -> JsonResponse:
    """
    获取或创建媒体文件夹。
    :param request: HTTP 请求
    :return: 文件夹列表或创建结果
    """
    if request.method == "GET":
        return _json_response({"success": True, "folders": list_folders()})

    body, error = _body_or_error(request)
    if error is not None:
        return error
    try:
        folder = create_folder(
            name=str(body.get("name", "")),
            parent_id=_optional_int(body.get("parent_id")),
        )
    except MediaError as media_error:
        return _error_response(str(media_error), code="media_error")
    return _json_response({"success": True, "folder": {
        "id": folder.pk,
        "name": folder.name,
        "parent_id": folder.parent_id,
        "created_at": folder.created_at,
        "updated_at": folder.updated_at,
    }}, status=201)


@csrf_exempt
@require_http_methods(["PATCH", "DELETE"])
def folder_detail_api(request: HttpRequest, folder_id: int) -> JsonResponse:
    """
    更新或删除媒体文件夹。
    :param request: HTTP 请求
    :param folder_id: 文件夹主键
    :return: 操作结果
    """
    if request.method == "DELETE":
        try:
            delete_folder(int(folder_id))
        except MediaError as media_error:
            return _error_response(str(media_error), code="media_error", status=404)
        return _json_response({"success": True})

    body, error = _body_or_error(request)
    if error is not None:
        return error
    try:
        folder = update_folder(
            folder_id=int(folder_id),
            name=str(body.get("name")) if "name" in body else None,
            parent_id=_optional_int(body.get("parent_id")) if "parent_id" in body else None,
        )
    except MediaError as media_error:
        return _error_response(str(media_error), code="media_error")
    return _json_response({"success": True, "folder": {
        "id": folder.pk,
        "name": folder.name,
        "parent_id": folder.parent_id,
    }})


@csrf_exempt
@require_http_methods(["POST"])
def upload_source_api(request: HttpRequest) -> JsonResponse:
    """
    通过 multipart 文件上传创建媒体源。
    :param request: HTTP 请求
    :return: 创建结果
    """
    uploaded_file = request.FILES.get("file")
    if uploaded_file is None:
        return _error_response("缺少 file 字段", code="missing_file")

    try:
        source = add_uploaded_file(
            uploaded_file=uploaded_file,
            display_name=request.POST.get("name", "").strip() or None,
            source_type=request.POST.get("source_type", "").strip() or None,
            folder_id=_optional_int(request.POST.get("folder_id")),
            is_temporary=_bool_value(request.POST.get("is_temporary")),
        )
    except MediaError as media_error:
        return _error_response(str(media_error), code="media_error")

    return _json_response({"success": True, "source": _source_payload(source)}, status=201)


@csrf_exempt
@require_http_methods(["POST"])
def add_local_source_api(request: HttpRequest) -> JsonResponse:
    """
    通过本地文件路径创建媒体源。
    :param request: HTTP 请求
    :return: 创建结果
    """
    body, error = _body_or_error(request)
    if error is not None:
        return error
    local_path = str(body.get("path", "")).strip()
    if not local_path:
        return _error_response("缺少 path 字段", code="missing_path")

    try:
        source = add_local_path(
            local_path=local_path,
            display_name=str(body.get("name", "")).strip() or None,
            source_type=str(body.get("source_type", "")).strip() or None,
            folder_id=_optional_int(body.get("folder_id")),
        )
    except MediaError as media_error:
        return _error_response(str(media_error), code="media_error")

    return _json_response({"success": True, "source": _source_payload(source)}, status=201)


@csrf_exempt
@require_http_methods(["POST"])
def add_web_source_api(request: HttpRequest) -> JsonResponse:
    """
    通过 URL 创建网页媒体源。
    :param request: HTTP 请求
    :return: 创建结果
    """
    body, error = _body_or_error(request)
    if error is not None:
        return error
    web_url = str(body.get("url", "")).strip()
    if not web_url:
        return _error_response("缺少 url 字段", code="missing_url")

    try:
        source = add_web_url(
            web_url,
            str(body.get("name", "")).strip() or None,
            folder_id=_optional_int(body.get("folder_id")),
        )
    except MediaError as media_error:
        return _error_response(str(media_error), code="media_error")

    return _json_response({"success": True, "source": _source_payload(source)}, status=201)


@csrf_exempt
@require_http_methods(["PATCH"])
def move_source_api(request: HttpRequest, source_id: int) -> JsonResponse:
    """
    移动媒体源到指定文件夹。
    :param request: HTTP 请求
    :param source_id: 媒体源主键
    :return: 更新后的媒体源
    """
    body, error = _body_or_error(request)
    if error is not None:
        return error
    try:
        source = move_source(int(source_id), _optional_int(body.get("folder_id")))
    except MediaError as media_error:
        return _error_response(str(media_error), code="media_error", status=404)
    return _json_response({"success": True, "source": _source_payload(source)})


@require_GET
def download_source_api(request: HttpRequest, source_id: int) -> FileResponse | JsonResponse:
    """
    下载文件型媒体源。
    :param request: HTTP 请求
    :param source_id: 媒体源主键
    :return: 文件下载响应
    """
    try:
        file_path, file_name, mime_type = get_source_download_info(int(source_id))
    except MediaError as media_error:
        return _error_response(str(media_error), code="media_error", status=404)
    return FileResponse(open(file_path, "rb"), as_attachment=True, filename=file_name, content_type=mime_type)


@csrf_exempt
@require_http_methods(["GET", "PUT"])
def ppt_resources_api(request: HttpRequest, source_id: int) -> JsonResponse:
    """
    获取或覆盖 PPT 解析资源。
    :param request: HTTP 请求
    :param source_id: PPT 媒体源主键
    :return: PPT 资源列表
    """
    try:
        if request.method == "GET":
            resources = list_ppt_resources(int(source_id))
        else:
            body, error = _body_or_error(request)
            if error is not None:
                return error
            raw_resources = body.get("resources", [])
            if not isinstance(raw_resources, list):
                return _error_response("resources 必须是数组", code="invalid_resources")
            resources = replace_ppt_resources(int(source_id), raw_resources)
    except MediaError as media_error:
        return _error_response(str(media_error), code="media_error", status=400)
    return _json_response({"success": True, "resources": resources})


@csrf_exempt
@require_http_methods(["DELETE"])
def delete_source_api(request: HttpRequest, source_id: int) -> JsonResponse:
    """
    删除媒体源。
    :param request: HTTP 请求
    :param source_id: 媒体源主键
    :return: 删除结果
    """
    try:
        delete_media_source(int(source_id))
    except MediaError as media_error:
        return _error_response(str(media_error), code="media_error", status=404)
    return _json_response({"success": True})


@require_GET
def list_devices_api(request: HttpRequest) -> JsonResponse:
    """
    获取可控制设备列表。
    :param request: HTTP 请求
    :return: 设备状态列表
    """
    return _json_response({"success": True, "devices": list_devices()})


@csrf_exempt
@require_http_methods(["POST"])
def toggle_device_api(request: HttpRequest, device_type: str) -> JsonResponse:
    """
    切换设备开关机状态。
    :param request: HTTP 请求
    :param device_type: 设备类型
    :return: 更新后的设备状态
    """
    try:
        return _json_response({"success": True, "device": toggle_device(device_type)})
    except DeviceError as device_error:
        return _error_response(str(device_error), code="device_error", status=404)


@csrf_exempt
@require_http_methods(["POST"])
def power_device_api(request: HttpRequest, device_type: str, action: str) -> JsonResponse:
    """
    设置设备开机或关机状态。
    :param request: HTTP 请求
    :param device_type: 设备类型
    :param action: on 或 off
    :return: 更新后的设备状态
    """
    try:
        if action == "on":
            device = power_on_device(device_type)
        elif action == "off":
            device = power_off_device(device_type)
        else:
            return _error_response("action 必须是 on 或 off", code="invalid_action")
    except DeviceError as device_error:
        return _error_response(str(device_error), code="device_error", status=404)
    return _json_response({"success": True, "device": device})


@require_GET
def events_api(request: HttpRequest) -> StreamingHttpResponse:
    """
    播放状态 SSE 事件流。
    :param request: HTTP 请求
    :return: SSE 响应
    """
    try:
        last_sequence = int(request.GET.get("last_id", "0"))
    except (TypeError, ValueError):
        last_sequence = 0
    response = StreamingHttpResponse(event_stream(last_sequence), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response
