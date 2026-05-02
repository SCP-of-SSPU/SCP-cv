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
from urllib.parse import urlparse

from django.conf import settings
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden
from django.utils.cache import patch_vary_headers


_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
_LOCAL_FRONTEND_PORTS = frozenset({5173, 4173})
_LOCALHOST_NAMES = frozenset({"localhost", "127.0.0.1", "::1"})


class CorsMiddleware:
    """
    本地控制台 CORS 中间件。
    默认只允许同主机 Vite 控制台跨端口访问，避免外部网页触发局域网控制请求。
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        allowed_origin = self._allowed_origin(request)
        if self._should_reject_origin(request, allowed_origin):
            return HttpResponseForbidden("Origin 不在控制台允许范围内")

        if request.method == "OPTIONS":
            # 浏览器跨域直连 Django 时会预检 PATCH/DELETE/JSON 请求。
            response = HttpResponse(status=204)
        else:
            response = self.get_response(request)
        if allowed_origin:
            response["Access-Control-Allow-Origin"] = allowed_origin
            response["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
            response["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            response["Access-Control-Max-Age"] = "86400"
            patch_vary_headers(response, ["Origin"])
        return response

    @staticmethod
    def _allowed_origin(request: HttpRequest) -> str:
        """
        判断请求 Origin 是否属于当前控制台。
        :param request: HTTP 请求
        :return: 允许时返回规范化 Origin，否则返回空字符串
        """
        origin = request.headers.get("Origin", "").strip().rstrip("/")
        if not origin:
            return ""
        if origin in getattr(settings, "SCP_CV_ALLOWED_ORIGINS", []):
            return origin

        parsed_origin = urlparse(origin)
        origin_host = (parsed_origin.hostname or "").lower()
        if parsed_origin.scheme not in {"http", "https"} or not origin_host:
            return ""

        request_host = CorsMiddleware._request_hostname(request)
        origin_port = parsed_origin.port
        same_host = origin_host == request_host
        same_localhost = origin_host in _LOCALHOST_NAMES and request_host in _LOCALHOST_NAMES
        if (same_host or same_localhost) and origin_port in _LOCAL_FRONTEND_PORTS:
            return origin
        return ""

    @staticmethod
    def _request_hostname(request: HttpRequest) -> str:
        """
        提取 Host 头中的主机名，兼容 IPv4、域名和方括号 IPv6。
        :param request: HTTP 请求
        :return: 小写主机名
        """
        request_host = request.get_host().strip().lower()
        if request_host.startswith("[") and "]" in request_host:
            return request_host[1:request_host.index("]")]
        return request_host.split(":", 1)[0]

    @staticmethod
    def _should_reject_origin(request: HttpRequest, allowed_origin: str) -> bool:
        """
        拒绝带外部 Origin 的变更请求和预检请求。
        :param request: HTTP 请求
        :param allowed_origin: 通过校验的 Origin
        :return: True 表示立即返回 403
        """
        has_origin = bool(request.headers.get("Origin", "").strip())
        if not has_origin or allowed_origin:
            return False
        return request.method not in _SAFE_METHODS or request.method == "OPTIONS"
