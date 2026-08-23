#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
pytest 全局夹具。
自鉴权落地后，REST 接口默认要求登录；为了让既有大量函数视图测试无需逐个
改造，本文件提供 autouse fixture：
  - 在每条 django_db 测试启动前自动创建 admin/admin 超级用户；
  - monkey-patch django.test.Client 的 __init__，让默认实例化即处于已登录态。

测试若需要显式验证未登录行为，可通过 anonymous_client fixture 拿到原始 Client。
@Project : SCP-cv
@File : conftest.py
@Author : Qintsg
@Date : 2026-05-21
'''
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest


_TEST_USERNAME = "admin"
_TEST_PASSWORD = "admin"


@pytest.fixture(autouse=True)
def _allow_test_local_media_root(tmp_path: Path, settings: Any) -> None:
    """
    允许测试使用各自隔离的临时目录作为本地媒体根目录。

    :param tmp_path: 当前测试隔离目录
    :param settings: pytest-django 设置对象
    :return: None
    """
    settings.LOCAL_MEDIA_ALLOWED_ROOTS = [tmp_path, Path(settings.MEDIA_ROOT)]


@pytest.fixture(autouse=True)
def _disable_slides_pdf_auto_convert(settings) -> None:
    """单元测试默认不触发 PowerPoint COM 的演示文稿 PDF 自动导出。"""
    settings.SLIDES_PDF_AUTO_CONVERT = False


@pytest.fixture(autouse=True)
def _ensure_test_admin(request: pytest.FixtureRequest) -> None:
    """
    若用例需要数据库（标记 django_db / 间接依赖 db 夹具），自动播种 admin 用户
    并替换 Client.__init__ 使新建实例直接以 admin 登录。
    :param request: pytest 当前用例上下文
    :return: None
    """
    needs_db = "db" in request.fixturenames or "transactional_db" in request.fixturenames
    if not needs_db:
        for marker in request.node.iter_markers():
            if marker.name == "django_db":
                needs_db = True
                break
    if not needs_db:
        yield
        return

    # 显式触发 db / transactional_db fixture 在本 autouse 之前完成数据库准备，
    # 否则 ORM 查询会因 pytest-django 的 db 阻断保护而 RuntimeError。
    if "transactional_db" in request.fixturenames:
        request.getfixturevalue("transactional_db")
    else:
        request.getfixturevalue("db")

    from django.contrib.auth import get_user_model
    from django.test import Client

    user_model = get_user_model()
    if not user_model.objects.filter(username=_TEST_USERNAME).exists():
        user_model.objects.create_superuser(
            username=_TEST_USERNAME,
            email="",
            password=_TEST_PASSWORD,
        )

    original_init = Client.__init__

    def _logged_in_init(self, *args, **kwargs) -> None:
        # kwargs 支持 _scp_cv_skip_auto_login=True 关闭自动登录，便于显式测试匿名行为。
        skip_login = kwargs.pop("_scp_cv_skip_auto_login", False)
        original_init(self, *args, **kwargs)
        if not skip_login:
            self.login(username=_TEST_USERNAME, password=_TEST_PASSWORD)

    Client.__init__ = _logged_in_init  # type: ignore[assignment]
    try:
        yield
    finally:
        Client.__init__ = original_init  # type: ignore[assignment]


@pytest.fixture()
def anonymous_client():
    """
    返回未登录的原始 Client，用于显式验证 401 行为。
    :return: django.test.Client 实例
    """
    from django.test import Client

    return Client(_scp_cv_skip_auto_login=True)
