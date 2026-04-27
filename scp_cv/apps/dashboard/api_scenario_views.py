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
    bool_value,
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
    list_scenarios,
    update_scenario,
)
from scp_cv.services.sse import publish_event


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
        scenario = create_scenario(
            name=name,
            description=str(body.get("description", "")),
            window1_source_id=int_value(body, "window1_source_id") or None,
            window1_autoplay=bool_value(body, "window1_autoplay", True),
            window1_resume=bool_value(body, "window1_resume", True),
            window2_source_id=int_value(body, "window2_source_id") or None,
            window2_autoplay=bool_value(body, "window2_autoplay", True),
            window2_resume=bool_value(body, "window2_resume", True),
            window1_fullscreen_to_window2=bool_value(body, "window1_fullscreen_to_window2", False),
        )
    except ScenarioError as scenario_error:
        return error_response(str(scenario_error), code="scenario_error")
    return json_response({"success": True, "scenario": _scenario_to_dict(scenario)}, status=201)


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
            return error_response(str(scenario_error), code="scenario_error", status=404)
        return json_response({"success": True})

    body, error = body_or_error(request)
    if error is not None:
        return error
    try:
        scenario = update_scenario(
            scenario_id=int(scenario_id),
            name=body.get("name") if "name" in body else None,
            description=body.get("description") if "description" in body else None,
            window1_source_id=int_value(body, "window1_source_id") or None,
            window1_autoplay=bool_value(body, "window1_autoplay", True) if "window1_autoplay" in body else None,
            window1_resume=bool_value(body, "window1_resume", True) if "window1_resume" in body else None,
            window2_source_id=int_value(body, "window2_source_id") or None,
            window2_autoplay=bool_value(body, "window2_autoplay", True) if "window2_autoplay" in body else None,
            window2_resume=bool_value(body, "window2_resume", True) if "window2_resume" in body else None,
            window1_fullscreen_to_window2=(
                bool_value(body, "window1_fullscreen_to_window2", False)
                if "window1_fullscreen_to_window2" in body else None
            ),
            _window1_source_provided="window1_source_id" in body,
            _window2_source_provided="window2_source_id" in body,
        )
    except ScenarioError as scenario_error:
        return error_response(str(scenario_error), code="scenario_error")
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
