#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PPT 页面预览导出服务，统一委托唯一 PowerPoint Broker。
@Project : SCP-cv
@File : ppt_preview.py
@Author : Qintsg
@Date : 2026-05-26
'''
from __future__ import annotations

import logging
import os
import uuid
import zipfile
from pathlib import Path

from django.conf import settings

from scp_cv.player.ppt_broker import (
    PptBrokerClient,
    PptSlideExportRequest,
)

logger = logging.getLogger(__name__)

_PREVIEW_WORKER_TIMEOUT_SECONDS = 180.0


def export_ppt_slide_previews(file_path: Path, source_id: int) -> list[str]:
    """
    导出 PPT 每页 PNG 预览。
    :param file_path: PPT 文件路径
    :param source_id: 媒体源 ID，用于隔离导出目录
    :return: 按页码排序的媒体 URL 列表；不可导出时返回空列表
    """
    if os.name != "nt" or not file_path.is_file() or not _is_ppt_export_candidate(file_path):
        return []
    return _export_ppt_slide_previews_with_broker(file_path, source_id)


def export_ppt_slide_previews_in_process(
    file_path: Path,
    source_id: int,
    backend: str | None = None,
) -> list[str]:
    """
    兼容旧 worker 的入口；实际导出仍只通过 PowerPoint Broker。
    :param file_path: PPT 文件路径
    :param source_id: 媒体源 ID，用于隔离导出目录
    :param backend: 旧 worker 参数兼容；当前忽略并始终使用 PowerPoint
    :return: 按页码排序的媒体 URL 列表；不可导出时返回空列表
    """
    del backend
    return export_ppt_slide_previews(file_path, source_id)


def _export_ppt_slide_previews_with_broker(
    file_path: Path,
    source_id: int,
) -> list[str]:
    """
    让唯一 Broker 导出 PNG，服务层只管理目录和媒体 URL。
    :param file_path: PPT 文件路径
    :param source_id: 媒体源 ID
    :return: 按页码排序的媒体 URL 列表；Broker 失败时返回空列表
    """
    relative_dir, preview_dir = _prepare_preview_dir(source_id)
    try:
        result = PptBrokerClient(
            timeout_seconds=_preview_worker_timeout_seconds(),
        ).export_slides(
            PptSlideExportRequest(
                source_uri=str(file_path),
                output_dir=str(preview_dir),
                image_format="PNG",
                request_id=uuid.uuid4().hex,
            )
        )
        preview_paths = _validate_broker_preview_paths(preview_dir, result.paths)
    except Exception as export_error:
        logger.warning(
            "PowerPoint Broker 预览导出失败：source_id=%d；"
            "请确认 runall 正在运行，或先执行 manage.py run_ppt_broker，"
            "并检查 Broker 日志。原始错误：%s",
            source_id,
            export_error,
        )
        _clear_preview_dir(preview_dir)
        return []
    logger.info(
        "PowerPoint Broker 预览导出成功：source_id=%d, slides=%d, "
        "powerpoint_pid=%d",
        source_id,
        len(preview_paths),
        result.powerpoint_pid,
    )
    return [
        _media_url(relative_dir / preview_path.name)
        for preview_path in preview_paths
    ]


def _preview_worker_timeout_seconds() -> float:
    """
    获取 PPT 预览 Broker 调用超时；保留旧配置名兼容现有部署。
    :return: 超时秒数
    """
    raw_value = getattr(settings, "PPT_PREVIEW_WORKER_TIMEOUT_SECONDS", _PREVIEW_WORKER_TIMEOUT_SECONDS)
    try:
        return max(1.0, float(raw_value))
    except (TypeError, ValueError):
        return _PREVIEW_WORKER_TIMEOUT_SECONDS


def export_ppt_slide_previews_with_powerpoint(file_path: Path, source_id: int) -> list[str]:
    """
    兼容旧入口；通过唯一 PowerPoint Broker 导出 PNG 预览。
    :param file_path: PPT 文件路径
    :param source_id: 媒体源 ID
    :return: 按页码排序的媒体 URL 列表
    """
    return export_ppt_slide_previews(file_path, source_id)


def _validate_broker_preview_paths(
    preview_dir: Path,
    raw_paths: tuple[str, ...],
) -> list[Path]:
    """确认 Broker 只返回预览目录内真实存在的 PNG 文件。"""
    resolved_preview_dir = preview_dir.resolve()
    preview_paths: list[Path] = []
    for raw_path in raw_paths:
        preview_path = Path(raw_path).resolve()
        if (
            preview_path.parent != resolved_preview_dir
            or preview_path.suffix.casefold() != ".png"
            or not preview_path.is_file()
        ):
            raise RuntimeError(
                "PowerPoint Broker 返回了无效预览路径："
                f"path={preview_path}, expected_dir={resolved_preview_dir}"
            )
        preview_paths.append(preview_path)
    if not preview_paths:
        raise RuntimeError("PowerPoint Broker 未生成任何 PNG 预览")
    return preview_paths


def _prepare_preview_dir(source_id: int) -> tuple[Path, Path]:
    """
    创建并清空 PPT 预览输出目录。
    :param source_id: 媒体源 ID
    :return: 相对目录和绝对目录
    """
    relative_dir = Path("ppt_previews") / str(source_id)
    preview_dir = Path(settings.MEDIA_ROOT) / relative_dir
    preview_dir.mkdir(parents=True, exist_ok=True)
    _clear_preview_dir(preview_dir)
    return relative_dir, preview_dir


def _clear_preview_dir(preview_dir: Path) -> None:
    """
    清理预览目录中的旧 PNG。
    :param preview_dir: 预览目录
    :return: None
    """
    for old_preview in preview_dir.glob("*.png"):
        old_preview.unlink(missing_ok=True)


def _media_url(relative_path: Path) -> str:
    """
    将 MEDIA_ROOT 下相对路径转换为媒体 URL。
    :param relative_path: MEDIA_ROOT 相对路径
    :return: 媒体 URL
    """
    return f"{settings.MEDIA_URL.rstrip('/')}/{relative_path.as_posix()}"


def _is_ppt_export_candidate(file_path: Path) -> bool:
    """
    粗略判断文件是否适合导出，避免测试用简化 zip 触发外部程序修复弹窗。
    :param file_path: 待导出的 PPT 文件路径
    :return: True 表示可尝试导出预览
    """
    suffix = file_path.suffix.lower()
    if suffix in {".ppt", ".pps", ".pot", ".odp"}:
        return True
    if suffix not in {".pptx", ".pptm", ".ppsx", ".ppsm", ".potx", ".potm"}:
        return False
    try:
        with zipfile.ZipFile(file_path) as archive:
            return "[Content_Types].xml" in archive.namelist()
    except (zipfile.BadZipFile, OSError):
        return False


__all__ = [
    "export_ppt_slide_previews",
    "export_ppt_slide_previews_in_process",
    "export_ppt_slide_previews_with_powerpoint",
]
