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

from scp_cv.services.mediamtx import get_srt_publish_url, get_srt_read_url


def test_publish_url_uses_configured_public_host(settings: object) -> None:
    """
    SRT 推流地址应使用可配置公网/局域网主机，供外部设备连接。
    :param settings: pytest-django settings fixture
    :return: None
    """
    settings.MEDIAMTX_SRT_PUBLIC_HOST = "192.168.1.100"

    assert get_srt_publish_url("camera-a") == "srt://192.168.1.100:8890?streamid=publish:camera-a&latency=30000"


def test_read_url_uses_configured_read_host(settings: object) -> None:
    """
    SRT 拉流地址支持配置局域网主机，供其它设备读取。
    :param settings: pytest-django settings fixture
    :return: None
    """
    settings.MEDIAMTX_SRT_READ_HOST = "192.168.1.100"

    assert get_srt_read_url("camera-a") == "srt://192.168.1.100:8890?streamid=read:camera-a&latency=30000"
