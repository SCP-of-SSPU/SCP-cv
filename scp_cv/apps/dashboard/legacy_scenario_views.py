#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
旧版播放控制台预案视图，保留表单和兼容 API 的路由处理。
@Project : SCP-cv
@File : legacy_scenario_views.py
@Author : Qintsg
@Date : 2026-05-02
'''
from __future__ import annotations

import json

from django.http import HttpRequest, JsonResponse
from django.views.decorators.http import require_GET, require_POST

from scp_cv.services.scenario import (
    ScenarioError,
    activate_scenario,
    create_scenario,
    delete_scenario,
    list_scenarios,
    update_scenario,
)
from scp_cv.services.sse import publish_event


@require_GET
def api_scenarios(request: HttpRequest) -> JsonResponse:
    """
    获取所有预案列表。
    :param request: HTTP 请求
    :return: JSON 格式的预案列表
    """
    return JsonResponse({
        "success": True,
        "scenarios": list_scenarios(),
    }, json_dumps_params={"default": str})


def _parse_scenario_body(request: HttpRequest) -> dict[str, object]:
    """
    从 POST 请求中解析预案配置参数（支持 JSON body 和 form-data）。
    :param request: HTTP 请求
    :return: 解析后的参数字典
    """
    # 兼容新版 JSON API 与旧版 form-data 提交，避免模板和前端面板同时改动。
    if request.content_type and "json" in request.content_type:
        try:
            return json.loads(request.body)
        except (json.JSONDecodeError, AttributeError):
            pass
    return dict(request.POST)


def _extract_int(raw_value: object, default: int = 0) -> int:
    """
    安全提取整数值。
    :param raw_value: 原始值（字符串、数字或 None）
    :param default: 解析失败时的默认值
    :return: 整数结果
    """
    if raw_value is None:
        return default
    try:
        return int(raw_value)
    except (ValueError, TypeError):
        return default


def _extract_bool(raw_value: object, default: bool = True) -> bool:
    """
    安全提取布尔值。
    :param raw_value: 原始值（字符串、布尔或 None）
    :param default: 解析失败时的默认值
    :return: 布尔结果
    """
    if raw_value is None:
        return default
    if isinstance(raw_value, bool):
        return raw_value
    return str(raw_value).strip().lower() in ("true", "1", "yes")


@require_POST
def create_scenario_view(request: HttpRequest) -> JsonResponse:
    """
    创建新预案。
    接受 JSON body 或 form-data，参数包含名称、描述、拼接模式及窗口 1/2 配置。
    :param request: HTTP 请求
    :return: JSON 响应（含创建后的预案详情）
    """
    body = _parse_scenario_body(request)
    name = str(body.get("name", "")).strip()
    if not name:
        return JsonResponse({"success": False, "error": "缺少 name 字段"}, status=400)

    try:
        scenario = create_scenario(
            name=name,
            description=str(body.get("description", "")),
            window1_source_id=_extract_int(body.get("window1_source_id")) or None,
            window1_autoplay=_extract_bool(body.get("window1_autoplay"), default=True),
            window1_resume=_extract_bool(body.get("window1_resume"), default=True),
            window2_source_id=_extract_int(body.get("window2_source_id")) or None,
            window2_autoplay=_extract_bool(body.get("window2_autoplay"), default=True),
            window2_resume=_extract_bool(body.get("window2_resume"), default=True),
        )
    except ScenarioError as create_err:
        return JsonResponse({"success": False, "error": str(create_err)}, status=400)

    from scp_cv.services.scenario import _scenario_to_dict
    return JsonResponse({"success": True, "scenario": _scenario_to_dict(scenario)})


@require_POST
def update_scenario_view(request: HttpRequest, scenario_id: str) -> JsonResponse:
    """
    更新已有预案。
    :param request: HTTP 请求（JSON body 或 form-data）
    :param scenario_id: URL 路径中的预案 ID
    :return: JSON 响应
    """
    try:
        sid = int(scenario_id)
    except (ValueError, TypeError):
        return JsonResponse({"success": False, "error": "预案 ID 格式无效"}, status=400)

    body = _parse_scenario_body(request)

    # 记录字段是否显式传入，服务层需要区分“不修改”和“主动清空”。
    window1_source_provided = "window1_source_id" in body
    window2_source_provided = "window2_source_id" in body

    try:
        scenario = update_scenario(
            scenario_id=sid,
            name=body.get("name") if "name" in body else None,
            description=body.get("description") if "description" in body else None,
            window1_source_id=_extract_int(body.get("window1_source_id")) or None,
            window1_autoplay=_extract_bool(body.get("window1_autoplay")) if "window1_autoplay" in body else None,
            window1_resume=_extract_bool(body.get("window1_resume")) if "window1_resume" in body else None,
            window2_source_id=_extract_int(body.get("window2_source_id")) or None,
            window2_autoplay=_extract_bool(body.get("window2_autoplay")) if "window2_autoplay" in body else None,
            window2_resume=_extract_bool(body.get("window2_resume")) if "window2_resume" in body else None,
            _window1_source_provided=window1_source_provided,
            _window2_source_provided=window2_source_provided,
        )
    except ScenarioError as update_err:
        return JsonResponse({"success": False, "error": str(update_err)}, status=400)

    from scp_cv.services.scenario import _scenario_to_dict
    return JsonResponse({"success": True, "scenario": _scenario_to_dict(scenario)})


@require_POST
def delete_scenario_view(request: HttpRequest, scenario_id: str) -> JsonResponse:
    """
    删除指定预案。
    :param request: HTTP 请求
    :param scenario_id: URL 路径中的预案 ID
    :return: JSON 响应
    """
    try:
        sid = int(scenario_id)
    except (ValueError, TypeError):
        return JsonResponse({"success": False, "error": "预案 ID 格式无效"}, status=400)

    try:
        delete_scenario(sid)
    except ScenarioError as del_err:
        return JsonResponse({"success": False, "error": str(del_err)}, status=400)

    return JsonResponse({"success": True})


@require_POST
def activate_scenario_view(request: HttpRequest, scenario_id: str) -> JsonResponse:
    """
    激活预案：一键应用预设的窗口配置。
    :param request: HTTP 请求
    :param scenario_id: URL 路径中的预案 ID
    :return: JSON 响应（含激活后的窗口快照）
    """
    try:
        sid = int(scenario_id)
    except (ValueError, TypeError):
        return JsonResponse({"success": False, "error": "预案 ID 格式无效"}, status=400)

    try:
        session_snapshots = activate_scenario(sid)
    except ScenarioError as act_err:
        return JsonResponse({"success": False, "error": str(act_err)}, status=400)

    publish_event("playback_state", {"sessions": session_snapshots})
    return JsonResponse({
        "success": True,
        "sessions": session_snapshots,
    })
