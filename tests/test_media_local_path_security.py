#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
本地媒体路径安全测试，覆盖登记与下载阶段的允许根校验。
@Project : SCP-cv
@File : test_media_local_path_security.py
@Author : Qintsg
@Date : 2026-08-23
'''
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from scp_cv.apps.playback.models import MediaSource, SourceType
from scp_cv.services.media import (
    MediaError,
    add_local_path,
    add_uploaded_file,
    get_source_download_info,
    get_source_preview_file_info,
)


@pytest.mark.django_db
def test_local_path_outside_allowed_roots_is_rejected(
    tmp_path: Path,
    settings: Any,
) -> None:
    """
    新增本地媒体源时拒绝允许根之外的文件。

    :param tmp_path: 临时文件目录
    :param settings: pytest-django 设置对象
    :return: None
    """
    allowed_root = tmp_path / "allowed"
    allowed_root.mkdir()
    outside_file = tmp_path / "private.png"
    outside_file.write_bytes(b"private")
    settings.LOCAL_MEDIA_ALLOWED_ROOTS = [allowed_root]

    with pytest.raises(MediaError, match="允许目录"):
        add_local_path(str(outside_file))


@pytest.mark.django_db
def test_download_revalidates_legacy_local_path(
    tmp_path: Path,
    settings: Any,
) -> None:
    """
    下载升级前已登记的本地源时仍需重新校验允许根。

    :param tmp_path: 临时文件目录
    :param settings: pytest-django 设置对象
    :return: None
    """
    allowed_root = tmp_path / "allowed"
    allowed_root.mkdir()
    outside_file = tmp_path / "legacy-private.mp4"
    outside_file.write_bytes(b"private")
    settings.LOCAL_MEDIA_ALLOWED_ROOTS = [allowed_root]
    source = MediaSource.objects.create(
        source_type=SourceType.VIDEO,
        name="旧本地源",
        uri=str(outside_file),
    )

    with pytest.raises(MediaError, match="允许目录"):
        get_source_download_info(source.pk)


@pytest.mark.django_db
def test_uploaded_file_remains_downloadable_with_external_allowed_root(
    tmp_path: Path,
    settings: Any,
) -> None:
    """
    配置外部本地根时仍应允许下载项目上传目录中的文件。

    :param tmp_path: 外部允许根目录
    :param settings: pytest-django 设置对象
    :return: None
    """
    external_root = tmp_path / "external"
    external_root.mkdir()
    settings.LOCAL_MEDIA_ALLOWED_ROOTS = [external_root]
    source = add_uploaded_file(SimpleUploadedFile("uploaded.mp4", b"video"))

    file_path, file_name, _mime_type = get_source_download_info(source.pk)

    assert Path(file_path).is_relative_to(Path(settings.MEDIA_ROOT).resolve())
    assert file_name == "uploaded.mp4"


@pytest.mark.django_db
def test_preview_revalidates_legacy_local_path(
    tmp_path: Path,
    settings: Any,
) -> None:
    """
    预览升级前已登记的本地源时仍需重新校验允许根。

    :param tmp_path: 临时文件目录
    :param settings: pytest-django 设置对象
    :return: None
    """
    allowed_root = tmp_path / "allowed"
    allowed_root.mkdir()
    outside_file = tmp_path / "legacy-private.png"
    outside_file.write_bytes(b"private")
    settings.LOCAL_MEDIA_ALLOWED_ROOTS = [allowed_root]
    source = MediaSource.objects.create(
        source_type=SourceType.IMAGE,
        name="旧本地图片",
        uri=str(outside_file),
    )

    with pytest.raises(MediaError, match="无法生成预览"):
        get_source_preview_file_info(source.pk)
