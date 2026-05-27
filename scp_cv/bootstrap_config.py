#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
固定启动数据配置读取与播种工具。
@Project : SCP-cv
@File : bootstrap_config.py
@Author : Qintsg
@Date : 2026-05-27
'''
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import tomllib

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.core.exceptions import ImproperlyConfigured


@dataclass(frozen=True)
class DefaultAdminConfig:
    """
    默认管理员固定数据配置。
    """

    username: str
    password: str
    email: str
    is_staff: bool
    is_superuser: bool
    is_active: bool


def config_path(base_dir: Path | None = None) -> Path:
    """
    返回项目固定数据配置文件路径。
    :param base_dir: 项目根目录；未传时使用 Django settings.BASE_DIR
    :return: config.toml 路径
    """
    root_dir = Path(base_dir) if base_dir is not None else Path(settings.BASE_DIR)
    return root_dir / "config.toml"


def load_config(base_dir: Path | None = None) -> dict[str, Any]:
    """
    读取固定数据配置。
    :param base_dir: 项目根目录；未传时使用 Django settings.BASE_DIR
    :return: TOML 配置字典；配置文件不存在时返回空字典
    """
    path = config_path(base_dir)
    if not path.exists():
        return {}
    try:
        with path.open("rb") as config_file:
            loaded = tomllib.load(config_file)
    except tomllib.TOMLDecodeError as decode_error:
        raise ImproperlyConfigured(f"config.toml 格式错误：{decode_error}") from decode_error
    if not isinstance(loaded, dict):
        raise ImproperlyConfigured("config.toml 顶层必须是 TOML 表")
    return loaded


def get_default_admin_config(base_dir: Path | None = None) -> DefaultAdminConfig | None:
    """
    读取默认管理员配置。
    :param base_dir: 项目根目录；未传时使用 Django settings.BASE_DIR
    :return: 默认管理员配置；未配置时返回 None
    """
    raw_config = load_config(base_dir)
    auth_config = raw_config.get("auth", {})
    if not isinstance(auth_config, dict):
        raise ImproperlyConfigured("config.toml 中 [auth] 必须是表")
    admin_config = auth_config.get("default_admin")
    if admin_config is None:
        return None
    if not isinstance(admin_config, dict):
        raise ImproperlyConfigured("config.toml 中 [auth.default_admin] 必须是表")

    username = str(admin_config.get("username", "")).strip()
    password = str(admin_config.get("password", ""))
    if not username:
        raise ImproperlyConfigured("config.toml 的 auth.default_admin.username 不能为空")
    if not password:
        raise ImproperlyConfigured("config.toml 的 auth.default_admin.password 不能为空")

    return DefaultAdminConfig(
        username=username,
        password=password,
        email=str(admin_config.get("email", "")),
        is_staff=bool(admin_config.get("is_staff", True)),
        is_superuser=bool(admin_config.get("is_superuser", True)),
        is_active=bool(admin_config.get("is_active", True)),
    )


def create_default_admin_from_config(user_model: Any, base_dir: Path | None = None) -> bool:
    """
    根据 config.toml 创建默认管理员。
    :param user_model: Django User 历史模型或当前模型类
    :param base_dir: 项目根目录；未传时使用 Django settings.BASE_DIR
    :return: True 表示本次创建了用户，False 表示未配置或已存在
    """
    admin_config = get_default_admin_config(base_dir)
    if admin_config is None:
        return False
    if user_model.objects.filter(username=admin_config.username).exists():
        return False
    user_model.objects.create(
        username=admin_config.username,
        password=make_password(admin_config.password),
        is_staff=admin_config.is_staff,
        is_superuser=admin_config.is_superuser,
        is_active=admin_config.is_active,
        first_name="",
        last_name="",
        email=admin_config.email,
    )
    return True


def delete_default_admin_from_config(user_model: Any, base_dir: Path | None = None) -> int:
    """
    根据 config.toml 删除默认管理员。
    :param user_model: Django User 历史模型或当前模型类
    :param base_dir: 项目根目录；未传时使用 Django settings.BASE_DIR
    :return: 删除的用户数量
    """
    admin_config = get_default_admin_config(base_dir)
    if admin_config is None:
        return 0
    deleted_count, _ = user_model.objects.filter(username=admin_config.username).delete()
    return int(deleted_count)
