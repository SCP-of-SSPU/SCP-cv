#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
鉴权 REST API 视图：登录、登出、获取 CSRF、查询当前用户。
所有端点都返回 JSON；登录端点会建立 Django session cookie 与 CSRF cookie，
后续业务接口由 ApiAuthMiddleware 校验 request.user.is_authenticated。
@Project : SCP-cv
@File : api_auth_views.py
@Author : Qintsg
@Date : 2026-05-21
'''
from __future__ import annotations

import json
from typing import Any

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.http import HttpRequest, JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST


def _json(payload: dict[str, Any], status: int = 200) -> JsonResponse:
    """
    统一 JSON 响应封装。
    :param payload: 响应体
    :param status: HTTP 状态码
    :return: JsonResponse 实例
    """
    return JsonResponse(payload, status=status, json_dumps_params={"ensure_ascii": False})


def _parse_body(request: HttpRequest) -> dict[str, Any]:
    """
    解析 JSON 请求体；非 JSON 或空请求返回空字典。
    :param request: HTTP 请求
    :return: 解析后的字典
    """
    if not request.body:
        return {}
    try:
        data = json.loads(request.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    return data


def _user_payload(user: Any) -> dict[str, Any]:
    """
    序列化用户的可下发字段；不包含敏感信息（密码哈希等）。
    :param user: Django 用户实例
    :return: 字典
    """
    return {
        "id": user.id,
        "username": user.get_username(),
        "is_staff": bool(user.is_staff),
        "is_superuser": bool(user.is_superuser),
    }


@require_GET
@ensure_csrf_cookie
def csrf_token_api(request: HttpRequest) -> JsonResponse:
    """
    显式触发 CSRF cookie 下发。
    前端首次加载时调用一次本接口，将 csrftoken cookie 写入；之后任意 POST/PUT/PATCH/DELETE
    请求都从 cookie 读出该 token 并回填到 X-CSRFToken 请求头，绕过 CsrfViewMiddleware 校验。
    :param request: HTTP 请求
    :return: JSON {"csrfToken": "..."}
    """
    return _json({"csrfToken": get_token(request)})


@csrf_exempt
@require_POST
@ensure_csrf_cookie
def login_api(request: HttpRequest) -> JsonResponse:
    """
    使用 username / password 建立 Django session。

    端点本身豁免 CSRF 校验（用户尚未登录，无可被 CSRF 滥用的会话状态，且跨
    端口/反向代理场景下浏览器可能尚未持有 csrftoken cookie）。登录成功后通过
    @ensure_csrf_cookie 强制下发新的 csrftoken，后续业务接口仍受 CSRF 保护。
    :param request: HTTP 请求（JSON body：{"username": "...", "password": "..."}）
    :return: 成功返回当前用户信息；失败返回 400/401 错误码
    """
    data = _parse_body(request)
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    if not username or not password:
        return _json({"detail": "用户名和密码不能为空", "code": "invalid_credentials"}, status=400)
    user = authenticate(request, username=username, password=password)
    if user is None:
        return _json({"detail": "用户名或密码错误", "code": "invalid_credentials"}, status=401)
    login(request, user)
    return _json({"user": _user_payload(user)})


@csrf_exempt
@require_POST
def logout_api(request: HttpRequest) -> JsonResponse:
    """
    清除 Django session。
    无论用户是否登录都返回 200，保持 idempotent。
    :param request: HTTP 请求
    :return: {"detail": "ok"}
    """
    logout(request)
    return _json({"detail": "ok"})


@require_GET
def me_api(request: HttpRequest) -> JsonResponse:
    """
    返回当前会话用户。未登录时返回 401，便于前端首屏判断登录态。
    :param request: HTTP 请求
    :return: 已登录返回用户信息；未登录返回 401
    """
    user = request.user
    if not user.is_authenticated:
        return _json({"detail": "未登录", "code": "unauthorized"}, status=401)
    return _json({"user": _user_payload(user)})


@require_GET
def status_api(request: HttpRequest) -> JsonResponse:
    """
    返回当前登录态，未登录时返回 200 而不是 401，避免浏览器控制台产生噪声。
    :param request: HTTP 请求
    :return: {"authenticated": bool, "user": 用户信息或 None}
    """
    user = request.user
    if not user.is_authenticated:
        return _json({"authenticated": False, "user": None})
    return _json({"authenticated": True, "user": _user_payload(user)})


@require_POST
def change_password_api(request: HttpRequest) -> JsonResponse:
    """校验旧密码并修改当前用户密码，成功后保持现有登录会话。"""
    user = request.user
    if not user.is_authenticated:
        return _json({"detail": "未登录", "code": "unauthorized"}, status=401)
    data = _parse_body(request)
    current_password = str(data.get("current_password") or "")
    new_password = str(data.get("new_password") or "")
    if not user.check_password(current_password):
        return _json({"detail": "当前密码错误", "code": "invalid_password"}, status=400)
    try:
        validate_password(new_password, user=user)
    except ValidationError as validation_error:
        return _json({"detail": "；".join(validation_error.messages), "code": "weak_password"}, status=400)
    user.set_password(new_password)
    user.save(update_fields=["password"])
    login(request, user)
    return _json({"detail": "密码已修改"})
