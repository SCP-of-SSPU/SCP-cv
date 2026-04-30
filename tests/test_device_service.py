#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
设备电源 TCP 指令服务测试。
验证拼接屏和电视电源指令帧顺序，不访问真实硬件。
@Project : SCP-cv
@File : test_device_service.py
@Author : Qintsg
@Date : 2026-04-30
'''
from __future__ import annotations

from typing import Any

import pytest

from scp_cv.services import device as device_service


class FakeSocket:
    """记录 sendall 数据的假 socket。"""

    def __init__(self, sent_frames: list[bytes]) -> None:
        """
        初始化假 socket。
        :param sent_frames: 发送帧记录列表
        :return: None
        """
        self._sent_frames = sent_frames

    def __enter__(self) -> "FakeSocket":
        """进入上下文。"""
        return self

    def __exit__(self, *_args: object) -> None:
        """退出上下文。"""

    def sendall(self, frame: bytes) -> None:
        """
        记录发送帧。
        :param frame: 发送数据
        :return: None
        """
        self._sent_frames.append(frame)


def test_splice_power_on_sends_two_tcp_frames(monkeypatch: Any) -> None:
    """拼接屏开机应按需求发送两帧并等待 5 秒。"""
    sent_frames: list[bytes] = []
    sleep_calls: list[float] = []

    monkeypatch.setattr(device_service.socket, "create_connection", lambda *_args, **_kwargs: FakeSocket(sent_frames))
    monkeypatch.setattr(device_service.time, "sleep", lambda seconds: sleep_calls.append(seconds))

    result = device_service.power_on_device("splice_screen")

    assert result["action"] == "on"
    assert sent_frames == [bytes.fromhex("FF06010A00010001FA"), bytes.fromhex("FF06010A00010000FA")]
    assert sleep_calls == [5.0]


def test_tv_left_toggle_sends_toggle_frames(monkeypatch: Any) -> None:
    """电视左切换应发送 0.1 秒间隔的两帧。"""
    sent_frames: list[bytes] = []
    sleep_calls: list[float] = []

    monkeypatch.setattr(device_service.socket, "create_connection", lambda *_args, **_kwargs: FakeSocket(sent_frames))
    monkeypatch.setattr(device_service.time, "sleep", lambda seconds: sleep_calls.append(seconds))

    result = device_service.toggle_device("tv_left")

    assert result["action"] == "toggle"
    assert sent_frames == [bytes.fromhex("FF06010A00330001FA"), bytes.fromhex("FF06010A00330000FA")]
    assert sleep_calls == [0.1]


def test_tv_rejects_power_on() -> None:
    """电视不支持单独开机接口。"""
    with pytest.raises(device_service.DeviceError, match="电视仅支持"):
        device_service.power_on_device("tv_right")
