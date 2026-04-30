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
import mimetypes
import os
import re
import zipfile
from datetime import timedelta
from pathlib import Path
from typing import Optional
from xml.etree import ElementTree

from django.core.files.uploadedfile import UploadedFile
from django.utils import timezone

from scp_cv.apps.playback.models import (
    MediaFolder,
    MediaSource,
    PptResource,
    SourceType,
)

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


def _guess_mime_type(file_name: str) -> str:
    """根据文件名猜测 MIME 类型。"""
    mime_type, _ = mimetypes.guess_type(file_name)
    return mime_type or "application/octet-stream"


# ════════════════════════════════════════════════════════════════
# 文件夹管理
# ════════════════════════════════════════════════════════════════


def list_folders() -> list[dict[str, object]]:
    """
    获取所有文件夹列表。
    :return: 文件夹字典列表
    """
    return list(MediaFolder.objects.values(
        "id", "name", "parent_id", "created_at", "updated_at",
    ))


def create_folder(name: str, parent_id: Optional[int] = None) -> MediaFolder:
    """
    创建文件夹。
    :param name: 文件夹名称
    :param parent_id: 父文件夹 ID（可选）
    :return: 创建的 MediaFolder 实例
    :raises MediaError: 名称为空或父文件夹不存在时
    """
    if not name.strip():
        raise MediaError("文件夹名称不能为空")
    parent = None
    if parent_id:
        try:
            parent = MediaFolder.objects.get(pk=parent_id)
        except MediaFolder.DoesNotExist as not_found:
            raise MediaError(f"父文件夹 id={parent_id} 不存在") from not_found
    folder = MediaFolder.objects.create(name=name.strip(), parent=parent)
    logger.info("创建文件夹「%s」(id=%d)", folder.name, folder.pk)
    return folder


def update_folder(folder_id: int, name: Optional[str] = None, parent_id: Optional[int] = None) -> MediaFolder:
    """
    更新文件夹。
    :param folder_id: 文件夹 ID
    :param name: 新名称
    :param parent_id: 新父文件夹 ID
    :return: 更新后的文件夹
    :raises MediaError: 文件夹不存在时
    """
    try:
        folder = MediaFolder.objects.get(pk=folder_id)
    except MediaFolder.DoesNotExist as not_found:
        raise MediaError(f"文件夹 id={folder_id} 不存在") from not_found
    if name is not None:
        if not name.strip():
            raise MediaError("文件夹名称不能为空")
        folder.name = name.strip()
    if parent_id is not None:
        if parent_id == folder_id:
            raise MediaError("不能将文件夹设为自己的子文件夹")
        folder.parent_id = parent_id if parent_id > 0 else None
    folder.save()
    logger.info("更新文件夹「%s」(id=%d)", folder.name, folder.pk)
    return folder


def delete_folder(folder_id: int) -> None:
    """
    删除文件夹，其中的源自动归到根目录。
    :param folder_id: 文件夹 ID
    :raises MediaError: 文件夹不存在时
    """
    try:
        folder = MediaFolder.objects.get(pk=folder_id)
    except MediaFolder.DoesNotExist as not_found:
        raise MediaError(f"文件夹 id={folder_id} 不存在") from not_found
    # 删除文件夹前先收集完整子树，避免级联删除导致源记录失去归档入口。
    descendant_ids = _collect_folder_tree_ids(folder)
    MediaSource.objects.filter(folder_id__in=descendant_ids).update(folder=None)
    folder_name = folder.name
    folder.delete()
    logger.info("删除文件夹「%s」", folder_name)


