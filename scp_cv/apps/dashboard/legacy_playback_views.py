#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
旧版表单播放控制、状态查询与 SSE 视图。
@Project : SCP-cv
@File : legacy_playback_views.py
@Author : Qintsg
@Date : 2026-07-11
'''
from __future__ import annotations

from django.http import HttpRequest, JsonResponse, StreamingHttpResponse
from django.views.decorators.http import require_GET, require_POST

from scp_cv.services.command_status import (
    capture_enqueued_commands,
    control_command_payloads,
)
from scp_cv.services.playback import (
    VALID_WINDOW_IDS,
    PlaybackError,
    close_source,
    control_playback,
    get_all_sessions_snapshot,
    get_session_snapshot,
    navigate_content,
    open_source,
    toggle_loop_playback,
)
from scp_cv.services.sse import event_stream, publish_event


def _parse_window_id(raw_window_id: str) -> int:
    """解析并校验路径中的 window_id。"""
    try:
        window_id = int(raw_window_id)
    except (ValueError, TypeError) as parse_err:
        raise PlaybackError(f"window_id 格式无效：{raw_window_id}") from parse_err
    if window_id not in VALID_WINDOW_IDS:
        raise PlaybackError(f"window_id 不在有效范围内：{window_id}")
    return window_id


@require_POST
def open_media_source(request: HttpRequest, window_id: str) -> JsonResponse:
    """
    打开指定媒体源到指定窗口。
    :param request: HTTP 请求（POST form，包含 source_id 字段）
    :param window_id: URL 路径中的窗口编号
    :return: JSON 响应
    """
    try:
        wid = _parse_window_id(window_id)
    except PlaybackError as wid_err:
        return JsonResponse({"success": False, "error": str(wid_err)}, status=400)

    source_id = request.POST.get("source_id")
    if not source_id:
        return JsonResponse({"success": False, "error": "缺少 source_id"}, status=400)

    try:
        source_id_int = int(source_id)
    except (ValueError, TypeError):
        return JsonResponse({"success": False, "error": "source_id 格式无效"}, status=400)

    autoplay = request.POST.get("autoplay", "true").lower() in ("true", "1", "yes")
    try:
        with capture_enqueued_commands() as accepted_commands:
            open_source(wid, source_id_int, autoplay=autoplay)
    except PlaybackError as open_err:
        return JsonResponse({"success": False, "error": str(open_err)}, status=400)

    snapshot = get_session_snapshot(wid)
    publish_event("playback_state", snapshot)
    return JsonResponse({
        "success": True,
        "session": snapshot,
        "commands": control_command_payloads(accepted_commands),
    })


@require_POST
def playback_control(request: HttpRequest, window_id: str) -> JsonResponse:
    """
    播放控制（play / pause / stop）。
    :param request: HTTP 请求（POST form，包含 action 字段）
    :param window_id: URL 路径中的窗口编号
    :return: JSON 响应
    """
    try:
        wid = _parse_window_id(window_id)
    except PlaybackError as wid_err:
        return JsonResponse({"success": False, "error": str(wid_err)}, status=400)

    action = request.POST.get("action", "").strip()
    if not action:
        return JsonResponse({"success": False, "error": "缺少 action 字段"}, status=400)

    try:
        with capture_enqueued_commands() as accepted_commands:
            control_playback(wid, action)
    except PlaybackError as ctrl_err:
        return JsonResponse({"success": False, "error": str(ctrl_err)}, status=400)

    snapshot = get_session_snapshot(wid)
    publish_event("playback_state", snapshot)
    return JsonResponse({
        "success": True,
        "session": snapshot,
        "commands": control_command_payloads(accepted_commands),
    })


@require_POST
def navigate(request: HttpRequest, window_id: str) -> JsonResponse:
    """
    内容导航（下一页/上一页/跳转/Seek）。
    :param request: HTTP 请求（POST form，包含 action 字段）
    :param window_id: URL 路径中的窗口编号
    :return: JSON 响应
    """
    try:
        wid = _parse_window_id(window_id)
    except PlaybackError as wid_err:
        return JsonResponse({"success": False, "error": str(wid_err)}, status=400)

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
        with capture_enqueued_commands() as accepted_commands:
            navigate_content(
                wid,
                action,
                target_index=target_index,
                position_ms=position_ms,
            )
    except PlaybackError as nav_err:
        return JsonResponse({"success": False, "error": str(nav_err)}, status=400)

    snapshot = get_session_snapshot(wid)
    publish_event("playback_state", snapshot)
    return JsonResponse({
        "success": True,
        "session": snapshot,
        "commands": control_command_payloads(accepted_commands),
    })


@require_POST
def close_current(request: HttpRequest, window_id: str) -> JsonResponse:
    """
    关闭指定窗口当前播放的源。
    :param request: HTTP 请求
    :param window_id: URL 路径中的窗口编号
    :return: JSON 响应
    """
    try:
        wid = _parse_window_id(window_id)
    except PlaybackError as wid_err:
        return JsonResponse({"success": False, "error": str(wid_err)}, status=400)

    try:
        with capture_enqueued_commands() as accepted_commands:
            close_source(wid)
    except PlaybackError as close_err:
        return JsonResponse({"success": False, "error": str(close_err)}, status=400)

    snapshot = get_session_snapshot(wid)
    publish_event("playback_state", snapshot)
    return JsonResponse({
        "success": True,
        "session": snapshot,
        "commands": control_command_payloads(accepted_commands),
    })


@require_POST
def toggle_loop(request: HttpRequest, window_id: str) -> JsonResponse:
    """
    切换指定窗口的循环播放状态。
    :param request: HTTP 请求（POST form，包含 enabled 字段）
    :param window_id: URL 路径中的窗口编号
    :return: JSON 响应
    """
    try:
        wid = _parse_window_id(window_id)
    except PlaybackError as wid_err:
        return JsonResponse({"success": False, "error": str(wid_err)}, status=400)

    enabled_raw = request.POST.get("enabled", "false").strip().lower()
    loop_enabled = enabled_raw in ("true", "1", "yes")
    try:
        with capture_enqueued_commands() as accepted_commands:
            toggle_loop_playback(wid, loop_enabled)
    except PlaybackError as loop_err:
        return JsonResponse({"success": False, "error": str(loop_err)}, status=400)

    snapshot = get_session_snapshot(wid)
    publish_event("playback_state", snapshot)
    return JsonResponse({
        "success": True,
        "session": snapshot,
        "commands": control_command_payloads(accepted_commands),
    })


@require_POST
def show_window_ids(request: HttpRequest) -> JsonResponse:
    """
    触发所有输出窗口显示 5 秒窗口 ID 叠加标识。
    向每个窗口追加 SHOW_ID ControlCommand，播放器原子认领后
    会在窗口上渲染半透明 ID 文字。
    :param request: HTTP 请求（POST）
    :return: JSON 响应
    """
    from scp_cv.services.playback import request_show_window_ids

    with capture_enqueued_commands() as accepted_commands:
        request_show_window_ids()
    return JsonResponse({
        "success": True,
        "commands": control_command_payloads(accepted_commands),
    })


@require_GET
def api_session_state(request: HttpRequest) -> JsonResponse:
    """
    获取所有窗口播放会话状态。
    可选 ?window_id=N 获取单个窗口状态。
    :param request: HTTP 请求
    :return: JSON 格式的会话快照
    """
    single_window = request.GET.get("window_id", "").strip()
    if single_window:
        try:
            wid = _parse_window_id(single_window)
        except PlaybackError as wid_err:
            return JsonResponse({"success": False, "error": str(wid_err)}, status=400)
        snapshot = get_session_snapshot(wid)
        return JsonResponse({"success": True, "session": snapshot})

    all_snapshots = get_all_sessions_snapshot()
    return JsonResponse({
        "success": True,
        "sessions": all_snapshots,
    })


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
