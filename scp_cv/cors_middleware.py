#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
CORS 中间件：为 SCP-cv 本地桌面工具添加跨域响应头。
前端 Vite 开发服务器直接访问 Django 后端时浏览器需要 CORS 头。
@Project : SCP-cv
@File : cors_middleware.py
@Author : Qintsg
@Date : 2026-04-29
'''
from __future__ import annotations

from collections.abc import Callable

from django.http import HttpRequest, HttpResponse


class CorsMiddleware:
    """
    开发阶段全局 CORS 中间件，允许任意源发起 API 请求。
    注意：此为本地桌面工具，生产环境应限制为具体域名。
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if request.method == "OPTIONS":
            # 浏览器跨域直连 Django 时会预检 PATCH/DELETE/JSON 请求。
            response = HttpResponse(status=204)
        else:
            response = self.get_response(request)
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response["Access-Control-Max-Age"] = "86400"
        return response
