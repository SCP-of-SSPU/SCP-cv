#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
资源文件管理服务，负责上传、删除、列表查询等文件管理操作。
@Project : SCP-cv
@File : resource_manager.py
@Author : Qintsg
@Date : 2026-04-10
'''
from __future__ import annotations

import hashlib
import logging
import shutil
from pathlib import Path

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.utils import timezone

from scp_cv.apps.resources.models import (
    ParseState,
    PresentationDocument,
    PresentationPageMedia,
    ResourceFile,
    ResourceKind,
    ResourceState,
)

logger = logging.getLogger(__name__)

# 允许上传的文件扩展名
ALLOWED_EXTENSIONS: frozenset[str] = frozenset({".ppt", ".pptx"})

# 上传资源根目录，相对于 BASE_DIR
UPLOAD_ROOT_NAME: str = "uploads"
RESOURCE_DIR_NAME: str = "resources"


class ResourceError(Exception):
    """资源管理操作的业务异常。"""


def _get_resource_dir(resource_id: int) -> Path:
    """
    获取某个资源的专属存储目录。
    :param resource_id: ResourceFile 主键
    :return: 资源目录的绝对路径
    """
    return Path(settings.BASE_DIR) / UPLOAD_ROOT_NAME / RESOURCE_DIR_NAME / str(resource_id)


def _compute_file_checksum(file_path: Path) -> str:
    """
    计算文件的 SHA-256 校验和。
    :param file_path: 文件绝对路径
    :return: 十六进制校验和字符串
    """
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(8192), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


def upload_ppt_file(uploaded_file: UploadedFile) -> ResourceFile:
    """
    处理上传的 PPT/PPTX 文件：保存文件、创建资源记录。
    :param uploaded_file: Django 上传文件对象
    :return: 创建的 ResourceFile 实例
    """
    file_name = uploaded_file.name or "untitled.pptx"
    file_extension = Path(file_name).suffix.lower()

    if file_extension not in ALLOWED_EXTENSIONS:
        raise ResourceError(f"不支持的文件格式：{file_extension}，仅允许 {', '.join(ALLOWED_EXTENSIONS)}")

    # 确定资源类型
    file_kind = ResourceKind.PPTX if file_extension == ".pptx" else ResourceKind.PPT

    # 先创建 ResourceFile 记录获取 id
    resource = ResourceFile.objects.create(
        display_name=Path(file_name).stem,
        file_kind=file_kind,
        original_path="",  # 后续更新
        file_size_bytes=uploaded_file.size or 0,
        parse_state=ParseState.PENDING,
    )

    # 创建资源目录
    resource_dir = _get_resource_dir(resource.pk)
    resource_dir.mkdir(parents=True, exist_ok=True)

    # 保存原始文件
    original_file_path = resource_dir / file_name
    with open(original_file_path, "wb") as destination:
        for chunk in uploaded_file.chunks():
            destination.write(chunk)

    # 更新资源记录的路径和校验和
    resource.original_path = str(original_file_path)
    resource.source_checksum = _compute_file_checksum(original_file_path)
    resource.save(update_fields=["original_path", "source_checksum"])

    logger.info("上传 PPT 资源「%s」，大小 %d 字节，id=%d", resource.display_name, resource.file_size_bytes, resource.pk)
    return resource


def import_local_ppt(local_path: str) -> ResourceFile:
    """
    导入本地已有的 PPT/PPTX 文件路径。
    :param local_path: 本地文件路径
    :return: 创建的 ResourceFile 实例
    """
    source_path = Path(local_path).resolve()

    if not source_path.exists():
        raise ResourceError(f"文件不存在：{local_path}")

    file_extension = source_path.suffix.lower()
    if file_extension not in ALLOWED_EXTENSIONS:
        raise ResourceError(f"不支持的文件格式：{file_extension}")

    file_kind = ResourceKind.PPTX if file_extension == ".pptx" else ResourceKind.PPT

    resource = ResourceFile.objects.create(
        display_name=source_path.stem,
        file_kind=file_kind,
        original_path="",
        file_size_bytes=source_path.stat().st_size,
        parse_state=ParseState.PENDING,
    )

    # 复制文件到资源目录
    resource_dir = _get_resource_dir(resource.pk)
    resource_dir.mkdir(parents=True, exist_ok=True)
    copied_path = resource_dir / source_path.name
    shutil.copy2(str(source_path), str(copied_path))

    resource.original_path = str(copied_path)
    resource.source_checksum = _compute_file_checksum(copied_path)
    resource.save(update_fields=["original_path", "source_checksum"])

    logger.info("导入本地 PPT「%s」，id=%d", resource.display_name, resource.pk)
    return resource


def list_resources() -> list[dict[str, object]]:
    """
    获取所有 PPT 资源列表（不含派生资源和流配置），用于页面展示。
    :return: 资源字典列表
    """
    queryset = ResourceFile.objects.filter(
        file_kind__in=[ResourceKind.PPT, ResourceKind.PPTX],
    ).order_by("-last_used_at", "-uploaded_at")

    resource_list: list[dict[str, object]] = []
    for resource in queryset:
        resource_list.append({
            "id": resource.pk,
            "display_name": resource.display_name,
            "file_kind": resource.file_kind,
            "file_kind_label": resource.get_file_kind_display(),
            "file_size_bytes": resource.file_size_bytes,
            "file_size_display": _format_file_size(resource.file_size_bytes),
            "page_count": resource.page_count,
            "uploaded_at": resource.uploaded_at,
            "last_used_at": resource.last_used_at,
            "parse_state": resource.parse_state,
            "parse_state_label": resource.get_parse_state_display(),
            "resource_state": resource.resource_state,
            "resource_state_label": resource.get_resource_state_display(),
        })

    return resource_list


def delete_resource(resource_id: int) -> None:
    """
    删除指定资源及其关联的派生文件和数据库记录。
    正在播放的资源必须先停止。
    :param resource_id: ResourceFile 主键
    """
    try:
        resource = ResourceFile.objects.get(pk=resource_id)
    except ResourceFile.DoesNotExist as not_found:
        raise ResourceError(f"资源 id={resource_id} 不存在") from not_found

    if resource.resource_state == ResourceState.PLAYING:
        raise ResourceError(f"资源「{resource.display_name}」正在播放中，请先停止播放再删除")

    resource_dir = _get_resource_dir(resource.pk)
    resource_display_name = resource.display_name

    # 删除数据库记录（级联删除 PresentationDocument 和 PresentationPageMedia）
    resource.delete()

    # 删除物理文件目录
    if resource_dir.exists():
        shutil.rmtree(str(resource_dir))
        logger.info("删除资源目录 %s", resource_dir)

    logger.info("删除资源「%s」(id=%d)", resource_display_name, resource_id)


def get_resource_detail(resource_id: int) -> dict[str, object]:
    """
    获取单个资源的详细信息。
    :param resource_id: ResourceFile 主键
    :return: 资源详情字典
    """
    try:
        resource = ResourceFile.objects.get(pk=resource_id)
    except ResourceFile.DoesNotExist as not_found:
        raise ResourceError(f"资源 id={resource_id} 不存在") from not_found

    detail: dict[str, object] = {
        "id": resource.pk,
        "display_name": resource.display_name,
        "file_kind": resource.file_kind,
        "file_kind_label": resource.get_file_kind_display(),
        "original_path": resource.original_path,
        "file_size_bytes": resource.file_size_bytes,
        "file_size_display": _format_file_size(resource.file_size_bytes),
        "page_count": resource.page_count,
        "uploaded_at": resource.uploaded_at,
        "last_used_at": resource.last_used_at,
        "parse_state": resource.parse_state,
        "parse_state_label": resource.get_parse_state_display(),
        "resource_state": resource.resource_state,
    }

    # 附加解析文档信息
    if hasattr(resource, "presentation_document"):
        presentation_doc = resource.presentation_document
        detail["total_pages"] = presentation_doc.total_pages
        detail["derived_resource_path"] = presentation_doc.derived_resource_path

    return detail


def _format_file_size(size_bytes: int) -> str:
    """
    将字节大小格式化为人类可读文本。
    :param size_bytes: 字节数
    :return: 格式化后的大小字符串
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
