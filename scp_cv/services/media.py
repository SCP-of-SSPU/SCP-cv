#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
媒体源管理服务，负责文件上传、本地路径注册、源列表查询。
支持通过 Web 上传和直接指定本地路径两种方式添加媒体源。
@Project : SCP-cv
@File : media.py
@Author : Qintsg
@Date : 2026-04-14
'''
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from django.core.files.uploadedfile import UploadedFile

from scp_cv.apps.playback.models import MediaSource, SourceType

logger = logging.getLogger(__name__)


# 源类型与文件扩展名映射（用于自动检测）
_EXTENSION_SOURCE_TYPE_MAP: dict[str, str] = {
    # PPT
    ".pptx": SourceType.PPT,
    ".ppt": SourceType.PPT,
    ".ppsx": SourceType.PPT,
    ".pps": SourceType.PPT,
    # 视频
    ".mp4": SourceType.VIDEO,
    ".mkv": SourceType.VIDEO,
    ".avi": SourceType.VIDEO,
    ".mov": SourceType.VIDEO,
    ".wmv": SourceType.VIDEO,
    ".flv": SourceType.VIDEO,
    ".webm": SourceType.VIDEO,
    ".m4v": SourceType.VIDEO,
    # 音频
    ".mp3": SourceType.AUDIO,
    ".wav": SourceType.AUDIO,
    ".flac": SourceType.AUDIO,
    ".aac": SourceType.AUDIO,
    ".ogg": SourceType.AUDIO,
    ".wma": SourceType.AUDIO,
    ".m4a": SourceType.AUDIO,
    # 图片
    ".png": SourceType.IMAGE,
    ".jpg": SourceType.IMAGE,
    ".jpeg": SourceType.IMAGE,
    ".gif": SourceType.IMAGE,
    ".bmp": SourceType.IMAGE,
    ".webp": SourceType.IMAGE,
    ".svg": SourceType.IMAGE,
}


class MediaError(Exception):
    """媒体源操作过程中的业务异常。"""


def detect_source_type(file_path: str) -> str:
    """
    根据文件扩展名自动检测源类型。
    :param file_path: 文件路径或文件名
    :return: SourceType 值
    :raises MediaError: 无法识别扩展名时
    """
    extension = Path(file_path).suffix.lower()
    detected_type = _EXTENSION_SOURCE_TYPE_MAP.get(extension)
    if detected_type is None:
        raise MediaError(f"无法识别的文件类型：{extension}")
    return detected_type


def add_uploaded_file(
    uploaded_file: UploadedFile,
    display_name: Optional[str] = None,
    source_type: Optional[str] = None,
) -> MediaSource:
    """
    通过 Web 上传添加媒体源，文件保存到 media/uploads/。
    :param uploaded_file: Django UploadedFile 实例
    :param display_name: 显示名称，默认使用文件名
    :param source_type: 源类型，默认自动检测
    :return: 创建的 MediaSource 实例
    :raises MediaError: 文件类型无法识别时
    """
    file_name = uploaded_file.name or "未命名文件"
    if source_type is None:
        source_type = detect_source_type(file_name)

    if display_name is None:
        display_name = Path(file_name).stem

    media_source = MediaSource(
        source_type=source_type,
        name=display_name,
        uri="",  # 上传完成后填入实际路径
    )
    # 先保存文件到 FileField
    media_source.uploaded_file.save(file_name, uploaded_file, save=False)
    # 设置 uri 为上传后的实际文件路径
    media_source.uri = media_source.uploaded_file.path
    media_source.save()

    logger.info("通过上传添加媒体源「%s」（%s）→ %s", display_name, source_type, media_source.uri)
    return media_source


def add_local_path(
    local_path: str,
    display_name: Optional[str] = None,
    source_type: Optional[str] = None,
) -> MediaSource:
    """
    通过本地路径注册媒体源。
    :param local_path: 本地文件绝对路径
    :param display_name: 显示名称，默认使用文件名
    :param source_type: 源类型，默认自动检测
    :return: 创建的 MediaSource 实例
    :raises MediaError: 文件不存在或类型无法识别时
    """
    resolved_path = Path(local_path).resolve()

    if not resolved_path.is_file():
        raise MediaError(f"文件不存在：{resolved_path}")

    if source_type is None:
        source_type = detect_source_type(str(resolved_path))

    if display_name is None:
        display_name = resolved_path.stem

    media_source = MediaSource.objects.create(
        source_type=source_type,
        name=display_name,
        uri=str(resolved_path),
        is_available=True,
    )

    logger.info("通过本地路径添加媒体源「%s」（%s）→ %s", display_name, source_type, resolved_path)
    return media_source


def add_web_url(
    url: str,
    display_name: Optional[str] = None,
) -> MediaSource:
    """
    通过 URL 添加网页类型媒体源。
    :param url: 网页 URL（如 https://example.com）
    :param display_name: 显示名称，默认使用 URL
    :return: 创建的 MediaSource 实例
    :raises MediaError: URL 为空时
    """
    stripped_url = url.strip()
    if not stripped_url:
        raise MediaError("URL 不能为空")

    if display_name is None:
        display_name = stripped_url[:80]

    media_source = MediaSource.objects.create(
        source_type=SourceType.WEB,
        name=display_name,
        uri=stripped_url,
        is_available=True,
    )

    logger.info("通过 URL 添加网页媒体源「%s」→ %s", display_name, stripped_url)
    return media_source


def list_media_sources(source_type: Optional[str] = None) -> list[dict[str, object]]:
    """
    查询所有媒体源列表。
    :param source_type: 可选过滤源类型
    :return: 媒体源字典列表
    """
    queryset = MediaSource.objects.all()
    if source_type:
        queryset = queryset.filter(source_type=source_type)

    return list(queryset.values(
        "id", "source_type", "name", "uri", "is_available",
        "stream_identifier", "created_at",
    ))


def delete_media_source(media_source_id: int) -> None:
    """
    删除指定媒体源（已上传文件同时删除）。
    :param media_source_id: MediaSource 主键
    :raises MediaError: 源不存在时
    """
    try:
        source = MediaSource.objects.get(pk=media_source_id)
    except MediaSource.DoesNotExist as not_found:
        raise MediaError(f"媒体源 id={media_source_id} 不存在") from not_found

    # 删除关联的上传文件
    if source.uploaded_file:
        file_path = source.uploaded_file.path
        if os.path.isfile(file_path):
            os.remove(file_path)
            logger.info("删除上传文件：%s", file_path)

    source_name = source.name
    source.delete()
    logger.info("删除媒体源「%s」", source_name)


def sync_streams_to_media_sources() -> dict[str, int]:
    """
    将 StreamSource 中在线的流同步为 MediaSource 记录。
    已存在的更新可用状态，新发现的自动创建。
    :return: 同步计数 {created, updated, removed}
    """
    from scp_cv.apps.streams.models import StreamSource
    from scp_cv.services.mediamtx import get_rtsp_read_url

    counts: dict[str, int] = {"created": 0, "updated": 0, "removed": 0}
    active_identifiers: set[str] = set()

    # 同步在线流
    for stream in StreamSource.objects.filter(is_online=True):
        active_identifiers.add(stream.stream_identifier)
        existing = MediaSource.objects.filter(
            source_type=SourceType.RTSP_STREAM,
            stream_identifier=stream.stream_identifier,
        ).first()

        rtsp_url = get_rtsp_read_url(stream.stream_identifier)

        if existing is None:
            MediaSource.objects.create(
                source_type=SourceType.RTSP_STREAM,
                name=stream.name,
                uri=rtsp_url,
                stream_identifier=stream.stream_identifier,
                is_available=True,
            )
            counts["created"] += 1
        else:
            if not existing.is_available or existing.uri != rtsp_url:
                existing.is_available = True
                existing.uri = rtsp_url
                existing.name = stream.name
                existing.save()
                counts["updated"] += 1

    # 标记已离线的流为不可用
    offline_sources = MediaSource.objects.filter(
        source_type=SourceType.RTSP_STREAM,
    ).exclude(stream_identifier__in=active_identifiers)

    for offline_source in offline_sources.filter(is_available=True):
        offline_source.is_available = False
        offline_source.save()
        counts["removed"] += 1

    return counts
