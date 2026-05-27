#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
data migration：保证存在 config.toml 定义的默认管理员账号。
单机部署场景下让运维通过 `python manage.py migrate` 一步完成固定数据播种；
若已经存在 admin 用户则保留原密码不动，避免覆盖运维已修改的凭据。
@Project : SCP-cv
@File : 0001_create_default_admin.py
@Author : Qintsg
@Date : 2026-05-21
'''
from __future__ import annotations

from django.db import migrations


def create_default_admin(apps, schema_editor) -> None:
    """
    若 config.toml 中的默认管理员尚不存在则创建超级用户。
    使用历史模型 apps.get_model 而非 django.contrib.auth.get_user_model，
    保证迁移在未来 USER 模型替换时仍可正确执行。
    :param apps: 迁移时的应用注册表
    :param schema_editor: schema editor（本迁移不直接使用）
    :return: None
    """
    from scp_cv.bootstrap_config import create_default_admin_from_config

    User = apps.get_model("auth", "User")
    create_default_admin_from_config(User)


def remove_default_admin(apps, schema_editor) -> None:
    """
    反向迁移：尝试删除 config.toml 定义的默认管理员。
    若用户已被改名或承担数据所有权则保留，避免误删。
    :param apps: 迁移时的应用注册表
    :param schema_editor: schema editor（本迁移不直接使用）
    :return: None
    """
    from scp_cv.bootstrap_config import delete_default_admin_from_config

    User = apps.get_model("auth", "User")
    delete_default_admin_from_config(User)


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(create_default_admin, remove_default_admin),
    ]
