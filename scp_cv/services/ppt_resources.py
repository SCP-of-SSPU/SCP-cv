#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PPT 媒体源资源解析服务，负责页资源、备注、嵌入媒体和预览图维护。
@Project : SCP-cv
@File : ppt_resources.py
@Author : Qintsg
@Date : 2026-05-02
'''
from __future__ import annotations

import logging
import os
import re
import zipfile
from pathlib import Path
from typing import Callable, Optional
from xml.etree import ElementTree

from django.conf import settings

from scp_cv.apps.playback.models import MediaSource, PptResource, SourceType
from scp_cv.services.media_types import MediaError

logger = logging.getLogger(__name__)

_PPT_ALERTS_NONE = 1
PreviewExporter = Callable[[Path, int], list[str]]
ResourcePreparer = Callable[[MediaSource], None]


def prepare_ppt_source_resources(
    source: MediaSource,
    preview_exporter: Optional[PreviewExporter] = None,
) -> None:
    """
    为 PPT 自动建立页资源、媒体清单和可用时的 PNG 预览。
    :param source: 已保存的 PPT 媒体源
    :param preview_exporter: 预览导出函数；测试可注入替身以避开本机 PowerPoint 依赖
    :return: None
    """
    if source.source_type != SourceType.PPT:
        return
    metadata = dict(source.metadata or {})
    source_path = Path(source.uri)
    exporter = preview_exporter or export_ppt_slide_previews
    try:
        resources = _extract_pptx_resources(source_path)
    except MediaError as parse_error:
        preview_paths = exporter(source_path, source.pk)
        if preview_paths:
            replace_ppt_resources(source.pk, _resources_from_preview_paths(preview_paths))
            metadata.update({
                "ppt_parse_status": "preview_only",
                "ppt_parse_error": str(parse_error),
                "total_slides": len(preview_paths),
                "preview_count": len(preview_paths),
                "has_media": False,
            })
            source.metadata = metadata
            source.save(update_fields=["metadata"])
            logger.info("PPT 预览导出完成：source_id=%d, pages=%d", source.pk, len(preview_paths))
            return
        metadata.update({"ppt_parse_status": "unsupported", "ppt_parse_error": str(parse_error)})
        source.metadata = metadata
        source.save(update_fields=["metadata"])
        logger.info("PPT 资源解析跳过：source_id=%d, reason=%s", source.pk, parse_error)
        return

    preview_paths = exporter(source_path, source.pk)
    _apply_preview_paths(resources, preview_paths)
    replace_ppt_resources(source.pk, resources)
    metadata.update({
        "ppt_parse_status": "parsed",
        "total_slides": len(resources),
        "preview_count": len(preview_paths),
        "has_media": any(bool(item.get("media_items")) for item in resources),
    })
    source.metadata = metadata
    source.save(update_fields=["metadata"])
    logger.info("PPT 资源解析完成：source_id=%d, pages=%d", source.pk, len(resources))


def resolve_ppt_image_path(image_reference: str) -> Optional[Path]:
    """
    将 PPT 预览引用转换为本地文件路径，供删除媒体源时清理文件。
    :param image_reference: 数据库存储的图片 URL、相对路径或绝对路径
    :return: 可检查的本地路径；空引用返回 None
    """
    if not image_reference:
        return None
    media_url = settings.MEDIA_URL.rstrip("/") + "/"
    if image_reference.startswith(media_url):
        relative_path = image_reference[len(media_url):]
        return Path(settings.MEDIA_ROOT) / relative_path
    image_path = Path(image_reference)
    if image_path.is_absolute():
        return image_path
    return Path(settings.MEDIA_ROOT) / image_reference.lstrip("/\\")


def export_ppt_slide_previews(file_path: Path, source_id: int) -> list[str]:
    """
    使用本机 PowerPoint 将每页幻灯片导出为 PNG 预览。
    :param file_path: PPT 文件路径
    :param source_id: 媒体源 ID，用于隔离导出目录
    :return: 按页码排序的媒体 URL 列表；不可导出时返回空列表
    """
    if os.name != "nt" or not file_path.is_file() or not _is_powerpoint_export_candidate(file_path):
        return []
    try:
        import pythoncom
        import win32com.client
    except ImportError as import_error:
        logger.info("PPT 预览导出跳过，缺少 COM 依赖：%s", import_error)
        return []

    relative_dir = Path("ppt_previews") / str(source_id)
    preview_dir = Path(settings.MEDIA_ROOT) / relative_dir
    preview_dir.mkdir(parents=True, exist_ok=True)
    for old_preview in preview_dir.glob("*.png"):
        old_preview.unlink(missing_ok=True)

    pythoncom.CoInitialize()
    ppt_app: Optional[object] = None
    presentation: Optional[object] = None
    try:
        ppt_app = win32com.client.DispatchEx("PowerPoint.Application")
        ppt_app.DisplayAlerts = _PPT_ALERTS_NONE
        presentation = ppt_app.Presentations.Open(
            str(file_path),
            ReadOnly=True,
            Untitled=False,
            WithWindow=False,
        )
        preview_paths: list[str] = []
        slide_count = int(presentation.Slides.Count)
        for page_index in range(1, slide_count + 1):
            output_path = preview_dir / f"slide-{page_index}.png"
            presentation.Slides(page_index).Export(str(output_path), "PNG")
            relative_path = (relative_dir / output_path.name).as_posix()
            preview_paths.append(f"{settings.MEDIA_URL.rstrip('/')}/{relative_path}")
        return preview_paths
    except Exception as export_error:
        logger.info("PPT 预览导出失败：%s", export_error)
        return []
    finally:
        if presentation is not None:
            try:
                presentation.Saved = True
                presentation.Close()
            except Exception:
                pass
        if ppt_app is not None:
            try:
                ppt_app.Quit()
            except Exception:
                pass
        try:
            pythoncom.CoUninitialize()
        except Exception:
            pass


def list_ppt_resources(
    source_id: int,
    prepare_resources: Optional[ResourcePreparer] = None,
) -> list[dict[str, object]]:
    """
    获取 PPT 源的解析资源列表。
    :param source_id: PPT 媒体源 ID
    :param prepare_resources: 旧数据缺资源时的补齐函数；测试可注入替身
    :return: PPT 页资源字典列表
    :raises MediaError: 源不存在或不是 PPT 时
    """
    source = _get_ppt_source(source_id)
    if not source.ppt_resources.exists():
        preparer = prepare_resources or prepare_ppt_source_resources
        preparer(source)
        source.refresh_from_db(fields=["metadata"])
    return [_ppt_resource_payload(resource) for resource in source.ppt_resources.all()]


def replace_ppt_resources(source_id: int, resources: list[dict[str, object]]) -> list[dict[str, object]]:
    """
    覆盖保存 PPT 解析资源。
    :param source_id: PPT 媒体源 ID
    :param resources: 资源列表，包含 page_index、slide_image、speaker_notes、media_items
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
            speaker_notes=str(resource_data.get("speaker_notes", "")),
            media_items=media_items,
        )
    logger.info("保存 PPT 资源：source_id=%d, pages=%d", source_id, len(resources))
    return list_ppt_resources(source_id)


def _apply_preview_paths(resources: list[dict[str, object]], preview_paths: list[str]) -> None:
    """
    将 PowerPoint 导出的 PNG 预览写入解析资源。
    :param resources: PPT 页资源字典列表
    :param preview_paths: 按页码排序的预览 URL 列表
    :return: None
    """
    if not preview_paths:
        return
    for resource_index, resource_data in enumerate(resources):
        if resource_index < len(preview_paths):
            resource_data["slide_image"] = preview_paths[resource_index]


def _resources_from_preview_paths(preview_paths: list[str]) -> list[dict[str, object]]:
    """
    为无法 zip 解析的 PPT/PPS 文件生成仅含 PNG 预览的页资源。
    :param preview_paths: 按页码排序的预览 URL 列表
    :return: PPT 页资源字典列表
    """
    resources: list[dict[str, object]] = []
    for page_index, preview_path in enumerate(preview_paths, start=1):
        resources.append({
            "page_index": page_index,
            "slide_image": preview_path,
            "speaker_notes": "",
            "media_items": [],
        })
    return resources


def _is_powerpoint_export_candidate(file_path: Path) -> bool:
    """
    粗略判断文件是否适合交给 PowerPoint COM 导出，避免测试用简化 zip 触发修复弹窗。
    :param file_path: 待导出的 PPT 文件路径
    :return: True 表示可尝试导出预览
    """
    suffix = file_path.suffix.lower()
    if suffix in {".ppt", ".pps"}:
        return True
    if suffix not in {".pptx", ".ppsx"}:
        return False
    try:
        with zipfile.ZipFile(file_path) as archive:
            return "[Content_Types].xml" in archive.namelist()
    except (zipfile.BadZipFile, OSError):
        return False


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
    seen_media_targets: set[tuple[str, str]] = set()
    for relationship in root:
        target = str(relationship.attrib.get("Target", ""))
        relationship_type = str(relationship.attrib.get("Type", "")).lower()
        if not _is_ppt_media_relationship(target, relationship_type):
            continue
        media_key = (target.lower(), relationship_type)
        if media_key in seen_media_targets:
            continue
        seen_media_targets.add(media_key)
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
    """
    判断 PPT 关系是否指向音视频媒体文件。
    :param target: PPT 关系中的目标路径
    :param relationship_type: PPT 关系类型
    :return: True 表示该关系指向可控制的音视频媒体
    """
    lower_target = target.lower()
    lower_relationship_type = relationship_type.lower()
    media_extensions = {".mp4", ".mov", ".wmv", ".avi", ".mp3", ".wav", ".wma", ".m4a"}
    media_relationship_markers = {"/video", "/audio"}
    return (
        any(marker in lower_relationship_type for marker in media_relationship_markers)
        or Path(lower_target).suffix in media_extensions
    )


def _guess_ppt_media_type(media_name: str, relationship_type: str) -> str:
    """
    根据关系类型和扩展名推断 PPT 媒体类型。
    :param media_name: 媒体文件名
    :param relationship_type: PPT 关系类型
    :return: audio 或 video
    """
    lower_name = media_name.lower()
    if "audio" in relationship_type or Path(lower_name).suffix in {".mp3", ".wav", ".wma", ".m4a"}:
        return "audio"
    return "video"


def _get_ppt_source(source_id: int) -> MediaSource:
    """
    查询并校验 PPT 媒体源。
    :param source_id: 媒体源 ID
    :return: PPT 类型的媒体源
    :raises MediaError: 源不存在或不是 PPT 时
    """
    try:
        source = MediaSource.objects.get(pk=source_id)
    except MediaSource.DoesNotExist as not_found:
        raise MediaError(f"媒体源 id={source_id} 不存在") from not_found
    if source.source_type != SourceType.PPT:
        raise MediaError("仅 PPT 源支持解析资源")
    return source


def _ppt_resource_payload(resource: PptResource) -> dict[str, object]:
    """
    序列化 PPT 页资源。
    :param resource: PptResource 模型实例
    :return: 前端和 API 可直接使用的资源字典
    """
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
    """
    将输入转换为非负整数，失败时使用默认值。
    :param raw_value: 任意用户输入值
    :param default: 转换失败时使用的默认值
    :return: 非负整数
    """
    try:
        return max(0, int(raw_value))
    except (TypeError, ValueError):
        return default
