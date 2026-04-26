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
from collections.abc import Callable
from typing import Any

from django.http import HttpRequest, JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods

from scp_cv.apps.playback.models import PlaybackCommand
from scp_cv.services.display import build_left_right_splice_target, list_display_targets
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
from scp_cv.services.playback import (
    VALID_WINDOW_IDS,
    PlaybackError,
    close_source,
    control_playback,
    get_all_sessions_snapshot,
    get_or_create_session,
    get_session_snapshot,
    is_splice_mode_active,
    navigate_content,
    open_source,
    select_display_target,
    set_splice_mode,
    toggle_loop_playback,
)
from scp_cv.services.scenario import (
    ScenarioError,
    activate_scenario,
    capture_scenario_from_current_state,
    create_scenario,
    delete_scenario,
    list_scenarios,
    update_scenario,
)
from scp_cv.services.scenario import _scenario_to_dict
from scp_cv.services.sse import event_stream, publish_event


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


def _int_value(body: dict[str, Any], field_name: str, default: int = 0) -> int:
    """
    从请求体提取整数。
    :param body: JSON 请求体
    :param field_name: 字段名
    :param default: 缺省值
    :return: 整数值
    """
    raw_value = body.get(field_name, default)
    try:
        return int(raw_value)
    except (TypeError, ValueError):
        return default


def _bool_value(body: dict[str, Any], field_name: str, default: bool = False) -> bool:
    """
    从请求体提取布尔值，兼容字符串表单值。
    :param body: JSON 请求体
    :param field_name: 字段名
    :param default: 缺省值
    :return: 布尔值
    """
    if field_name not in body:
        return default
    raw_value = body[field_name]
    if isinstance(raw_value, bool):
        return raw_value
    return str(raw_value).strip().lower() in {"true", "1", "yes", "on"}


def _parse_window_id(raw_window_id: int | str) -> int:
    """
    解析并校验窗口编号。
    :param raw_window_id: URL 捕获的窗口编号
    :return: 有效窗口编号
    :raises PlaybackError: 窗口编号无效时
    """
    try:
        window_id = int(raw_window_id)
    except (TypeError, ValueError) as parse_error:
        raise PlaybackError(f"window_id 格式无效：{raw_window_id}") from parse_error
    if window_id not in VALID_WINDOW_IDS:
        raise PlaybackError(f"window_id 不在有效范围内：{window_id}")
    return window_id


def _mutate_playback(operation: Callable[[], Any]) -> JsonResponse:
    """
    执行会改变播放状态的操作，并发布统一状态事件。
    :param operation: 业务操作回调
    :return: 包含全量会话快照的 JSON 响应
    """
    operation()
    sessions = get_all_sessions_snapshot()
    payload = {"sessions": sessions, "splice_active": is_splice_mode_active()}
    publish_event("playback_state", payload)
    return _json_response({"success": True, **payload})


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
    return _json_response({
        "success": True,
        "sources": list_media_sources(source_type_filter),
        "sync_result": {**sync_result, **stream_sync},
    })


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
        source = add_web_url(web_url, str(body.get("name", "")).strip() or None)
    except MediaError as media_error:
        return _error_response(str(media_error), code="media_error")

    return _json_response({"success": True, "source": _source_payload(source)}, status=201)


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
def list_sessions_api(request: HttpRequest) -> JsonResponse:
    """
    获取全部窗口会话快照。
    :param request: HTTP 请求
    :return: 会话快照列表
    """
    return _json_response({
        "success": True,
        "sessions": get_all_sessions_snapshot(),
        "splice_active": is_splice_mode_active(),
    })


@require_GET
def session_detail_api(request: HttpRequest, window_id: int) -> JsonResponse:
    """
    获取单个窗口会话快照。
    :param request: HTTP 请求
    :param window_id: 窗口编号
    :return: 会话快照
    """
    try:
        parsed_window_id = _parse_window_id(window_id)
    except PlaybackError as playback_error:
        return _error_response(str(playback_error), code="invalid_window")
    return _json_response({"success": True, "session": get_session_snapshot(parsed_window_id)})


@csrf_exempt
@require_http_methods(["POST"])
def open_source_api(request: HttpRequest, window_id: int) -> JsonResponse:
    """
    打开媒体源到指定窗口。
    :param request: HTTP 请求
    :param window_id: 窗口编号
    :return: 操作后的会话状态
    """
    body, error = _body_or_error(request)
    if error is not None:
        return error
    try:
        parsed_window_id = _parse_window_id(window_id)
        media_source_id = _int_value(body, "source_id") or _int_value(body, "media_source_id")
        if media_source_id <= 0:
            return _error_response("source_id 必须大于 0", code="invalid_source")
        return _mutate_playback(lambda: open_source(
            parsed_window_id, media_source_id, _bool_value(body, "autoplay", True),
        ))
    except PlaybackError as playback_error:
        return _error_response(str(playback_error), code="playback_error")


