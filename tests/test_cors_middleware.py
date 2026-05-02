#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
CORS 与 Origin 防护测试。
验证控制端默认只接受同主机前端 Origin，避免第三方网页触发局域网控制请求。
@Project : SCP-cv
@File : test_cors_middleware.py
@Author : Qintsg
@Date : 2026-05-02
'''
from __future__ import annotations

from django.test import Client, override_settings


@override_settings(SCP_CV_ALLOWED_ORIGINS=[])
def test_cors_preflight_allows_same_host_vite_origin() -> None:
    """
    同主机 Vite 控制台预检应通过，并回显具体 Origin。
    :return: None
    """
    client = Client()

    response = client.options(
        "/api/playback/1/open/",
        HTTP_HOST="127.0.0.1:8000",
        HTTP_ORIGIN="http://127.0.0.1:5173",
    )

    assert response.status_code == 204
    assert response["Access-Control-Allow-Origin"] == "http://127.0.0.1:5173"
    assert response["Vary"] == "Origin"


@override_settings(SCP_CV_ALLOWED_ORIGINS=[])
def test_cors_rejects_cross_host_mutation_origin() -> None:
    """
    外部网页发起的变更请求应在进入业务视图前被拒绝。
    :return: None
    """
    client = Client()

    response = client.post(
        "/api/playback/1/close/",
        HTTP_HOST="127.0.0.1:8000",
        HTTP_ORIGIN="https://example.com",
    )

    assert response.status_code == 403
    assert "Access-Control-Allow-Origin" not in response


@override_settings(SCP_CV_ALLOWED_ORIGINS=["https://console.example.test"])
def test_cors_allows_explicit_configured_origin() -> None:
    """
    显式配置的控制台 Origin 应允许跨域访问，便于固定域名部署。
    :return: None
    """
    client = Client()

    response = client.options(
        "/api/playback/1/open/",
        HTTP_HOST="127.0.0.1:8000",
        HTTP_ORIGIN="https://console.example.test",
    )

    assert response.status_code == 204
    assert response["Access-Control-Allow-Origin"] == "https://console.example.test"
