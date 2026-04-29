#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
预案 REST API 视图。
@Project : SCP-cv
@File : api_scenario_views.py
@Author : Qintsg
@Date : 2026-04-27
'''
from __future__ import annotations

from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from scp_cv.apps.dashboard.api_utils import (
    body_or_error,
    error_response,
    int_value,
    json_response,
)
from scp_cv.services.scenario import (
    ScenarioError,
    _scenario_to_dict,
    activate_scenario,
    capture_scenario_from_current_state,
    create_scenario,
    delete_scenario,
    get_scenario,
    list_scenarios,
    pin_scenario,
    update_scenario,
)
from scp_cv.services.sse import publish_event


def _target_bool(raw_value: object, default: bool = True) -> bool:
    """
    解析预案目标中的布尔字段。
    :param raw_value: 原始字段值
    :param default: 缺省值
    :return: 布尔值
    """
    if raw_value is None:
        return default
    if isinstance(raw_value, bool):
        return raw_value
    return str(raw_value).strip().lower() in {"true", "1", "yes", "on"}


def _targets_from_body(body: dict[str, object]) -> list[dict[str, object]] | None:
    """
    从请求体提取四窗口目标配置。
    :param body: JSON 请求体
    :return: 目标配置列表；未提供时返回 None
    :raises ScenarioError: targets 不是数组时
    """
    if "targets" not in body:
        return None
    raw_targets = body.get("targets")
    if not isinstance(raw_targets, list):
        raise ScenarioError("targets 必须是数组")

    targets: list[dict[str, object]] = []
    for raw_target in raw_targets:
        if not isinstance(raw_target, dict):
            continue
        targets.append({
            "window_id": int(raw_target.get("window_id", 0) or 0),
            "source_state": str(raw_target.get("source_state", "unset")),
            "source_id": raw_target.get("source_id"),
            "autoplay": _target_bool(raw_target.get("autoplay"), True),
            "resume": _target_bool(raw_target.get("resume"), True),
        })
    return targets


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
    return json_response({"success": True, "scenarios": list_scenarios()})


@csrf_exempt
@require_http_methods(["POST"])
def create_scenario_api(request: HttpRequest) -> JsonResponse:
    """
    创建预案。
    :param request: HTTP 请求
    :return: 创建结果
    """
    body, error = body_or_error(request)
    if error is not None:
        return error
    name = str(body.get("name", "")).strip()
    if not name:
        return error_response("缺少 name 字段", code="missing_name")
    try:
        targets = _targets_from_body(body)
        scenario = create_scenario(
            name=name,
            description=str(body.get("description", "")),
            big_screen_mode_state=str(body.get("big_screen_mode_state", "unset")),
            big_screen_mode=str(body.get("big_screen_mode", "single")),
            volume_state=str(body.get("volume_state", "unset")),
            volume_level=int_value(body, "volume_level", 100),
            targets=targets,
        )
    except ScenarioError as scenario_error:
        return error_response(str(scenario_error), code="scenario_error")
    return json_response({"success": True, "scenario": _scenario_to_dict(scenario)}, status=201)


@csrf_exempt
@require_http_methods(["GET", "PATCH", "DELETE"])
def scenario_detail_api(request: HttpRequest, scenario_id: int) -> JsonResponse:
    """
    更新或删除指定预案。
    :param request: HTTP 请求
    :param scenario_id: 预案主键
    :return: 操作结果
    """
    if request.method == "GET":
        try:
            return json_response({"success": True, "scenario": get_scenario(int(scenario_id))})
        except ScenarioError as scenario_error:
            return error_response(str(scenario_error), code="scenario_error", status=404)

    if request.method == "DELETE":
        try:
            delete_scenario(int(scenario_id))
        except ScenarioError as scenario_error:
            return error_response(str(scenario_error), code="scenario_error", status=404)
        return json_response({"success": True})

    body, error = body_or_error(request)
    if error is not None:
        return error
    try:
        targets = _targets_from_body(body)
        scenario = update_scenario(
            scenario_id=int(scenario_id),
            name=body.get("name") if "name" in body else None,
            description=body.get("description") if "description" in body else None,
            big_screen_mode_state=body.get("big_screen_mode_state") if "big_screen_mode_state" in body else None,
            big_screen_mode=body.get("big_screen_mode") if "big_screen_mode" in body else None,
            volume_state=body.get("volume_state") if "volume_state" in body else None,
            volume_level=int_value(body, "volume_level", 100) if "volume_level" in body else None,
            targets=targets,
        )
    except ScenarioError as scenario_error:
        return error_response(str(scenario_error), code="scenario_error")
    return json_response({"success": True, "scenario": _scenario_to_dict(scenario)})


@csrf_exempt
@require_http_methods(["POST"])
def pin_scenario_api(request: HttpRequest, scenario_id: int) -> JsonResponse:
    """
    置顶指定预案。
    :param request: HTTP 请求
    :param scenario_id: 预案主键
    :return: 更新后的预案
    """
    try:
        scenario = pin_scenario(int(scenario_id))
    except ScenarioError as scenario_error:
        return error_response(str(scenario_error), code="scenario_error", status=404)
    return json_response({"success": True, "scenario": _scenario_to_dict(scenario)})


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
        payload = {"sessions": sessions}
        publish_event("playback_state", payload)
        return json_response({"success": True, **payload})
    except ScenarioError as scenario_error:
        return error_response(str(scenario_error), code="scenario_error")


@csrf_exempt
@require_http_methods(["POST"])
def capture_scenario_api(request: HttpRequest) -> JsonResponse:
    """
    从当前窗口 1/2 状态捕获预案。
    :param request: HTTP 请求
    :return: 捕获结果
    """
    body, error = body_or_error(request)
    if error is not None:
        return error
    name = str(body.get("name", "")).strip()
    if not name:
        return error_response("缺少 name 字段", code="missing_name")
    try:
        scenario = capture_scenario_from_current_state(
            name=name,
            description=str(body.get("description", "")),
            scenario_id=int_value(body, "scenario_id") or None,
        )
    except ScenarioError as scenario_error:
        return error_response(str(scenario_error), code="scenario_error")
    return json_response({"success": True, "scenario": _scenario_to_dict(scenario)})
