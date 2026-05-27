#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PPT 播放器后端选择工具。
@Project : SCP-cv
@File : ppt_backend.py
@Author : Qintsg
@Date : 2026-05-26
'''
from __future__ import annotations

PPT_BACKEND_LIBREOFFICE = "libreoffice"
PPT_BACKEND_POWERPOINT = "powerpoint"
PPT_BACKEND_WPS = "wps"
SUPPORTED_PPT_BACKENDS = frozenset({
    PPT_BACKEND_LIBREOFFICE,
    PPT_BACKEND_POWERPOINT,
    PPT_BACKEND_WPS,
})
DEFAULT_PPT_BACKEND = PPT_BACKEND_LIBREOFFICE
PPT_BACKEND_LABELS = {
    PPT_BACKEND_LIBREOFFICE: "LibreOffice（稳定）",
    PPT_BACKEND_POWERPOINT: "Microsoft PowerPoint",
    PPT_BACKEND_WPS: "WPS 演示",
}


def normalize_ppt_backend(raw_backend: object, default: str = DEFAULT_PPT_BACKEND) -> str:
    """
    规范化 PPT 播放器后端值。
    :param raw_backend: 用户输入或数据库字段值
    :param default: 空值时使用的默认后端
    :return: 后端枚举值字符串
    :raises ValueError: 后端值不受支持时
    """
    backend = str(raw_backend or default).strip().lower()
    if backend not in SUPPORTED_PPT_BACKENDS:
        raise ValueError(f"不支持的 PPT 播放器：{backend}")
    return backend


def ppt_backend_label(backend: object) -> str:
    """
    获取 PPT 播放器后端展示名称。
    :param backend: 后端值
    :return: 中文展示名称
    """
    normalized = normalize_ppt_backend(backend)
    return PPT_BACKEND_LABELS.get(normalized, str(normalized))


__all__ = [
    "DEFAULT_PPT_BACKEND",
    "PPT_BACKEND_LIBREOFFICE",
    "PPT_BACKEND_POWERPOINT",
    "PPT_BACKEND_WPS",
    "PPT_BACKEND_LABELS",
    "SUPPORTED_PPT_BACKENDS",
    "normalize_ppt_backend",
    "ppt_backend_label",
]
