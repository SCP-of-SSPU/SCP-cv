#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
媒体源管理服务，负责文件上传、本地路径注册、源列表查询。
支持通过 Web 上传和直接指定本地路径两种方式添加媒体源。
@Project : SCP-cv
@File : media.py
@Author : Qintsg
@Date : 2026-04-29
'''
from __future__ import annotations

import logging
import os
from datetime import timedelta
from pathlib import Path
from typing import Optional

from django.core.files.uploadedfile import UploadedFile
from django.utils import timezone

from scp_cv.apps.playback.models import (
    MediaFolder,
    MediaSource,
    SourceType,
)
from scp_cv.services import ppt_resources as _ppt_resources
from scp_cv.services.media_folders import (
    create_folder as create_folder,
    delete_folder as delete_folder,
    list_folders as list_folders,
    update_folder as update_folder,
)
from scp_cv.services.media_types import (
    MediaError,
    detect_source_type,
    guess_mime_type as _guess_mime_type,
)

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════
# 媒体源 CRUD
# ════════════════════════════════════════════════════════════════


def add_uploaded_file(
    uploaded_file: UploadedFile,
    display_name: Optional[str] = None,
    source_type: Optional[str] = None,
    folder_id: Optional[int] = None,
    is_temporary: bool = False,
) -> MediaSource:
    """
    通过 Web 上传添加媒体源，文件保存到 media/uploads/。
    :param uploaded_file: Django UploadedFile 实例
    :param display_name: 显示名称，默认使用文件名
    :param source_type: 源类型，默认自动检测
    :param folder_id: 所属文件夹 ID
    :param is_temporary: 是否为临时源
    :return: 创建的 MediaSource 实例
    :raises MediaError: 文件类型无法识别时
    """
    file_name = uploaded_file.name or "未命名文件"
    if source_type is None:
        source_type = detect_source_type(file_name)

    if display_name is None:
        display_name = Path(file_name).stem

    folder = None
    if folder_id:
        try:
            folder = MediaFolder.objects.get(pk=folder_id)
        except MediaFolder.DoesNotExist:
            folder = None

    media_source = MediaSource(
        source_type=source_type,
        name=display_name,
        uri="",
        original_filename=file_name,
        file_size=uploaded_file.size or 0,
        mime_type=_guess_mime_type(file_name),
        folder=folder,
        is_temporary=is_temporary,
        expires_at=timezone.now() + timedelta(days=1) if is_temporary else None,
    )
    media_source.uploaded_file.save(file_name, uploaded_file, save=False)
    media_source.uri = media_source.uploaded_file.path
    media_source.save()
    _prepare_ppt_source_resources(media_source)

    logger.info("通过上传添加媒体源「%s」（%s）→ %s", display_name, source_type, media_source.uri)
    return media_source


def add_local_path(
    local_path: str,
    display_name: Optional[str] = None,
    source_type: Optional[str] = None,
    folder_id: Optional[int] = None,
) -> MediaSource:
    """
    通过本地路径注册媒体源。
    :param local_path: 本地文件绝对路径
    :param display_name: 显示名称，默认使用文件名
    :param source_type: 源类型，默认自动检测
    :param folder_id: 所属文件夹 ID
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

    folder = None
    if folder_id:
        try:
            folder = MediaFolder.objects.get(pk=folder_id)
        except MediaFolder.DoesNotExist:
            folder = None

    media_source = MediaSource.objects.create(
        source_type=source_type,
        name=display_name,
        uri=str(resolved_path),
        is_available=True,
        original_filename=resolved_path.name,
        file_size=resolved_path.stat().st_size,
        mime_type=_guess_mime_type(resolved_path.name),
        folder=folder,
    )
    _prepare_ppt_source_resources(media_source)

    logger.info("通过本地路径添加媒体源「%s」（%s）→ %s", display_name, source_type, resolved_path)
    return media_source


def add_web_url(
    url: str,
    display_name: Optional[str] = None,
    folder_id: Optional[int] = None,
) -> MediaSource:
    """
    通过 URL 添加网页类型媒体源。
    :param url: 网页 URL（如 https://example.com）
    :param display_name: 显示名称，默认使用 URL
    :param folder_id: 所属文件夹 ID
    :return: 创建的 MediaSource 实例
    :raises MediaError: URL 为空时
    """
    normalized_url = normalize_web_url(url)
    if not normalized_url:
        raise MediaError("URL 不能为空")

    if display_name is None:
        display_name = normalized_url[:80]

    folder = None
    if folder_id:
        try:
            folder = MediaFolder.objects.get(pk=folder_id)
        except MediaFolder.DoesNotExist:
            folder = None

    media_source = MediaSource.objects.create(
        source_type=SourceType.WEB,
        name=display_name,
        uri=normalized_url,
        is_available=True,
        mime_type="text/html",
        folder=folder,
    )

    logger.info("通过 URL 添加网页媒体源「%s」→ %s", display_name, normalized_url)
    return media_source


def normalize_web_url(url: str) -> str:
    """
    规范化网页源 URL，未写协议时默认使用 http 以兼容局域网设备。
    :param url: 用户输入的网页地址
    :return: 可交给 QWebEngineView 加载的 URL，空输入返回空字符串
    """
    stripped_url = url.strip()
    if not stripped_url:
        return ""
    lower_url = stripped_url.lower()
    if lower_url.startswith(("http://", "https://", "file://", "about:")):
        return stripped_url
    if len(stripped_url) > 2 and stripped_url[1] == ":":
        return f"file:///{stripped_url}"
    return f"http://{stripped_url}"


def move_source(source_id: int, folder_id: Optional[int] = None) -> MediaSource:
    """
    移动媒体源到指定文件夹。
    :param source_id: 媒体源 ID
    :param folder_id: 目标文件夹 ID（None 表示移到根目录）
    :return: 更新后的媒体源
    :raises MediaError: 源或文件夹不存在时
    """
    try:
        source = MediaSource.objects.get(pk=source_id)
    except MediaSource.DoesNotExist as not_found:
        raise MediaError(f"媒体源 id={source_id} 不存在") from not_found

    folder = None
    if folder_id:
        try:
            folder = MediaFolder.objects.get(pk=folder_id)
        except MediaFolder.DoesNotExist as not_found:
            raise MediaError(f"文件夹 id={folder_id} 不存在") from not_found

    source.folder = folder
    source.save(update_fields=["folder"])
    logger.info("移动媒体源「%s」到文件夹 %s", source.name, folder.name if folder else "根目录")
    return source


def get_source_download_info(source_id: int) -> tuple[str, str, str]:
    """
    获取媒体源的下载文件信息。
    :param source_id: 媒体源 ID
    :return: (文件路径, 文件名, MIME 类型)
    :raises MediaError: 源不存在或不可下载时
    """
    try:
        source = MediaSource.objects.get(pk=source_id)
    except MediaSource.DoesNotExist as not_found:
        raise MediaError(f"媒体源 id={source_id} 不存在") from not_found

    file_path = source.uri
    if not file_path or not os.path.isfile(file_path):
        raise MediaError("源文件不存在，无法下载")

    file_name = source.original_filename or os.path.basename(file_path)
    mime_type = source.mime_type or _guess_mime_type(file_name)
    return file_path, file_name, mime_type


def list_media_sources(
    source_type: Optional[str] = None,
    folder_id: Optional[int] = None,
) -> list[dict[str, object]]:
    """
    查询所有媒体源列表。
    :param source_type: 可选过滤源类型
    :param folder_id: 可选过滤文件夹 ID（-1 表示根目录）
    :return: 媒体源字典列表
    """
    queryset = MediaSource.objects.all()
    if source_type:
        queryset = queryset.filter(source_type=source_type)
    if folder_id is not None:
        if folder_id < 0:
            queryset = queryset.filter(folder__isnull=True)
        else:
            queryset = queryset.filter(folder_id=folder_id)

    return list(queryset.values(
        "id", "source_type", "name", "uri", "is_available",
        "stream_identifier", "created_at", "folder_id",
        "original_filename", "file_size", "mime_type",
        "is_temporary", "expires_at", "metadata",
    ))


def delete_media_source(media_source_id: int) -> None:
    """
    删除指定媒体源（已上传文件同时删除，关联 PPT 资源一并删除）。
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

    # 删除 PPT 解析资源文件
    for resource in source.ppt_resources.all():
        for image_reference in [resource.slide_image, resource.next_slide_image]:
            image_path = _resolve_ppt_image_path(image_reference)
            if image_path is not None and image_path.is_file():
                image_path.unlink()
                logger.info("删除 PPT 资源文件：%s", image_path)

    source_name = source.name
    source.delete()
    logger.info("删除媒体源「%s」", source_name)


def delete_temporary_source_if_unused(media_source_id: Optional[int]) -> bool:
    """
    删除已切离的临时源。
    :param media_source_id: 媒体源 ID；为空时不处理
    :return: 是否删除了临时源
    """
    if not media_source_id:
        return False
    source = MediaSource.objects.filter(pk=media_source_id, is_temporary=True).first()
    if source is None:
        return False
    delete_media_source(source.pk)
    return True


def _prepare_ppt_source_resources(source: MediaSource) -> None:
    """
    为 PPT 自动建立页资源、媒体清单和可用时的 PNG 预览。
    :param source: 已保存的 PPT 媒体源
    :return: None
    """
    _ppt_resources.prepare_ppt_source_resources(source, preview_exporter=_export_ppt_slide_previews)


def _export_ppt_slide_previews(file_path: Path, source_id: int) -> list[str]:
    """
    兼容旧测试 patch 路径的 PPT 预览导出入口。
    :param file_path: PPT 文件路径
    :param source_id: 媒体源 ID
    :return: 按页码排序的媒体 URL 列表
    """
    return _ppt_resources.export_ppt_slide_previews(file_path, source_id)


def _resolve_ppt_image_path(image_reference: str) -> Optional[Path]:
    """
    将 PPT 预览引用转换为本地文件路径。
    :param image_reference: 数据库存储的图片 URL、相对路径或绝对路径
    :return: 可检查的本地路径；空引用返回 None
    """
    return _ppt_resources.resolve_ppt_image_path(image_reference)


def list_ppt_resources(source_id: int) -> list[dict[str, object]]:
    """
    获取 PPT 源的解析资源列表。
    :param source_id: PPT 媒体源 ID
    :return: PPT 页资源字典列表
    :raises MediaError: 源不存在或不是 PPT 时
    """
    return _ppt_resources.list_ppt_resources(source_id, prepare_resources=_prepare_ppt_source_resources)


def replace_ppt_resources(source_id: int, resources: list[dict[str, object]]) -> list[dict[str, object]]:
    """
    覆盖保存 PPT 解析资源。
    :param source_id: PPT 媒体源 ID
    :param resources: PPT 页资源配置列表
    :return: 保存后的资源列表
    :raises MediaError: 源不存在、类型错误或页码无效时
    """
    return _ppt_resources.replace_ppt_resources(source_id, resources)


def cleanup_expired_temporary_sources() -> int:
    """
    清理过期的临时源。
    :return: 删除的源数量
    """
    now = timezone.now()
    expired = MediaSource.objects.filter(
        is_temporary=True,
        expires_at__lte=now,
    )
    count = 0
    for source in expired:
        try:
            delete_media_source(source.pk)
            count += 1
        except MediaError as e:
            logger.warning("清理临时源失败：%s", e)
    if count:
        logger.info("清理过期临时源 %d 个", count)
    return count


def sync_streams_to_media_sources() -> dict[str, int]:
    """
    将 StreamSource 中在线的流同步为 MediaSource 记录。
    已存在的更新可用状态，新发现的自动创建。
    同时删除离线超过 1 小时的直播源。
    :return: 同步计数 {created, updated, removed}
    """
    from scp_cv.apps.streams.models import StreamSource
    from scp_cv.services.mediamtx import get_srt_read_url

    counts: dict[str, int] = {"created": 0, "updated": 0, "removed": 0}
    active_identifiers: set[str] = set()

    # 同步在线流
    for stream in StreamSource.objects.filter(is_online=True):
        active_identifiers.add(stream.stream_identifier)
        existing = MediaSource.objects.filter(
            source_type=SourceType.SRT_STREAM,
            stream_identifier=stream.stream_identifier,
        ).first()

        # 向后兼容：同时查找旧的 RTSP_STREAM 类型记录
        if existing is None:
            existing = MediaSource.objects.filter(
                source_type=SourceType.RTSP_STREAM,
                stream_identifier=stream.stream_identifier,
            ).first()

        srt_url = get_srt_read_url(stream.stream_identifier)

        if existing is None:
            MediaSource.objects.create(
                source_type=SourceType.SRT_STREAM,
                name=stream.name,
                uri=srt_url,
                stream_identifier=stream.stream_identifier,
                is_available=True,
            )
            counts["created"] += 1
        else:
            if not existing.is_available or existing.uri != srt_url:
                existing.is_available = True
                existing.uri = srt_url
                existing.name = stream.name
                existing.source_type = SourceType.SRT_STREAM
                existing.save()
                counts["updated"] += 1

    # 标记已离线的流为不可用
    offline_sources = MediaSource.objects.filter(
        source_type__in=[SourceType.SRT_STREAM, SourceType.RTSP_STREAM],
    ).exclude(stream_identifier__in=active_identifiers)

    for offline_source in offline_sources.filter(is_available=True):
        offline_source.is_available = False
        offline_source.save(update_fields=["is_available"])
        counts["removed"] += 1

    # 删除离线超过 1 小时的直播源
    one_hour_ago = timezone.now() - timedelta(hours=1)
    stale_identifiers = set(
        StreamSource.objects.filter(
            is_online=False,
            last_seen_at__lte=one_hour_ago,
        ).values_list("stream_identifier", flat=True)
    )
    if stale_identifiers:
        stale_sources = MediaSource.objects.filter(
            source_type__in=[SourceType.SRT_STREAM, SourceType.RTSP_STREAM],
            stream_identifier__in=stale_identifiers,
        )
        stale_count = stale_sources.count()
        stale_sources.delete()
        if stale_count:
            counts["removed"] += stale_count
            logger.info("清理离线超过 1 小时的直播源 %d 个", stale_count)

    return counts
