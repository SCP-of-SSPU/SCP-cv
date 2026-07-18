from __future__ import annotations

import json

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.test import override_settings


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
