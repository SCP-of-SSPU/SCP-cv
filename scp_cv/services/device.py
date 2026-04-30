#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
设备电源控制服务，通过 TCP 发送固定 hex 控制帧。
不保存设备状态，也不读取设备返回数据。
@Project : SCP-cv
@File : device.py
@Author : Qintsg
@Date : 2026-04-30
'''
from __future__ import annotations

import logging
import socket
import time
from dataclasses import dataclass

from scp_cv.apps.playback.models import DeviceType

logger = logging.getLogger(__name__)


class DeviceError(Exception):
    """设备操作过程中的业务异常。"""


@dataclass(frozen=True)
class DeviceDefinition:
    """物理电源控制端点定义。"""

    device_type: str
    name: str
    host: str
    port: int


_TCP_TIMEOUT_SECONDS = 3
_SPLICE_ON_FRAMES = ["FF06010A00010001FA", "FF06010A00010000FA"]
_SPLICE_OFF_FRAMES = ["FF06010A00020001FA", "FF06010A00020000FA"]
_TV_TOGGLE_FRAMES = ["FF06010A00330001FA", "FF06010A00330000FA"]
_DEVICES: dict[str, DeviceDefinition] = {
    DeviceType.SPLICE_SCREEN: DeviceDefinition(DeviceType.SPLICE_SCREEN, "拼接屏", "192.168.5.10", 8889),
    DeviceType.TV_LEFT: DeviceDefinition(DeviceType.TV_LEFT, "电视左", "192.168.5.161", 8889),
    DeviceType.TV_RIGHT: DeviceDefinition(DeviceType.TV_RIGHT, "电视右", "192.168.5.162", 8889),
}


def list_devices() -> list[dict[str, object]]:
    """
    获取可控制设备按钮配置，不包含状态。
    :return: 设备按钮配置列表
    """
    return [_device_payload(device) for device in _DEVICES.values()]


def toggle_device(device_type: str) -> dict[str, object]:
    """
    执行电视开关机切换指令。
    :param device_type: 设备类型
    :return: 执行结果
    :raises DeviceError: 设备不支持切换或发送失败时
    """
    device = _get_device(device_type)
    if device.device_type not in {DeviceType.TV_LEFT, DeviceType.TV_RIGHT}:
        raise DeviceError("拼接屏不支持切换指令，请使用开机或关机")
    _send_sequence(device, _TV_TOGGLE_FRAMES, 0.1)
    logger.info("设备「%s」已发送开关机切换指令", device.name)
    return _device_payload(device, action="toggle")


def power_on_device(device_type: str) -> dict[str, object]:
    """
    执行拼接屏开机指令。
    :param device_type: 设备类型
    :return: 执行结果
    :raises DeviceError: 设备不支持开机或发送失败时
    """
    device = _get_device(device_type)
    if device.device_type != DeviceType.SPLICE_SCREEN:
        raise DeviceError("电视仅支持开关机切换指令")
    _send_sequence(device, _SPLICE_ON_FRAMES, 5.0)
    logger.info("设备「%s」已发送开机指令", device.name)
    return _device_payload(device, action="on")


def power_off_device(device_type: str) -> dict[str, object]:
    """
    执行拼接屏关机指令。
    :param device_type: 设备类型
    :return: 执行结果
    :raises DeviceError: 设备不支持关机或发送失败时
    """
    device = _get_device(device_type)
    if device.device_type != DeviceType.SPLICE_SCREEN:
        raise DeviceError("电视仅支持开关机切换指令")
    _send_sequence(device, _SPLICE_OFF_FRAMES, 5.0)
    logger.info("设备「%s」已发送关机指令", device.name)
    return _device_payload(device, action="off")


def _get_device(device_type: str) -> DeviceDefinition:
    """
    查询静态设备定义。
    :param device_type: 设备类型
    :return: 设备定义
    :raises DeviceError: 设备类型不存在时
    """
    device = _DEVICES.get(device_type)
    if device is None:
        raise DeviceError(f"设备类型 {device_type} 不存在")
    return device


def _send_sequence(device: DeviceDefinition, hex_frames: list[str], interval_seconds: float) -> None:
    """
    按顺序发送 TCP hex 帧，两帧之间按需求等待。
    :param device: 设备定义
    :param hex_frames: hex 字符串帧列表
    :param interval_seconds: 两帧之间等待秒数
    :return: None
    """
    for frame_index, hex_frame in enumerate(hex_frames):
        _send_tcp_frame(device.host, device.port, hex_frame)
        if frame_index < len(hex_frames) - 1:
            time.sleep(interval_seconds)


def _send_tcp_frame(host: str, port: int, hex_frame: str) -> None:
    """
    向指定 TCP 端点发送单帧数据，不读取返回。
    :param host: 目标 IP
    :param port: 目标端口
    :param hex_frame: 控制帧 hex 字符串
    :return: None
    :raises DeviceError: 网络发送失败时
    """
    try:
        frame = bytes.fromhex(hex_frame.replace(" ", ""))
        with socket.create_connection((host, port), timeout=_TCP_TIMEOUT_SECONDS) as tcp_socket:
            tcp_socket.sendall(frame)
    except (OSError, ValueError) as send_error:
        raise DeviceError(f"发送设备电源指令失败：{host}:{port} {send_error}") from send_error


def _device_payload(device: DeviceDefinition, action: str = "") -> dict[str, object]:
    """序列化电源控制结果，不包含任何设备状态。"""
    return {
        "name": device.name,
        "device_type": device.device_type,
        "device_type_label": dict(DeviceType.choices).get(device.device_type, device.name),
        "host": device.host,
        "port": device.port,
        "action": action,
        "detail": "电源指令已发送，未读取设备返回",
    }
