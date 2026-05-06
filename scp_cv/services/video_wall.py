#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
视频墙模式控制服务，根据单屏/双屏模式向 50 个输出节点下发 TCP 控制包。
@Project : SCP-cv
@File : video_wall.py
@Author : Qintsg
@Date : 2026-05-06
'''
from __future__ import annotations

import logging
import socket
from ipaddress import IPv4Address

from scp_cv.apps.playback.models import BigScreenMode

logger = logging.getLogger(__name__)


class VideoWallError(Exception):
    """视频墙控制过程中的业务异常。"""


_TCP_PORT = 4830
_TCP_TIMEOUT_SECONDS = 1.0
_WALL_COLS = 10
_WALL_ROWS = 5
_SCREEN_WIDTH = 1920
_SCREEN_HEIGHT = 1080
_SOURCE_WIDTH = 3840
_SOURCE_HEIGHT = 2160
_WS21_MCAST = "224.1.1.55"
_WS22_MCAST = "224.1.1.56"
_CLEAR_PACKET = bytes.fromhex("FB FC 61 FF 00 00 00 00 01 60 FD FE")
_COMMIT_PACKET = bytes.fromhex("FB FC 61 B8 00 00 00 00 01 19 FD FE")
_REFRESH_PACKET = bytes.fromhex("FB FC 61 B9 00 00 00 00 01 1A FD FE")
_FIXED_FLAGS = bytes.fromhex("00 09 00 01 00 01")


class VideoWallMode:
    """视频墙物理布局模式。"""

    FULLSCREEN_WS21 = "fullscreen-ws21"
    SPLIT_WS21_WS22 = "split-ws21-ws22"


def apply_big_screen_mode(big_screen_mode: str) -> None:
    """
    根据运行态大屏模式下发视频墙控制包。
    :param big_screen_mode: single 或 double
    :return: None
    :raises VideoWallError: 模式无效或网络发送失败时
    """
    mode = _video_wall_mode_for_runtime(big_screen_mode)
    sequence = build_sequence(mode)
    for item in sequence:
        _send_tcp_packet(item["ip"], item["port"], item["packet"])
    logger.info("视频墙模式已切换为 %s，共发送 %d 个 TCP 包", mode, len(sequence))


def build_sequence(mode: str) -> list[dict[str, object]]:
    """
    构造完整的视频墙下发序列。
    :param mode: 物理视频墙模式
    :return: 待发送项列表
    :raises VideoWallError: 模式无效时
    """
    sequence: list[dict[str, object]] = []

    for ip in all_target_ips():
        sequence.append(_make_send_item("clear", ip, _TCP_PORT, _CLEAR_PACKET))

    if mode == VideoWallMode.FULLSCREEN_WS21:
        sequence.extend(_build_fullscreen_ws21_mappings())
    elif mode == VideoWallMode.SPLIT_WS21_WS22:
        sequence.extend(_build_split_ws21_ws22_mappings())
    else:
        raise VideoWallError(f"未知的视频墙模式：{mode}")

    for ip in all_target_ips():
        sequence.append(_make_send_item("commit", ip, _TCP_PORT, _COMMIT_PACKET))

    for ip in all_target_ips():
        sequence.append(_make_send_item("refresh", ip, _TCP_PORT, _REFRESH_PACKET))

    return sequence


def all_target_ips() -> list[str]:
    """返回视频墙全部目标节点 IP。"""
    return [target_ip(col, row) for col in range(_WALL_COLS) for row in range(_WALL_ROWS)]


def target_ip(col: int, row: int) -> str:
    """
    根据列行坐标计算目标节点 IP，并处理现场 45/46 互换补丁。
    :param col: 列号
    :param row: 行号
    :return: 目标节点 IP
    """
    screen_id = col * _WALL_ROWS + row
    if screen_id == 45:
        screen_id = 46
    elif screen_id == 46:
        screen_id = 45
    return f"192.168.5.{101 + screen_id}"


def _video_wall_mode_for_runtime(big_screen_mode: str) -> str:
    """
    将运行态 single/double 映射为物理视频墙模式。
    :param big_screen_mode: single 或 double
    :return: 视频墙模式
    :raises VideoWallError: 模式未知时
    """
    if big_screen_mode == BigScreenMode.SINGLE:
        return VideoWallMode.FULLSCREEN_WS21
    if big_screen_mode == BigScreenMode.DOUBLE:
        return VideoWallMode.SPLIT_WS21_WS22
    raise VideoWallError(f"无效的大屏模式：{big_screen_mode}")


def _build_fullscreen_ws21_mappings() -> list[dict[str, object]]:
    """生成工作站 2-1 全屏铺满视频墙的映射包。"""
    sequence: list[dict[str, object]] = []
    src_width = _SOURCE_WIDTH // _WALL_COLS
    src_height = _SOURCE_HEIGHT // _WALL_ROWS

    for col in range(_WALL_COLS):
        for row in range(_WALL_ROWS):
            sequence.append(
                _make_send_item(
                    "mapping_ws21_fullscreen",
                    target_ip(col, row),
                    _TCP_PORT,
                    _mapping_packet(
                        mcast_ip=_WS21_MCAST,
                        window_id=1,
                        src_x=col * src_width,
                        src_y=row * src_height,
                        src_width=src_width,
                        src_height=src_height,
                    ),
                ),
            )
    return sequence


def _build_split_ws21_ws22_mappings() -> list[dict[str, object]]:
    """生成左半屏工作站 2-1、右半屏工作站 2-2 的映射包。"""
    sequence: list[dict[str, object]] = []
    half_cols = _WALL_COLS // 2
    src_width = _SOURCE_WIDTH // half_cols
    src_height = _SOURCE_HEIGHT // _WALL_ROWS

    for col in range(_WALL_COLS):
        for row in range(_WALL_ROWS):
            if col < half_cols:
                phase = "mapping_ws21_left_half"
                packet = _mapping_packet(
                    mcast_ip=_WS21_MCAST,
                    window_id=1,
                    src_x=col * src_width,
                    src_y=row * src_height,
                    src_width=src_width,
                    src_height=src_height,
                )
            else:
                phase = "mapping_ws22_right_half"
                packet = _mapping_packet(
                    mcast_ip=_WS22_MCAST,
                    window_id=2,
                    src_x=(col - half_cols) * src_width,
                    src_y=row * src_height,
                    src_width=src_width,
                    src_height=src_height,
                )
            sequence.append(_make_send_item(phase, target_ip(col, row), _TCP_PORT, packet))
    return sequence


def _mapping_packet(
    *,
    mcast_ip: str,
    window_id: int,
    src_x: int,
    src_y: int,
    src_width: int,
    src_height: int,
) -> bytes:
    """
    生成单个 61 02 窗口映射包。
    :param mcast_ip: 输入源组播地址
    :param window_id: 窗口编号
    :param src_x: 源裁切起始 X
    :param src_y: 源裁切起始 Y
    :param src_width: 源裁切宽度
    :param src_height: 源裁切高度
    :return: 45 字节映射包
    """
    packet = bytearray()
    packet += bytes.fromhex("FB FC")
    packet += bytes.fromhex("61 02")
    packet += bytes.fromhex("00 00 00 21")
    packet += _u16(window_id)
    packet += IPv4Address(mcast_ip).packed
    packet += _u16(5000)
    packet += _u16(0)
    packet += _u16(0)
    packet += _u16(_SCREEN_WIDTH)
    packet += _u16(_SCREEN_HEIGHT)
    packet += _u16(window_id)
    packet += _u16(src_x)
    packet += _u16(src_y)
    packet += _u16(src_width)
    packet += _u16(src_height)
    packet += _FIXED_FLAGS
    packet += bytes.fromhex("01")
    checksum = (sum(packet[2:]) - 1) & 0xFFFF
    packet += _u16(checksum)
    packet += bytes.fromhex("FD FE")
    if len(packet) != 45:
        raise VideoWallError(f"窗口映射包长度异常：{len(packet)}")
    return bytes(packet)


def _make_send_item(phase: str, ip: str, port: int, packet: bytes) -> dict[str, object]:
    """构造单个待发送项。"""
    return {
        "phase": phase,
        "ip": ip,
        "port": port,
        "packet": packet,
    }


def _u16(value: int) -> bytes:
    """将 0-65535 的整数编码为双字节大端无符号数。"""
    if not 0 <= value <= 0xFFFF:
        raise VideoWallError(f"u16 超出范围：{value}")
    return value.to_bytes(2, "big")


def _send_tcp_packet(ip: str, port: int, packet: bytes) -> None:
    """
    向指定输出节点发送单个 TCP 包。
    :param ip: 目标 IP
    :param port: 目标端口
    :param packet: 原始字节包
    :return: None
    :raises VideoWallError: 发送失败时
    """
    try:
        with socket.create_connection((ip, port), timeout=_TCP_TIMEOUT_SECONDS) as tcp_socket:
            tcp_socket.sendall(packet)
    except OSError as send_error:
        raise VideoWallError(f"发送视频墙控制包失败：{ip}:{port} {send_error}") from send_error
