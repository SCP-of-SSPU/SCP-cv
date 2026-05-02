#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
播放与显示布局 REST API 视图。
@Project : SCP-cv
@File : api_playback_views.py
@Author : Qintsg
@Date : 2026-04-27
'''
from __future__ import annotations

from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods

from scp_cv.apps.dashboard.api_utils import (
    body_or_error,
    bool_value,
    error_response,
    int_value,
    json_response,
    mutate_playback,
    parse_window_id,
)
from scp_cv.apps.playback.models import PlaybackCommand
from scp_cv.services.display import build_left_right_splice_target, list_display_targets
from scp_cv.services.playback import (
    VALID_WINDOW_IDS,
    PlaybackError,
    close_source,
    control_ppt_media,
    control_playback,
    get_all_sessions_snapshot,
    get_or_create_session,
    get_runtime_snapshot,
    get_session_snapshot,
    navigate_content,
    open_source,
    select_display_target,
    set_big_screen_mode,
    set_window_mute,
    set_window_volume,
    toggle_loop_playback,
)
from scp_cv.services.volume import VolumeError, get_system_volume, set_system_volume


@require_GET
def list_sessions_api(request: HttpRequest) -> JsonResponse:
    """
    获取全部窗口会话快照。
    :param request: HTTP 请求
    :return: 会话快照列表
    """
    return json_response({"success": True, "sessions": get_all_sessions_snapshot()})


@require_GET
def session_detail_api(request: HttpRequest, window_id: int) -> JsonResponse:
    """
    获取单个窗口会话快照。
    :param request: HTTP 请求
    :param window_id: 窗口编号
    :return: 会话快照
    """
    try:
        parsed_window_id = parse_window_id(window_id)
    except PlaybackError as playback_error:
        return error_response(str(playback_error), code="invalid_window")
    return json_response({"success": True, "session": get_session_snapshot(parsed_window_id)})


@csrf_exempt
@require_http_methods(["POST"])
def open_source_api(request: HttpRequest, window_id: int) -> JsonResponse:
    """
    打开媒体源到指定窗口。
    :param request: HTTP 请求
    :param window_id: 窗口编号
    :return: 操作后的会话状态
    """
    body, error = body_or_error(request)
    if error is not None:
        return error
    try:
        parsed_window_id = parse_window_id(window_id)
        media_source_id = int_value(body, "source_id") or int_value(body, "media_source_id")
        if media_source_id <= 0:
            return error_response("source_id 必须大于 0", code="invalid_source")
        return mutate_playback(lambda: open_source(
            parsed_window_id, media_source_id, bool_value(body, "autoplay", True),
        ))
    except PlaybackError as playback_error:
        return error_response(str(playback_error), code="playback_error")


@csrf_exempt
@require_http_methods(["POST"])
def playback_control_api(request: HttpRequest, window_id: int) -> JsonResponse:
    """
    发送播放、暂停或停止指令。
    :param request: HTTP 请求
    :param window_id: 窗口编号
    :return: 操作后的会话状态
    """
    body, error = body_or_error(request)
    if error is not None:
        return error
    action = str(body.get("action", "")).strip()
    if not action:
        return error_response("缺少 action 字段", code="missing_action")
    try:
        return mutate_playback(lambda: control_playback(parse_window_id(window_id), action))
    except PlaybackError as playback_error:
        return error_response(str(playback_error), code="playback_error")


@csrf_exempt
@require_http_methods(["POST"])
def navigate_content_api(request: HttpRequest, window_id: int) -> JsonResponse:
    """
    发送翻页、跳页或 seek 指令。
    :param request: HTTP 请求
    :param window_id: 窗口编号
    :return: 操作后的会话状态
    """
    body, error = body_or_error(request)
    if error is not None:
        return error
    action = str(body.get("action", "")).strip()
    if not action:
        return error_response("缺少 action 字段", code="missing_action")
    try:
        return mutate_playback(lambda: navigate_content(
            parse_window_id(window_id),
            action,
            target_index=int_value(body, "target_index"),
            position_ms=int_value(body, "position_ms"),
        ))
    except PlaybackError as playback_error:
        return error_response(str(playback_error), code="playback_error")


@csrf_exempt
@require_http_methods(["POST"])
def ppt_media_control_api(request: HttpRequest, window_id: int) -> JsonResponse:
    """
    控制 PPT 当前页中的单个媒体对象。
    :param request: HTTP 请求
    :param window_id: 窗口编号
    :return: 操作后的会话状态
    """
    body, error = body_or_error(request)
    if error is not None:
        return error
    media_action = str(body.get("action", "")).strip()
    if not media_action:
        return error_response("缺少 action 字段", code="missing_action")
    try:
        return mutate_playback(lambda: control_ppt_media(
            parse_window_id(window_id),
            media_action,
            media_id=str(body.get("media_id", "")),
            media_index=int_value(body, "media_index"),
        ))
    except PlaybackError as playback_error:
        return error_response(str(playback_error), code="playback_error")


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
        return mutate_playback(lambda: close_source(parse_window_id(window_id)))
    except PlaybackError as playback_error:
        return error_response(str(playback_error), code="playback_error")


@csrf_exempt
@require_http_methods(["PATCH"])
def toggle_loop_api(request: HttpRequest, window_id: int) -> JsonResponse:
    """
    设置指定窗口循环播放状态。
    :param request: HTTP 请求
    :param window_id: 窗口编号
    :return: 操作后的会话状态
    """
    body, error = body_or_error(request)
    if error is not None:
        return error
    try:
        return mutate_playback(lambda: toggle_loop_playback(
            parse_window_id(window_id), bool_value(body, "enabled"),
        ))
    except PlaybackError as playback_error:
        return error_response(str(playback_error), code="playback_error")


@csrf_exempt
@require_http_methods(["PATCH"])
def set_window_volume_api(request: HttpRequest, window_id: int) -> JsonResponse:
    """
    设置指定窗口音量。
    :param request: HTTP 请求
    :param window_id: 窗口编号
    :return: 操作后的会话状态
    """
    body, error = body_or_error(request)
    if error is not None:
        return error
    try:
        return mutate_playback(lambda: set_window_volume(
            parse_window_id(window_id), int_value(body, "volume", 100),
        ))
    except PlaybackError as playback_error:
        return error_response(str(playback_error), code="playback_error")


@csrf_exempt
@require_http_methods(["PATCH"])
def set_window_mute_api(request: HttpRequest, window_id: int) -> JsonResponse:
    """
    设置指定窗口静音状态。
    :param request: HTTP 请求
    :param window_id: 窗口编号
    :return: 操作后的会话状态
    """
    body, error = body_or_error(request)
    if error is not None:
        return error
    try:
        return mutate_playback(lambda: set_window_mute(
            parse_window_id(window_id), bool_value(body, "muted"),
        ))
    except PlaybackError as playback_error:
        return error_response(str(playback_error), code="playback_error")


@csrf_exempt
@require_http_methods(["GET", "PATCH"])
def runtime_state_api(request: HttpRequest) -> JsonResponse:
    """
    获取或设置全局运行状态。
    :param request: HTTP 请求
    :return: 运行状态快照
    """
    if request.method == "GET":
        return json_response({"success": True, "runtime": get_runtime_snapshot()})

    body, error = body_or_error(request)
    if error is not None:
        return error
    try:
        runtime = set_big_screen_mode(str(body.get("big_screen_mode", "")).strip())
    except PlaybackError as playback_error:
        return error_response(str(playback_error), code="playback_error")
    sessions = get_all_sessions_snapshot()
    return json_response({"success": True, "runtime": runtime, "sessions": sessions})


@csrf_exempt
@require_http_methods(["GET", "PATCH"])
def system_volume_api(request: HttpRequest) -> JsonResponse:
    """
    获取或设置系统音量状态。
    :param request: HTTP 请求
    :return: 系统音量状态
    """
    if request.method == "GET":
        return json_response({"success": True, "volume": get_system_volume()})

    body, error = body_or_error(request)
    if error is not None:
        return error
    try:
        level = int_value(body, "level", -1)
        volume = set_system_volume(
            level if level >= 0 else None,
            bool_value(body, "muted") if "muted" in body else None,
        )
    except VolumeError as volume_error:
        return error_response(str(volume_error), code="volume_error")
    return json_response({"success": True, "volume": volume})


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

    return mutate_playback(apply_show_id)


@require_GET
def list_displays_api(request: HttpRequest) -> JsonResponse:
    """
    获取显示器列表和左右拼接标签。
    :param request: HTTP 请求
    :return: 显示器列表
    """
    display_targets = list_display_targets()
    splice_target = build_left_right_splice_target(display_targets)
    return json_response({
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
    body, error = body_or_error(request)
    if error is not None:
        return error
    try:
        return mutate_playback(lambda: select_display_target(
            int_value(body, "window_id", 1),
            str(body.get("display_mode", "single")).strip(),
            str(body.get("target_label", "")).strip(),
        ))
    except PlaybackError as playback_error:
        return error_response(str(playback_error), code="playback_error")
