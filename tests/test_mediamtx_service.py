#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
MediaMTX 服务单元测试。
覆盖局域网推流地址与本机拉流地址生成规则。
@Project : SCP-cv
@File : test_mediamtx_service.py
@Author : Qintsg
@Date : 2026-04-28
'''
from __future__ import annotations

from scp_cv.services.mediamtx import get_rtsp_read_url, get_srt_publish_url, get_srt_read_url


def test_publish_url_uses_configured_public_host(settings: object) -> None:
    """
    SRT 推流地址应使用可配置公网/局域网主机，供外部设备连接。
    :param settings: pytest-django settings fixture
    :return: None
    """
    settings.MEDIAMTX_SRT_PUBLIC_HOST = "192.168.1.100"

    assert (
        get_srt_publish_url("camera-a")
        == "srt://192.168.1.100:8890?streamid=publish:camera-a&latency=30000&pkt_size=1316"
    )


def test_read_url_uses_configured_read_host(settings: object) -> None:
    """
    SRT 拉流地址支持配置局域网主机，供其它设备读取。
    :param settings: pytest-django settings fixture
    :return: None
    """
    settings.MEDIAMTX_SRT_READ_HOST = "192.168.1.100"

    assert get_srt_read_url("camera-a") == "srt://192.168.1.100:8890?streamid=read:camera-a&latency=50"


def test_read_url_defaults_to_loopback_when_unconfigured(settings: object) -> None:
    """
    SRT 拉流地址默认面向同机播放器，避免局域网地址受防火墙或网卡路径影响。
    :param settings: pytest-django settings fixture
    :return: None
    """
    settings.MEDIAMTX_SRT_READ_HOST = ""

    assert get_srt_read_url("camera-a") == "srt://127.0.0.1:8890?streamid=read:camera-a&latency=50"


def test_rtsp_read_url_defaults_to_loopback(settings: object) -> None:
    """
    RTSP 拉流地址默认面向同机播放器。
    :param settings: pytest-django settings fixture
    :return: None
    """
    settings.MEDIAMTX_SRT_READ_HOST = ""

    assert get_rtsp_read_url("camera-a") == "rtsp://127.0.0.1:8554/camera-a"


def test_srt_latency_values_are_configurable(settings: object) -> None:
    """
    SRT 推流/拉流 latency 应允许通过 settings 覆盖，便于现场调参。
    :param settings: pytest-django settings fixture
    :return: None
    """
    settings.MEDIAMTX_SRT_PUBLIC_HOST = "10.0.0.5"
    settings.MEDIAMTX_SRT_READ_HOST = "10.0.0.6"
    settings.MEDIAMTX_SRT_PUBLISH_LATENCY_US = 120000
    settings.MEDIAMTX_SRT_READ_LATENCY_MS = 120

    assert (
        get_srt_publish_url("camera-a")
        == "srt://10.0.0.5:8890?streamid=publish:camera-a&latency=120000&pkt_size=1316"
    )
    assert get_srt_read_url("camera-a") == "srt://10.0.0.6:8890?streamid=read:camera-a&latency=120"
