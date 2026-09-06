#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
背景音频 REST API 视图。
@Project : SCP-cv
@File : api_background_audio_views.py
@Author : Qintsg
@Date : 2026-05-31
'''
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods

from scp_cv.apps.dashboard.api_utils import body_or_error, bool_value, error_response, int_value, json_response
from scp_cv.services.background_audio import (
    BackgroundAudioError,
    add_source_to_playlist,
    clear_playlist,
    pause_background_audio,
    play_next_background_audio,
    play_playlist_item,
    play_previous_background_audio,
    play_source,
    remove_playlist_item,
    resume_background_audio,
    seek_background_audio,
    set_background_audio_loop,
    set_background_audio_mute,
    set_background_audio_volume,
    stop_background_audio,
)
from scp_cv.services.background_audio_payloads import get_background_audio_snapshot
from scp_cv.services.playback import get_all_sessions_snapshot
from scp_cv.services.sse import publish_event


def _mutate_background_audio(operation: Callable[[], Any]) -> JsonResponse:
    """
    执行背景音频变更并发布统一播放状态事件。

    :param operation: 业务操作回调
    :return: 最新背景音频快照响应
    """
    operation()
    snapshot = get_background_audio_snapshot()
    publish_event("playback_state", {
        "sessions": get_all_sessions_snapshot(),
        "background_audio": snapshot,
    })
    return json_response({"success": True, "background_audio": snapshot})


@require_GET
def background_audio_api(request: HttpRequest) -> JsonResponse:
    """
    获取背景音频状态与播放列表。

    :param request: HTTP 请求
    :return: 背景音频快照
    """
    return json_response({"success": True, "background_audio": get_background_audio_snapshot()})


@csrf_exempt
@require_http_methods(["POST", "DELETE"])
def background_audio_playlist_api(request: HttpRequest) -> JsonResponse:
    """
    新增播放列表项或清空播放列表。

    :param request: HTTP 请求
    :return: 背景音频快照
    """
    if request.method == "DELETE":
        return _mutate_background_audio(clear_playlist)

    body, error = body_or_error(request)
    if error is not None:
        return error
    source_id = int_value(body, "source_id")
    if source_id <= 0:
        return error_response("source_id 必须大于 0", code="invalid_source")
    try:
        return _mutate_background_audio(lambda: add_source_to_playlist(source_id))
    except BackgroundAudioError as audio_error:
        return error_response(str(audio_error), code="background_audio_error")


@csrf_exempt
@require_http_methods(["DELETE"])
def background_audio_playlist_item_api(request: HttpRequest, item_id: int) -> JsonResponse:
    """
    删除播放列表项。

    :param request: HTTP 请求
    :param item_id: 播放列表项主键
    :return: 背景音频快照
    """
    try:
        return _mutate_background_audio(lambda: remove_playlist_item(int(item_id)))
    except BackgroundAudioError as audio_error:
        return error_response(str(audio_error), code="background_audio_error", status=404)


@csrf_exempt
@require_http_methods(["POST"])
def background_audio_play_source_api(request: HttpRequest) -> JsonResponse:
    """
    加入并立即播放指定音频源。

    :param request: HTTP 请求
    :return: 背景音频快照
    """
    body, error = body_or_error(request)
    if error is not None:
        return error
    source_id = int_value(body, "source_id")
    if source_id <= 0:
        return error_response("source_id 必须大于 0", code="invalid_source")
    try:
        return _mutate_background_audio(lambda: play_source(source_id))
    except BackgroundAudioError as audio_error:
        return error_response(str(audio_error), code="background_audio_error")


@csrf_exempt
@require_http_methods(["POST"])
def background_audio_play_item_api(request: HttpRequest, item_id: int) -> JsonResponse:
    """
    播放指定播放列表项。

    :param request: HTTP 请求
    :param item_id: 播放列表项主键
    :return: 背景音频快照
    """
    try:
        return _mutate_background_audio(lambda: play_playlist_item(int(item_id)))
    except BackgroundAudioError as audio_error:
        return error_response(str(audio_error), code="background_audio_error", status=404)


@csrf_exempt
@require_http_methods(["POST"])
def background_audio_control_api(request: HttpRequest) -> JsonResponse:
    """
    控制背景音频播放、暂停、停止、上一首、下一首或跳转。

    :param request: HTTP 请求
    :return: 背景音频快照
    """
    body, error = body_or_error(request)
    if error is not None:
        return error
    action = str(body.get("action", "")).strip()
    operations: dict[str, Callable[[], Any]] = {
        "play": resume_background_audio,
        "pause": pause_background_audio,
        "stop": stop_background_audio,
        "next": play_next_background_audio,
        "prev": play_previous_background_audio,
        "seek": lambda: seek_background_audio(int_value(body, "position_ms")),
    }
    operation = operations.get(action)
    if operation is None:
        return error_response("无效的背景音频控制动作", code="invalid_action")
    try:
        return _mutate_background_audio(operation)
    except BackgroundAudioError as audio_error:
        return error_response(str(audio_error), code="background_audio_error")


@csrf_exempt
@require_http_methods(["PATCH"])
def background_audio_volume_api(request: HttpRequest) -> JsonResponse:
    """
    设置背景音频音量。

    :param request: HTTP 请求
    :return: 背景音频快照
    """
    body, error = body_or_error(request)
    if error is not None:
        return error
    return _mutate_background_audio(lambda: set_background_audio_volume(int_value(body, "volume", 70)))


@csrf_exempt
@require_http_methods(["PATCH"])
def background_audio_mute_api(request: HttpRequest) -> JsonResponse:
    """
    设置背景音频静音状态。

    :param request: HTTP 请求
    :return: 背景音频快照
    """
    body, error = body_or_error(request)
    if error is not None:
        return error
    return _mutate_background_audio(lambda: set_background_audio_mute(bool_value(body, "muted")))


@csrf_exempt
@require_http_methods(["PATCH"])
def background_audio_loop_api(request: HttpRequest) -> JsonResponse:
    """
    设置背景音频列表循环状态。

    :param request: HTTP 请求
    :return: 背景音频快照
    """
    body, error = body_or_error(request)
    if error is not None:
        return error
    return _mutate_background_audio(lambda: set_background_audio_loop(bool_value(body, "enabled")))
