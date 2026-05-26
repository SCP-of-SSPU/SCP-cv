#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
API 鉴权中间件：要求所有 /api/ 接口必须已登录。
未登录请求统一返回 401 JSON（而非 302 重定向到登录页），便于 Vue 前端的
axios 拦截器集中处理：未登录 → 清 Pinia → 跳 /login。

放行白名单：登录、登出、获取 CSRF、查询当前用户。
@Project : SCP-cv
@File : auth_middleware.py
@Author : Qintsg
@Date : 2026-05-21
'''
from __future__ import annotations

from collections.abc import Callable

from django.http import HttpRequest, HttpResponse, JsonResponse


# 未登录时仍可访问的接口前缀：登录态自身的获取与建立。
_PUBLIC_PATHS = (
    "/api/auth/login/",
    "/api/auth/logout/",
    "/api/auth/csrf/",
    "/api/auth/me/",
)

# 需要鉴权保护的业务前缀。/api/ 是 SPA 主入口，其余 dashboard 旧路径同样涉及
# 状态变更与 SSE 推送，统一挡在登录态后。
_PROTECTED_PREFIXES = (
    "/api/",
    "/sources/",
    "/playback/",
    "/scenarios/",
    "/events/",
)


class ApiAuthMiddleware:
    """
    针对 API / 业务路由的轻量鉴权拦截器。
    DRF 视图也走 IsAuthenticated；本中间件主要保护项目中大量纯 Django
    函数视图（api_views / api_playback_views / api_scenario_views）以及
    dashboard 旧版直连端点。
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if self._needs_auth(request):
            user = getattr(request, "user", None)
            if user is None or not getattr(user, "is_authenticated", False):
                return JsonResponse(
                    {"detail": "未登录或会话已过期", "code": "unauthorized"},
                    status=401,
                )
        return self.get_response(request)

    @staticmethod
    def _needs_auth(request: HttpRequest) -> bool:
        """
        判断当前请求是否落在受保护范围内。
        :param request: HTTP 请求
        :return: True 表示需要登录才能访问
        """
        path = request.path
        if request.method == "OPTIONS":
            # 预检请求无 cookie 可参考，统一放行交给 CORS 中间件。
            return False
        # 公开端点（登录、获取 CSRF 等）不需要鉴权，先于保护检查处理。
        for prefix in _PUBLIC_PATHS:
            if path.startswith(prefix):
                return False
        for prefix in _PROTECTED_PREFIXES:
            if path.startswith(prefix):
                return True
        return False
