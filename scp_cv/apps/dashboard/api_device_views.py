#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
设备控制 REST API 视图。
@Project : SCP-cv
@File : api_device_views.py
@Author : Qintsg
@Date : 2026-07-12
'''
from __future__ import annotations

from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods

from scp_cv.services.device import (
    DeviceError,
    list_devices,
    power_off_device,
    power_on_device,
    toggle_device,
)

from .api_utils import error_response, json_response


@require_GET
def list_devices_api(request: HttpRequest) -> JsonResponse:
    """
    获取可控制设备列表。
    :param request: HTTP 请求
    :return: 设备状态列表
    """
    return json_response({"success": True, "devices": list_devices()})


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
        return json_response({"success": True, "device": toggle_device(device_type)})
    except DeviceError as device_error:
        return error_response(str(device_error), code="device_error", status=404)


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
            return error_response("action 必须是 on 或 off", code="invalid_action")
    except DeviceError as device_error:
        return error_response(str(device_error), code="device_error", status=404)
    return json_response({"success": True, "device": device})
