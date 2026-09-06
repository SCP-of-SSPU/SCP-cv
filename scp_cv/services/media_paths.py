#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
本地媒体路径安全策略，统一维护上传目录与显式允许根校验。
@Project : SCP-cv
@File : media_paths.py
@Author : Qintsg
@Date : 2026-08-23
'''
from __future__ import annotations

from pathlib import Path

from django.conf import settings

from scp_cv.services.media_types import MediaError


def allowed_local_media_roots() -> tuple[Path, ...]:
    """
    返回本地媒体可读取根目录，并始终包含 Django 上传目录。

    :return: 去重后的绝对路径元组
    """
    configured_roots = getattr(settings, "LOCAL_MEDIA_ALLOWED_ROOTS", ())
    candidate_roots = [Path(settings.MEDIA_ROOT), *configured_roots]
    allowed_roots: list[Path] = []
    for candidate_root in candidate_roots:
        resolved_root = Path(candidate_root).expanduser().resolve()
        if resolved_root not in allowed_roots:
            allowed_roots.append(resolved_root)
    return tuple(allowed_roots)


def validate_local_media_path(file_path: Path) -> Path:
    """
    校验本地媒体文件位于上传目录或显式允许的目录中。

    :param file_path: 待校验的本地文件路径
    :return: 已解析的绝对路径
    :raises MediaError: 文件不属于任一允许目录
    """
    resolved_path = file_path.expanduser().resolve()
    allowed_roots = allowed_local_media_roots()
    if any(
        resolved_path == root or resolved_path.is_relative_to(root)
        for root in allowed_roots
    ):
        return resolved_path
    readable_roots = "、".join(str(root) for root in allowed_roots) or "未配置"
    raise MediaError(
        f"本地文件不在允许目录中：{resolved_path}；请将文件放入 {readable_roots}，"
        "或配置 LOCAL_MEDIA_ALLOWED_ROOTS"
    )
