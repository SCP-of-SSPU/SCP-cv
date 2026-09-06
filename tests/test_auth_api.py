#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
鉴权接口与受保护资源访问测试。
@Project : SCP-cv
@File : test_auth_api.py
@Author : Qintsg
@Date : 2026-08-23
'''
from __future__ import annotations

import json

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.test import override_settings


@pytest.mark.django_db
def test_auth_status_returns_anonymous_without_401(anonymous_client: Client) -> None:
    """未登录访问 auth/status 应返回 200 且 authenticated=false。"""
    response = anonymous_client.get("/api/auth/status/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["authenticated"] is False
    assert payload["user"] is None


@pytest.mark.django_db
def test_auth_status_returns_user_when_logged_in() -> None:
    """已登录访问 auth/status 应返回用户信息。"""
    user = get_user_model().objects.create_user(username="operator", password="Old-password-123")
    client = Client(enforce_csrf_checks=False)
    client.force_login(user)

    response = client.get("/api/auth/status/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["authenticated"] is True
    assert payload["user"]["username"] == "operator"


def test_media_files_require_authentication(anonymous_client: Client) -> None:
    """
    未登录客户端访问媒体文件路径时应被鉴权中间件拒绝。

    :param anonymous_client: 未登录 Django 测试客户端
    :return: None
    """
    response = anonymous_client.get("/media/uploads/private.png")

    assert response.status_code == 401
    assert response.json()["code"] == "unauthorized"


@pytest.mark.django_db
@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
def test_authenticated_user_can_change_password_and_keep_session() -> None:
    user = get_user_model().objects.create_user(username="operator", password="Old-password-123")
    client = Client(enforce_csrf_checks=False)
    client.force_login(user)

    response = client.post(
        "/api/auth/change-password/",
        data=json.dumps({"current_password": "Old-password-123", "new_password": "New-password-456"}),
        content_type="application/json",
    )

    assert response.status_code == 200
    user.refresh_from_db()
    assert user.check_password("New-password-456") is True
    assert client.get("/api/auth/me/").status_code == 200


@pytest.mark.django_db
@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
def test_change_password_rejects_wrong_current_password() -> None:
    user = get_user_model().objects.create_user(username="operator", password="Old-password-123")
    client = Client(enforce_csrf_checks=False)
    client.force_login(user)

    response = client.post(
        "/api/auth/change-password/",
        data=json.dumps({"current_password": "wrong", "new_password": "New-password-456"}),
        content_type="application/json",
    )

    assert response.status_code == 400
    user.refresh_from_db()
    assert user.check_password("Old-password-123") is True
