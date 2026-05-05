#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
CORS 直连放行测试。
验证浏览器、手机与固定域名控制台均可直接访问 Django 后端。
@Project : SCP-cv
@File : test_cors_middleware.py
@Author : Qintsg
@Date : 2026-05-05
'''
from __future__ import annotations

from django.test import Client


def test_cors_preflight_allows_any_origin_and_private_network() -> None:
    """
    任意 Origin 的预检都应通过，并返回私网放行响应头。
    :return: None
    """
    client = Client()

    response = client.options(
        "/api/playback/1/open/",
        HTTP_HOST="127.0.0.1:8000",
        HTTP_ORIGIN="https://console.example.test",
        HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
        HTTP_ACCESS_CONTROL_REQUEST_HEADERS="Content-Type, X-Control-Token",
        HTTP_ACCESS_CONTROL_REQUEST_PRIVATE_NETWORK="true",
    )

    assert response.status_code == 204
    assert response["Access-Control-Allow-Origin"] == "*"
    assert response["Access-Control-Allow-Headers"] == "Content-Type, X-Control-Token"
    assert response["Access-Control-Allow-Private-Network"] == "true"


def test_cors_allows_cross_host_mutation_origin(db: object) -> None:
    """
    外部控制页发起的变更请求应直接进入业务视图，不再被 Origin 拦截。
    :param db: pytest-django 数据库夹具
    :return: None
    """
    client = Client()

    response = client.post(
        "/api/playback/1/close/",
        HTTP_HOST="127.0.0.1:8000",
        HTTP_ORIGIN="https://example.com",
    )

    assert response.status_code == 200
    assert response["Access-Control-Allow-Origin"] == "*"


def test_cors_allows_cross_host_read_origin(db: object) -> None:
    """
    跨主机读取请求也应统一返回放行头，便于任意控制台直接查询状态。
    :param db: pytest-django 数据库夹具
    :return: None
    """
    client = Client()

    response = client.get(
        "/api/sessions/",
        HTTP_HOST="127.0.0.1:8000",
        HTTP_ORIGIN="https://dashboard.example.test",
    )

    assert response.status_code == 200
    assert response["Access-Control-Allow-Origin"] == "*"
