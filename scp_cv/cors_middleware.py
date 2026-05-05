#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
CORS 中间件：为 SCP-cv 直接连接场景统一放开跨域响应头。
前端 Vite 控制台、手机浏览器与固定域名控制页都可以直接访问 Django 后端。
@Project : SCP-cv
@File : cors_middleware.py
@Author : Qintsg
@Date : 2026-05-05
'''
from __future__ import annotations

from collections.abc import Callable

from django.http import HttpRequest, HttpResponse


_ALLOW_METHODS = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
_DEFAULT_ALLOW_HEADERS = "Content-Type, Authorization, X-Requested-With"


class CorsMiddleware:
    """
    为浏览器直连场景补齐通用 CORS 响应头。
    保持 API 与媒体资源可从任意 Origin 直接访问，避免局域网或固定域名控制台受限。
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if request.method == "OPTIONS":
            # 浏览器跨域直连 Django 时会为 JSON / PATCH / DELETE 请求发送预检。
            response = HttpResponse(status=204)
        else:
            response = self.get_response(request)
        self._apply_cors_headers(request, response)
        return response

    @staticmethod
    def _apply_cors_headers(request: HttpRequest, response: HttpResponse) -> None:
        """
        向所有响应补齐允许直连所需的跨域头。
        :param request: HTTP 请求
        :param response: HTTP 响应
        :return: None
        """
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = _ALLOW_METHODS
        response["Access-Control-Allow-Headers"] = (
            request.headers.get("Access-Control-Request-Headers", "").strip()
            or _DEFAULT_ALLOW_HEADERS
        )
        response["Access-Control-Max-Age"] = "86400"
        if request.headers.get("Access-Control-Request-Private-Network", "").lower() == "true":
            response["Access-Control-Allow-Private-Network"] = "true"
