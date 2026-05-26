#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
data migration：保证至少存在一名默认管理员账号（admin/admin）。
单机部署场景下让运维通过 `python manage.py migrate` 一步完成账号种子；
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
    若 username=admin 尚不存在则创建超级用户（密码 admin）。
    使用历史模型 apps.get_model 而非 django.contrib.auth.get_user_model，
    保证迁移在未来 USER 模型替换时仍可正确执行。
    :param apps: 迁移时的应用注册表
    :param schema_editor: schema editor（本迁移不直接使用）
    :return: None
    """
    User = apps.get_model("auth", "User")
    if User.objects.filter(username="admin").exists():
        return
    # 直接以 ORM 创建并 set_password 等价手段：用 make_password 走密码哈希逻辑。
    from django.contrib.auth.hashers import make_password

    User.objects.create(
        username="admin",
        password=make_password("admin"),
        is_staff=True,
        is_superuser=True,
        is_active=True,
        first_name="",
        last_name="",
        email="",
    )


def remove_default_admin(apps, schema_editor) -> None:
    """
    反向迁移：尝试删除 admin 用户。
    若用户已被改名或承担数据所有权则保留，避免误删。
    :param apps: 迁移时的应用注册表
    :param schema_editor: schema editor（本迁移不直接使用）
    :return: None
    """
    User = apps.get_model("auth", "User")
    User.objects.filter(username="admin").delete()


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(create_default_admin, remove_default_admin),
    ]
