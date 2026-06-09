#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
视频墙控制服务测试。
覆盖单屏/双屏模式的目标节点映射与控制包序列生成。
@Project : SCP-cv
@File : test_video_wall_service.py
@Author : Qintsg
@Date : 2026-05-06
'''
from __future__ import annotations

import threading
from typing import Any

import pytest

from scp_cv.apps.playback.models import BigScreenMode
from scp_cv.services.video_wall import (
    VideoWallError,
    VideoWallMode,
    _mapping_packet,
    _video_wall_mode_for_runtime,
    all_target_ips,
    build_sequence,
    target_ip,
)


def test_target_ip_swaps_screen_45_and_46() -> None:
    """目标节点 IP 应对逻辑屏幕 45 和 46 应用现场互换补丁。"""
    assert target_ip(9, 0) == "192.168.5.147"
    assert target_ip(9, 1) == "192.168.5.146"


def test_all_target_ips_returns_50_nodes() -> None:
    """视频墙全部目标节点应固定为 50 台。"""
    ips = all_target_ips()

    assert len(ips) == 50
    assert ips[0] == "192.168.5.101"
    assert ips[-1] == "192.168.5.150"


def test_runtime_mode_maps_to_video_wall_mode() -> None:
    """运行态单屏双屏应映射到文档要求的视频墙模式。"""
    assert _video_wall_mode_for_runtime(BigScreenMode.SINGLE) == VideoWallMode.FULLSCREEN_WS21
    assert _video_wall_mode_for_runtime(BigScreenMode.DOUBLE) == VideoWallMode.SPLIT_WS21_WS22


def test_runtime_mode_rejects_unknown_value() -> None:
    """未知运行态模式应返回明确错误。"""
    try:
        _video_wall_mode_for_runtime("triple")
    except VideoWallError as error:
        assert "无效的大屏模式" in str(error)
    else:
        raise AssertionError("expected VideoWallError")


def test_build_fullscreen_sequence_contains_200_packets() -> None:
    """单屏模式应生成 50 清屏 + 50 映射 + 50 提交 + 50 刷新。"""
    sequence = build_sequence(VideoWallMode.FULLSCREEN_WS21)

    assert len(sequence) == 200
    assert sequence[0]["phase"] == "clear"
    assert sequence[49]["phase"] == "clear"
    assert sequence[50]["phase"] == "mapping_ws21_fullscreen"
    assert sequence[99]["phase"] == "mapping_ws21_fullscreen"
    assert sequence[100]["phase"] == "commit"
    assert sequence[150]["phase"] == "refresh"


def test_build_split_sequence_contains_left_and_right_mappings() -> None:
    """双屏模式应分别生成左半屏和右半屏映射包。"""
    sequence = build_sequence(VideoWallMode.SPLIT_WS21_WS22)
    mapping_items = sequence[50:100]

    assert len(sequence) == 200
    assert len([item for item in mapping_items if item["phase"] == "mapping_ws21_left_half"]) == 25
    assert len([item for item in mapping_items if item["phase"] == "mapping_ws22_right_half"]) == 25


def test_mapping_packet_encodes_expected_multicast_and_source_crop() -> None:
    """窗口映射包应编码组播地址、窗口号和源裁切区域。"""
    packet = _mapping_packet(
        mcast_ip="224.1.1.55",
        window_id=1,
        src_x=384,
        src_y=432,
        src_width=384,
        src_height=432,
    )

    assert len(packet) == 45
    assert packet[:2] == bytes.fromhex("FB FC")
    assert packet[2:4] == bytes.fromhex("61 02")
    assert packet[10:14] == bytes.fromhex("E0 01 01 37")
    assert packet[14:16] == bytes.fromhex("13 88")
    assert packet[26:28] == bytes.fromhex("01 80")
    assert packet[28:30] == bytes.fromhex("01 B0")
    assert packet[30:32] == bytes.fromhex("01 80")
    assert packet[32:34] == bytes.fromhex("01 B0")


def test_build_sequence_rejects_unknown_mode() -> None:
    """未知视频墙模式不应生成发送序列。"""
    try:
        build_sequence("unsupported")
    except VideoWallError as error:
        assert "未知的视频墙模式" in str(error)
    else:
        raise AssertionError("expected VideoWallError")


def test_apply_big_screen_mode_sends_same_stage_packets_in_parallel(monkeypatch: Any) -> None:
    """同一阶段的多个节点应并行发送，同时保持阶段之间的顺序。"""
    from scp_cv.services import video_wall

    sequence = [
        {"phase": "clear", "ip": "192.168.5.101", "port": 4830, "packet": b"clear-a"},
        {"phase": "clear", "ip": "192.168.5.102", "port": 4830, "packet": b"clear-b"},
        {"phase": "mapping_ws21_fullscreen", "ip": "192.168.5.101", "port": 4830, "packet": b"mapping"},
        {"phase": "commit", "ip": "192.168.5.101", "port": 4830, "packet": b"commit"},
        {"phase": "refresh", "ip": "192.168.5.101", "port": 4830, "packet": b"refresh"},
    ]
    clear_b_started = threading.Event()
    clear_a_done = threading.Event()
    clear_b_done = threading.Event()

    monkeypatch.setattr(video_wall, "build_sequence", lambda _mode: sequence)

    def fake_send_packet(_ip: str, _port: int, packet: bytes) -> None:
        """
        记录并阻塞第一个 clear 包，若发送退化为串行则会触发断言。

        :param _ip: 目标 IP
        :param _port: 目标端口
        :param packet: 控制包
        :return: None
        """
        if packet == b"clear-a":
            if not clear_b_started.wait(timeout=1.0):
                raise AssertionError("clear 阶段未并行发送")
            clear_a_done.set()
        elif packet == b"clear-b":
            clear_b_started.set()
            clear_b_done.set()
        elif packet == b"mapping":
            assert clear_a_done.is_set()
            assert clear_b_done.is_set()

    monkeypatch.setattr(video_wall, "_send_tcp_packet", fake_send_packet)

    video_wall.apply_big_screen_mode(BigScreenMode.SINGLE)


def test_apply_big_screen_mode_retries_transient_packet_error(monkeypatch: Any) -> None:
    """单包瞬时失败应重试，重试成功后不应让整次切屏失败。"""
    from scp_cv.services import video_wall

    attempts = 0
    sequence = [
        {"phase": "clear", "ip": "192.168.5.101", "port": 4830, "packet": b"clear"},
    ]
    monkeypatch.setattr(video_wall, "build_sequence", lambda _mode: sequence)

    def fake_send_packet(_ip: str, _port: int, _packet: bytes) -> None:
        """
        第一次模拟现场 timed out，第二次成功。

        :param _ip: 目标 IP
        :param _port: 目标端口
        :param _packet: 控制包
        :return: None
        :raises VideoWallError: 首次发送时模拟超时
        """
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise VideoWallError("发送视频墙控制包失败：192.168.5.101:4830 timed out")

    monkeypatch.setattr(video_wall, "_send_tcp_packet", fake_send_packet)

    video_wall.apply_big_screen_mode(BigScreenMode.SINGLE)

    assert attempts == 2


def test_apply_big_screen_mode_waits_between_clear_and_mapping(monkeypatch: Any) -> None:
    """清空内容阶段完成后，应等待 100ms 再发送更改显示映射包。"""
    from scp_cv.services import video_wall

    sleep_calls: list[float] = []
    sequence = [
        {"phase": "clear", "ip": "192.168.5.101", "port": 4830, "packet": b"clear"},
        {"phase": "mapping_ws21_fullscreen", "ip": "192.168.5.101", "port": 4830, "packet": b"mapping"},
        {"phase": "commit", "ip": "192.168.5.101", "port": 4830, "packet": b"commit"},
    ]
    monkeypatch.setattr(video_wall, "build_sequence", lambda _mode: sequence)
    monkeypatch.setattr(video_wall, "_send_tcp_packet", lambda *_args: None)
    monkeypatch.setattr(video_wall.time, "sleep", lambda seconds: sleep_calls.append(seconds))

    video_wall.apply_big_screen_mode(BigScreenMode.SINGLE)

    assert sleep_calls == [0.1]


def test_apply_big_screen_mode_reports_error_after_five_attempts(monkeypatch: Any) -> None:
    """单包失败达到 5 次后应报错，并停止继续后续阶段。"""
    from scp_cv.services import video_wall

    attempts = 0
    sent_packets: list[bytes] = []
    sequence = [
        {"phase": "clear", "ip": "192.168.5.101", "port": 4830, "packet": b"clear-fail"},
        {"phase": "clear", "ip": "192.168.5.102", "port": 4830, "packet": b"clear-ok"},
        {"phase": "mapping_ws21_fullscreen", "ip": "192.168.5.102", "port": 4830, "packet": b"mapping-ok"},
        {"phase": "commit", "ip": "192.168.5.102", "port": 4830, "packet": b"commit-ok"},
        {"phase": "refresh", "ip": "192.168.5.102", "port": 4830, "packet": b"refresh-ok"},
    ]
    monkeypatch.setattr(video_wall, "build_sequence", lambda _mode: sequence)

    def fake_send_packet(_ip: str, _port: int, packet: bytes) -> None:
        """
        固定让一个节点失败，用于确认最多 5 次重试并阻断后续阶段。

        :param _ip: 目标 IP
        :param _port: 目标端口
        :param packet: 控制包
        :return: None
        :raises VideoWallError: 指定包模拟永久失败
        """
        nonlocal attempts
        sent_packets.append(packet)
        if packet == b"clear-fail":
            attempts += 1
            raise VideoWallError("发送视频墙控制包失败：192.168.5.101:4830 timed out")

    monkeypatch.setattr(video_wall, "_send_tcp_packet", fake_send_packet)
    monkeypatch.setattr(video_wall.time, "sleep", lambda _seconds: None)

    with pytest.raises(VideoWallError) as error:
        video_wall.apply_big_screen_mode(BigScreenMode.SINGLE)

    assert attempts == 5
    assert b"clear-ok" in sent_packets
    assert b"mapping-ok" not in sent_packets
    assert b"commit-ok" not in sent_packets
    assert b"refresh-ok" not in sent_packets
    assert "192.168.5.101:4830" in str(error.value)
