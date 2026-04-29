#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
设备开关机占位服务，记录设备状态但不实际控制硬件。
@Project : SCP-cv
@File : device.py
@Author : Qintsg
@Date : 2026-04-29
'''
from __future__ import annotations

import logging

from scp_cv.apps.playback.models import DeviceEndpoint, DeviceType

logger = logging.getLogger(__name__)


class DeviceError(Exception):
    """设备操作过程中的业务异常。"""


def list_devices() -> list[dict[str, object]]:
    """
    获取所有设备端点列表。
    :return: 设备字典列表
    """
    devices = DeviceEndpoint.objects.all()
    if not devices.exists():
        _ensure_default_devices()
        devices = DeviceEndpoint.objects.all()
    return [
        {
            "id": d.pk,
            "name": d.name,
            "device_type": d.device_type,
            "device_type_label": d.get_device_type_display(),
            "is_powered_on": d.is_powered_on,
            "address": d.address,
            "is_placeholder": True,
            "detail": "当前仅记录控制意图，未接入物理设备协议",
        }
        for d in devices
    ]


def toggle_device(device_type: str) -> dict[str, object]:
    """
    切换设备开关机状态（占位实现）。
    :param device_type: 设备类型
    :return: 更新后的设备状态
    :raises DeviceError: 设备不存在时
    """
    _ensure_default_devices()
    try:
        device = DeviceEndpoint.objects.get(device_type=device_type)
    except DeviceEndpoint.DoesNotExist as not_found:
        raise DeviceError(f"设备类型 {device_type} 不存在") from not_found

    device.is_powered_on = not device.is_powered_on
    device.save(update_fields=["is_powered_on", "updated_at"])
    action = "开机" if device.is_powered_on else "关机"
    logger.info("设备「%s」执行%s（占位）", device.name, action)
    return {
        "id": device.pk,
        "name": device.name,
        "device_type": device.device_type,
        "is_powered_on": device.is_powered_on,
        "is_placeholder": True,
        "detail": "当前仅记录控制意图，未接入物理设备协议",
    }


def power_on_device(device_type: str) -> dict[str, object]:
    """
    设备开机（占位实现）。
    :param device_type: 设备类型
    :return: 设备状态
    """
    _ensure_default_devices()
    try:
        device = DeviceEndpoint.objects.get(device_type=device_type)
    except DeviceEndpoint.DoesNotExist as not_found:
        raise DeviceError(f"设备类型 {device_type} 不存在") from not_found

    device.is_powered_on = True
    device.save(update_fields=["is_powered_on", "updated_at"])
    logger.info("设备「%s」执行开机（占位）", device.name)
    return {
        "id": device.pk,
        "name": device.name,
        "device_type": device.device_type,
        "is_powered_on": device.is_powered_on,
        "is_placeholder": True,
        "detail": "当前仅记录控制意图，未接入物理设备协议",
    }


def power_off_device(device_type: str) -> dict[str, object]:
    """
    设备关机（占位实现）。
    :param device_type: 设备类型
    :return: 设备状态
    """
    _ensure_default_devices()
    try:
        device = DeviceEndpoint.objects.get(device_type=device_type)
    except DeviceEndpoint.DoesNotExist as not_found:
        raise DeviceError(f"设备类型 {device_type} 不存在") from not_found

    device.is_powered_on = False
    device.save(update_fields=["is_powered_on", "updated_at"])
    logger.info("设备「%s」执行关机（占位）", device.name)
    return {
        "id": device.pk,
        "name": device.name,
        "device_type": device.device_type,
        "is_powered_on": device.is_powered_on,
        "is_placeholder": True,
        "detail": "当前仅记录控制意图，未接入物理设备协议",
    }


def _ensure_default_devices() -> None:
    """确保三个默认设备端点存在。"""
    defaults = [
        (DeviceType.SPLICE_SCREEN, "拼接屏"),
        (DeviceType.TV_LEFT, "电视左"),
        (DeviceType.TV_RIGHT, "电视右"),
    ]
    for device_type, name in defaults:
        DeviceEndpoint.objects.get_or_create(
            device_type=device_type,
            defaults={"name": name},
        )
