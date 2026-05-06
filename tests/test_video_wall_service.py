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
