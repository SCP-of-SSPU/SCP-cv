#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
REST API 公共工具函数，供控制台各 API 模块复用。
@Project : SCP-cv
@File : api_utils.py
@Author : Qintsg
@Date : 2026-04-27
'''
from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from django.http import HttpRequest, JsonResponse

from scp_cv.services.playback import VALID_WINDOW_IDS, PlaybackError, get_all_sessions_snapshot
from scp_cv.services.sse import publish_event


def json_response(payload: dict[str, Any], status: int = 200) -> JsonResponse:
    """
    返回统一 JSON 响应，允许 datetime 等对象转换为字符串。
    :param payload: 响应体
    :param status: HTTP 状态码
    :return: JsonResponse 实例
    """
    return JsonResponse(payload, status=status, json_dumps_params={"default": str})


def error_response(message: str, code: str = "bad_request", status: int = 400) -> JsonResponse:
    """
    返回统一错误响应。
    :param message: 错误描述
    :param code: 稳定错误码
    :param status: HTTP 状态码
    :return: JsonResponse 实例
    """
    return json_response({"detail": message, "code": code}, status=status)


def parse_json_body(request: HttpRequest) -> dict[str, Any]:
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


def body_or_error(request: HttpRequest) -> tuple[dict[str, Any] | None, JsonResponse | None]:
    """
    安全解析请求体，避免每个视图重复 try/except。
    :param request: HTTP 请求
    :return: (body, error_response)
    """
    try:
        return parse_json_body(request), None
    except ValueError as body_error:
        return None, error_response(str(body_error), code="invalid_json")


def int_value(body: dict[str, Any], field_name: str, default: int = 0) -> int:
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


def bool_value(body: dict[str, Any], field_name: str, default: bool = False) -> bool:
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


def parse_window_id(raw_window_id: int | str) -> int:
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


def mutate_playback(operation: Callable[[], Any]) -> JsonResponse:
    """
    执行会改变播放状态的操作，并发布统一状态事件。
    :param operation: 业务操作回调
    :return: 包含全量会话快照的 JSON 响应
    """
    operation()
    sessions = get_all_sessions_snapshot()
    payload = {"sessions": sessions}
    publish_event("playback_state", payload)
    return json_response({"success": True, **payload})
