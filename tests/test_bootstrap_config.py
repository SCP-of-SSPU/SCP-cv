#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
固定启动数据配置测试。
@Project : SCP-cv
@File : test_bootstrap_config.py
@Author : Qintsg
@Date : 2026-05-27
'''
from __future__ import annotations

from pathlib import Path

import pytest
from django.contrib.auth import get_user_model

from scp_cv.bootstrap_config import (
    create_default_admin_from_config,
    get_default_admin_config,
)


def test_get_default_admin_config_reads_config_toml(tmp_path: Path) -> None:
    """
    默认管理员固定数据应从 config.toml 读取。
    :param tmp_path: pytest 临时目录 fixture
    :return: None
    """
    (tmp_path / "config.toml").write_text(
        """
[auth.default_admin]
username = "root"
password = "secret"
email = "root@example.local"
is_staff = true
is_superuser = true
is_active = true
""".strip(),
        encoding="utf-8",
    )

    admin_config = get_default_admin_config(tmp_path)

    assert admin_config is not None
    assert admin_config.username == "root"
    assert admin_config.password == "secret"
    assert admin_config.email == "root@example.local"
    assert admin_config.is_staff is True
    assert admin_config.is_superuser is True
    assert admin_config.is_active is True


@pytest.mark.django_db
def test_create_default_admin_from_config_creates_user(tmp_path: Path) -> None:
    """
    固定配置播种应创建默认管理员且不会覆盖已存在用户。
    :param tmp_path: pytest 临时目录 fixture
    :return: None
    """
    (tmp_path / "config.toml").write_text(
        """
[auth.default_admin]
username = "clear-admin"
password = "clear-password"
email = "clear@example.local"
is_staff = true
is_superuser = true
is_active = true
""".strip(),
        encoding="utf-8",
    )
    user_model = get_user_model()

    created_first = create_default_admin_from_config(user_model, tmp_path)
    created_second = create_default_admin_from_config(user_model, tmp_path)

    user = user_model.objects.get(username="clear-admin")
    assert created_first is True
    assert created_second is False
    assert user.check_password("clear-password") is True
    assert user.email == "clear@example.local"
    assert user.is_staff is True
    assert user.is_superuser is True
