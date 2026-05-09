#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
媒体源预览服务：为 PPT、图片和视频提供统一预览信息。
@Project : SCP-cv
@File : media_previews.py
@Author : Qintsg
@Date : 2026-05-09
'''
from __future__ import annotations

import os
from pathlib import Path

from scp_cv.apps.playback.models import MediaSource, SourceType
from scp_cv.services import ppt_resources as _ppt_resources
from scp_cv.services.media_types import MediaError, guess_mime_type


def source_preview_payload(source: MediaSource) -> dict[str, str]:
    """
    构建媒体源预览字段。
    :param source: 媒体源模型实例
    :return: preview_url / thumbnail_url / preview_kind / preview_label 字段
    """
    preview_url = ""
    preview_kind = "icon"
    preview_label = "无预览"

    if source.source_type == SourceType.PPT:
        preview_url = first_ppt_slide_preview_url(source)
        preview_kind = "image" if preview_url else "icon"
        preview_label = "PPT 第一页缩略图" if preview_url else "PPT 暂无缩略图"
    elif source.source_type == SourceType.IMAGE and _source_file_is_readable(source):
        preview_url = f"/api/sources/{source.pk}/preview/"
        preview_kind = "image"
        preview_label = "图片缩略图"
    elif source.source_type == SourceType.VIDEO and _source_file_is_readable(source):
        preview_url = f"/api/sources/{source.pk}/preview/"
        preview_kind = "video"
        preview_label = "视频封面"

    return {
        "preview_url": preview_url,
        "thumbnail_url": preview_url,
        "preview_kind": preview_kind,
        "preview_label": preview_label,
    }


def first_ppt_slide_preview_url(source: MediaSource) -> str:
    """
    获取 PPT 第一页预览图 URL，必要时补齐旧源资源。
    :param source: PPT 媒体源
    :return: 第一页 slide_image；缺失时返回空字符串
    """
    if source.source_type != SourceType.PPT:
        return ""
    resources = list(source.ppt_resources.all())
    if not resources:
        _ppt_resources.prepare_ppt_source_resources(source)
        # 若调用方用了 prefetch，补齐资源后需要清掉旧缓存再读取第一页。
        getattr(source, "_prefetched_objects_cache", {}).pop("ppt_resources", None)
        resources = list(source.ppt_resources.all())
    first_resource = next((resource for resource in resources if resource.page_index == 1), None)
    return first_resource.slide_image if first_resource and first_resource.slide_image else ""


def get_source_preview_file_info(source_id: int) -> tuple[str, str]:
    """
    获取图片/视频预览文件信息。
    :param source_id: 媒体源 ID
    :return: (文件路径, MIME 类型)
    :raises MediaError: 源不存在、不支持预览或文件不可读时
    """
    try:
        source = MediaSource.objects.get(pk=source_id)
    except MediaSource.DoesNotExist as not_found:
        raise MediaError(f"媒体源 id={source_id} 不存在") from not_found
    if source.source_type not in {SourceType.IMAGE, SourceType.VIDEO}:
        raise MediaError("仅图片和视频源支持文件预览")
    if not _source_file_is_readable(source):
        raise MediaError("源文件不存在，无法生成预览")
    return source.uri, source.mime_type or guess_mime_type(source.uri)


def _source_file_is_readable(source: MediaSource) -> bool:
    """
    判断源文件是否可作为浏览器预览资源读取。
    :param source: 媒体源
    :return: 文件路径存在且可读时返回 True
    """
    source_path = Path(source.uri) if source.uri and source.is_available else None
    return bool(source_path and source_path.is_file() and os.access(source_path, os.R_OK))