def _collect_folder_tree_ids(folder: MediaFolder) -> list[int]:
    """递归收集文件夹及其所有子文件夹 ID。"""
    folder_ids = [folder.pk]
    for child in folder.children.all():
        folder_ids.extend(_collect_folder_tree_ids(child))
    return folder_ids


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
        for image_path in [resource.slide_image, resource.next_slide_image]:
            if image_path and os.path.isfile(image_path):
                os.remove(image_path)
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
    为 zip 格式 PPT 自动建立页资源和媒体清单，失败时保留源本身可打开。
    :param source: 已保存的 PPT 媒体源
    :return: None
    """
    if source.source_type != SourceType.PPT:
        return
    metadata = dict(source.metadata or {})
    try:
        resources = _extract_pptx_resources(Path(source.uri))
    except MediaError as parse_error:
        metadata.update({"ppt_parse_status": "unsupported", "ppt_parse_error": str(parse_error)})
        source.metadata = metadata
        source.save(update_fields=["metadata"])
        logger.info("PPT 资源解析跳过：source_id=%d, reason=%s", source.pk, parse_error)
        return

    replace_ppt_resources(source.pk, resources)
    metadata.update({
        "ppt_parse_status": "parsed",
        "total_slides": len(resources),
        "has_media": any(bool(item.get("media_items")) for item in resources),
    })
    source.metadata = metadata
    source.save(update_fields=["metadata"])
    logger.info("PPT 资源解析完成：source_id=%d, pages=%d", source.pk, len(resources))


def _extract_pptx_resources(file_path: Path) -> list[dict[str, object]]:
    """
    从 pptx/ppsx zip 包解析页数、备注文本和媒体引用清单。
    :param file_path: PPT 文件路径
    :return: PPT 页资源列表
    :raises MediaError: 文件不是可解析的 zip PPT 时
    """
    if file_path.suffix.lower() not in {".pptx", ".ppsx"}:
        raise MediaError("仅 pptx/ppsx 支持自动解析资源")
    try:
        with zipfile.ZipFile(file_path) as archive:
            slide_names = sorted(
                (name for name in archive.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)),
                key=lambda name: int(re.search(r"slide(\d+)\.xml", name).group(1)),
            )
            return [
                {
                    "page_index": page_index,
                    "speaker_notes": _extract_notes_text(archive, page_index),
                    "media_items": _extract_slide_media_items(archive, slide_name, page_index),
                }
                for page_index, slide_name in enumerate(slide_names, start=1)
            ]
    except (zipfile.BadZipFile, OSError, ElementTree.ParseError) as parse_error:
        raise MediaError(f"PPT 资源解析失败：{parse_error}") from parse_error


def _extract_slide_media_items(
    archive: zipfile.ZipFile,
    slide_name: str,
    page_index: int,
) -> list[dict[str, object]]:
    """
    解析单页 PPT 的音视频关系项。
    :param archive: PPT zip 包
    :param slide_name: slide XML 路径
    :param page_index: 页码
    :return: 媒体对象列表
    """
    relationship_name = f"ppt/slides/_rels/{Path(slide_name).name}.rels"
    if relationship_name not in archive.namelist():
        return []
    root = ElementTree.fromstring(archive.read(relationship_name))
    media_items: list[dict[str, object]] = []
    for relationship in root:
        target = str(relationship.attrib.get("Target", ""))
        relationship_type = str(relationship.attrib.get("Type", "")).lower()
        if not _is_ppt_media_relationship(target, relationship_type):
            continue
        media_index = len(media_items) + 1
        media_name = Path(target).name or f"media-{media_index}"
        media_items.append({
            "id": f"page-{page_index}-media-{media_index}",
            "media_index": media_index,
            "media_type": _guess_ppt_media_type(media_name, relationship_type),
            "name": media_name,
            "target": target,
            "shape_id": 0,
        })
    return media_items


def _extract_notes_text(archive: zipfile.ZipFile, page_index: int) -> str:
    """
    从 notesSlide XML 提取纯文本备注。
    :param archive: PPT zip 包
    :param page_index: 页码
    :return: 备注文本；不存在时返回空字符串
    """
    notes_name = f"ppt/notesSlides/notesSlide{page_index}.xml"
    if notes_name not in archive.namelist():
        return ""
    root = ElementTree.fromstring(archive.read(notes_name))
    texts = [node.text.strip() for node in root.iter() if node.tag.endswith("}t") and node.text and node.text.strip()]
    return "\n".join(texts)


def _is_ppt_media_relationship(target: str, relationship_type: str) -> bool:
    """判断 PPT 关系是否指向音视频媒体文件。"""
    lower_target = target.lower()
    media_extensions = {".mp4", ".mov", ".wmv", ".avi", ".mp3", ".wav", ".wma", ".m4a"}
    return (
        "/media" in relationship_type
        or "../media/" in lower_target
        or Path(lower_target).suffix in media_extensions
    )


def _guess_ppt_media_type(media_name: str, relationship_type: str) -> str:
    """根据关系类型和扩展名推断 PPT 媒体类型。"""
    lower_name = media_name.lower()
    if "audio" in relationship_type or Path(lower_name).suffix in {".mp3", ".wav", ".wma", ".m4a"}:
        return "audio"
    return "video"


def list_ppt_resources(source_id: int) -> list[dict[str, object]]:
    """
    获取 PPT 源的解析资源列表。
    :param source_id: PPT 媒体源 ID
    :return: PPT 页资源字典列表
    :raises MediaError: 源不存在或不是 PPT 时
    """
    source = _get_ppt_source(source_id)
    return [_ppt_resource_payload(resource) for resource in source.ppt_resources.all()]


def replace_ppt_resources(source_id: int, resources: list[dict[str, object]]) -> list[dict[str, object]]:
    """
    覆盖保存 PPT 解析资源。
    :param source_id: PPT 媒体源 ID
    :param resources: 资源列表，包含 page_index、slide_image、next_slide_image、speaker_notes、has_media
    :return: 保存后的资源列表
    :raises MediaError: 源不存在、类型错误或页码无效时
    """
    source = _get_ppt_source(source_id)
    source.ppt_resources.all().delete()
    for resource_data in resources:
        try:
            page_index = int(resource_data.get("page_index", 0))
        except (TypeError, ValueError) as parse_error:
            raise MediaError("PPT 页码必须是整数") from parse_error
        if page_index <= 0:
            raise MediaError("PPT 页码必须大于 0")
        media_items = _normalize_ppt_media_items(resource_data.get("media_items", []))
        PptResource.objects.create(
            source=source,
            page_index=page_index,
            slide_image=str(resource_data.get("slide_image", "")),
            next_slide_image=str(resource_data.get("next_slide_image", "")),
            speaker_notes=str(resource_data.get("speaker_notes", "")),
            has_media=bool(resource_data.get("has_media", False)) or bool(media_items),
            media_items=media_items,
        )
    logger.info("保存 PPT 资源：source_id=%d, pages=%d", source_id, len(resources))
    return list_ppt_resources(source_id)


def _get_ppt_source(source_id: int) -> MediaSource:
    """查询并校验 PPT 媒体源。"""
    try:
        source = MediaSource.objects.get(pk=source_id)
    except MediaSource.DoesNotExist as not_found:
        raise MediaError(f"媒体源 id={source_id} 不存在") from not_found
    if source.source_type != SourceType.PPT:
        raise MediaError("仅 PPT 源支持解析资源")
    return source


def _ppt_resource_payload(resource: PptResource) -> dict[str, object]:
    """序列化 PPT 页资源。"""
    return {
        "id": resource.pk,
        "source_id": resource.source_id,
        "page_index": resource.page_index,
        "slide_image": resource.slide_image,
        "next_slide_image": resource.next_slide_image,
        "speaker_notes": resource.speaker_notes,
        "has_media": resource.has_media,
        "media_items": resource.media_items or [],
        "created_at": resource.created_at.isoformat() if resource.created_at else "",
    }


def _normalize_ppt_media_items(raw_media_items: object) -> list[dict[str, object]]:
    """
    校验并规范化前端保存的 PPT 页面媒体清单。
    :param raw_media_items: 用户提交的媒体清单
    :return: 规范化后的媒体对象列表
    :raises MediaError: 媒体清单格式错误时
    """
    if raw_media_items in (None, ""):
        return []
    if not isinstance(raw_media_items, list):
        raise MediaError("media_items 必须是数组")
    normalized_items: list[dict[str, object]] = []
    for item_index, raw_item in enumerate(raw_media_items, start=1):
        if not isinstance(raw_item, dict):
            raise MediaError("media_items 中的元素必须是对象")
        media_index = _positive_int(raw_item.get("media_index"), item_index)
        shape_id = _positive_int(raw_item.get("shape_id"), 0)
        normalized_items.append({
            "id": str(raw_item.get("id") or f"media-{media_index}"),
            "media_index": media_index,
            "media_type": str(raw_item.get("media_type") or raw_item.get("type") or "unknown"),
            "name": str(raw_item.get("name") or f"媒体 {media_index}"),
            "target": str(raw_item.get("target") or ""),
            "shape_id": shape_id,
        })
    return normalized_items


def _positive_int(raw_value: object, default: int) -> int:
    """将输入转换为非负整数，失败时使用默认值。"""
    try:
        return max(0, int(raw_value))
    except (TypeError, ValueError):
        return default


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