@csrf_exempt
@require_http_methods(["POST"])
def playback_control_api(request: HttpRequest, window_id: int) -> JsonResponse:
    """
    发送播放、暂停或停止指令。
    :param request: HTTP 请求
    :param window_id: 窗口编号
    :return: 操作后的会话状态
    """
    body, error = _body_or_error(request)
    if error is not None:
        return error
    action = str(body.get("action", "")).strip()
    if not action:
        return _error_response("缺少 action 字段", code="missing_action")
    try:
        return _mutate_playback(lambda: control_playback(_parse_window_id(window_id), action))
    except PlaybackError as playback_error:
        return _error_response(str(playback_error), code="playback_error")


@csrf_exempt
@require_http_methods(["POST"])
def navigate_content_api(request: HttpRequest, window_id: int) -> JsonResponse:
    """
    发送翻页、跳页或 seek 指令。
    :param request: HTTP 请求
    :param window_id: 窗口编号
    :return: 操作后的会话状态
    """
    body, error = _body_or_error(request)
    if error is not None:
        return error
    action = str(body.get("action", "")).strip()
    if not action:
        return _error_response("缺少 action 字段", code="missing_action")
    try:
        return _mutate_playback(lambda: navigate_content(
            _parse_window_id(window_id),
            action,
            target_index=_int_value(body, "target_index"),
            position_ms=_int_value(body, "position_ms"),
        ))
    except PlaybackError as playback_error:
        return _error_response(str(playback_error), code="playback_error")


@csrf_exempt
@require_http_methods(["POST"])
def close_source_api(request: HttpRequest, window_id: int) -> JsonResponse:
    """
    关闭指定窗口媒体源。
    :param request: HTTP 请求
    :param window_id: 窗口编号
    :return: 操作后的会话状态
    """
    try:
        return _mutate_playback(lambda: close_source(_parse_window_id(window_id)))
    except PlaybackError as playback_error:
        return _error_response(str(playback_error), code="playback_error")


@csrf_exempt
@require_http_methods(["PATCH"])
def toggle_loop_api(request: HttpRequest, window_id: int) -> JsonResponse:
    """
    设置指定窗口循环播放状态。
    :param request: HTTP 请求
    :param window_id: 窗口编号
    :return: 操作后的会话状态
    """
    body, error = _body_or_error(request)
    if error is not None:
        return error
    try:
        return _mutate_playback(lambda: toggle_loop_playback(
            _parse_window_id(window_id), _bool_value(body, "enabled"),
        ))
    except PlaybackError as playback_error:
        return _error_response(str(playback_error), code="playback_error")


@csrf_exempt
@require_http_methods(["POST"])
def set_splice_mode_api(request: HttpRequest) -> JsonResponse:
    """
    设置窗口 1+2 拼接模式。
    :param request: HTTP 请求
    :return: 操作后的会话状态
    """
    body, error = _body_or_error(request)
    if error is not None:
        return error
    try:
        return _mutate_playback(lambda: set_splice_mode(_bool_value(body, "enabled")))
    except PlaybackError as playback_error:
        return _error_response(str(playback_error), code="playback_error")


@csrf_exempt
@require_http_methods(["POST"])
def show_window_ids_api(request: HttpRequest) -> JsonResponse:
    """
    下发所有窗口显示 ID 指令。
    :param request: HTTP 请求
    :return: 操作后的会话状态
    """
    def apply_show_id() -> None:
        for window_id in VALID_WINDOW_IDS:
            session = get_or_create_session(window_id)
            session.pending_command = PlaybackCommand.SHOW_ID
            session.command_args = {}
            session.save(update_fields=["pending_command", "command_args"])

    return _mutate_playback(apply_show_id)


@require_GET
def list_displays_api(request: HttpRequest) -> JsonResponse:
    """
    获取显示器列表和左右拼接标签。
    :param request: HTTP 请求
    :return: 显示器列表
    """
    display_targets = list_display_targets()
    splice_target = build_left_right_splice_target(display_targets)
    return _json_response({
        "success": True,
        "targets": [target.__dict__ for target in display_targets],
        "splice_label": (
            f"{splice_target.left.name} + {splice_target.right.name}"
            if splice_target is not None else ""
        ),
    })


@csrf_exempt
@require_http_methods(["POST"])
def select_display_api(request: HttpRequest) -> JsonResponse:
    """
    切换指定窗口显示目标。
    :param request: HTTP 请求
    :return: 操作后的会话状态
    """
    body, error = _body_or_error(request)
    if error is not None:
        return error
    try:
        return _mutate_playback(lambda: select_display_target(
            _int_value(body, "window_id", 1),
            str(body.get("display_mode", "single")).strip(),
            str(body.get("target_label", "")).strip(),
        ))
    except PlaybackError as playback_error:
        return _error_response(str(playback_error), code="playback_error")


