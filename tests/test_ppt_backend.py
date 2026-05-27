#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PPT 后端枚举工具测试，覆盖 WPS 演示显式后端值。
@Project : SCP-cv
@File : test_ppt_backend.py
@Author : Qintsg
@Date : 2026-05-27
'''
from __future__ import annotations

import pytest

from scp_cv.ppt_backend import normalize_ppt_backend, ppt_backend_label


@pytest.mark.parametrize(
    ("raw_backend", "expected_backend"),
    [
        ("libreoffice", "libreoffice"),
        ("PowerPoint", "powerpoint"),
        (" WPS ", "wps"),
    ],
)
def test_normalize_ppt_backend_accepts_supported_backends(
    raw_backend: object,
    expected_backend: str,
) -> None:
    """
    后端值应支持大小写和空格归一，并接受 WPS。
    :param raw_backend: 原始后端值
    :param expected_backend: 规范化后的后端值
    :return: None
    """
    assert normalize_ppt_backend(raw_backend) == expected_backend


def test_ppt_backend_label_returns_wps_label() -> None:
    """
    WPS 后端应返回中文展示名。
    :return: None
    """
    assert ppt_backend_label("wps") == "WPS 演示"


def test_normalize_ppt_backend_rejects_auto() -> None:
    """
    auto 已删除，不应恢复隐式兜底。
    :return: None
    """
    with pytest.raises(ValueError, match="不支持"):
        normalize_ppt_backend("auto")