@csrf_exempt
@require_http_methods(["GET", "POST"])
def list_scenarios_api(request: HttpRequest) -> JsonResponse:
    """
    获取预案列表或创建预案。
    :param request: HTTP 请求
    :return: 预案列表或创建结果
    """
    if request.method == "POST":
        return create_scenario_api(request)
    return _json_response({"success": True, "scenarios": list_scenarios()})


@csrf_exempt
@require_http_methods(["POST"])
def create_scenario_api(request: HttpRequest) -> JsonResponse:
    """
    创建预案。
    :param request: HTTP 请求
    :return: 创建结果
    """
    body, error = _body_or_error(request)
    if error is not None:
        return error
    name = str(body.get("name", "")).strip()
    if not name:
        return _error_response("缺少 name 字段", code="missing_name")
    try:
        scenario = create_scenario(
            name=name,
            description=str(body.get("description", "")),
            is_splice_mode=_bool_value(body, "is_splice_mode"),
            window1_source_id=_int_value(body, "window1_source_id") or None,
            window1_autoplay=_bool_value(body, "window1_autoplay", True),
            window1_resume=_bool_value(body, "window1_resume", True),
            window2_source_id=_int_value(body, "window2_source_id") or None,
            window2_autoplay=_bool_value(body, "window2_autoplay", True),
            window2_resume=_bool_value(body, "window2_resume", True),
        )
    except ScenarioError as scenario_error:
        return _error_response(str(scenario_error), code="scenario_error")
    return _json_response({"success": True, "scenario": _scenario_to_dict(scenario)}, status=201)


@csrf_exempt
@require_http_methods(["PATCH", "DELETE"])
def scenario_detail_api(request: HttpRequest, scenario_id: int) -> JsonResponse:
    """
    更新或删除指定预案。
    :param request: HTTP 请求
    :param scenario_id: 预案主键
    :return: 操作结果
    """
    if request.method == "DELETE":
        try:
            delete_scenario(int(scenario_id))
        except ScenarioError as scenario_error:
            return _error_response(str(scenario_error), code="scenario_error", status=404)
        return _json_response({"success": True})

    body, error = _body_or_error(request)
    if error is not None:
        return error
    try:
        scenario = update_scenario(
            scenario_id=int(scenario_id),
            name=body.get("name") if "name" in body else None,
            description=body.get("description") if "description" in body else None,
            is_splice_mode=_bool_value(body, "is_splice_mode") if "is_splice_mode" in body else None,
            window1_source_id=_int_value(body, "window1_source_id") or None,
            window1_autoplay=_bool_value(body, "window1_autoplay", True) if "window1_autoplay" in body else None,
            window1_resume=_bool_value(body, "window1_resume", True) if "window1_resume" in body else None,
            window2_source_id=_int_value(body, "window2_source_id") or None,
            window2_autoplay=_bool_value(body, "window2_autoplay", True) if "window2_autoplay" in body else None,
            window2_resume=_bool_value(body, "window2_resume", True) if "window2_resume" in body else None,
            _window1_source_provided="window1_source_id" in body,
            _window2_source_provided="window2_source_id" in body,
        )
    except ScenarioError as scenario_error:
        return _error_response(str(scenario_error), code="scenario_error")
    return _json_response({"success": True, "scenario": _scenario_to_dict(scenario)})


@csrf_exempt
@require_http_methods(["POST"])
def activate_scenario_api(request: HttpRequest, scenario_id: int) -> JsonResponse:
    """
    激活指定预案。
    :param request: HTTP 请求
    :param scenario_id: 预案主键
    :return: 激活后的会话状态
    """
    try:
        sessions = activate_scenario(int(scenario_id))
        payload = {"sessions": sessions, "splice_active": is_splice_mode_active()}
        publish_event("playback_state", payload)
        return _json_response({"success": True, **payload})
    except ScenarioError as scenario_error:
        return _error_response(str(scenario_error), code="scenario_error")


@csrf_exempt
@require_http_methods(["POST"])
def capture_scenario_api(request: HttpRequest) -> JsonResponse:
    """
    从当前窗口 1/2 状态捕获预案。
    :param request: HTTP 请求
    :return: 捕获结果
    """
    body, error = _body_or_error(request)
    if error is not None:
        return error
    name = str(body.get("name", "")).strip()
    if not name:
        return _error_response("缺少 name 字段", code="missing_name")
    try:
        scenario = capture_scenario_from_current_state(
            name=name,
            description=str(body.get("description", "")),
            scenario_id=_int_value(body, "scenario_id") or None,
        )
    except ScenarioError as scenario_error:
        return _error_response(str(scenario_error), code="scenario_error")
    return _json_response({"success": True, "scenario": _scenario_to_dict(scenario)})


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
