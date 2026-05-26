#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PPT 页面预览导出服务，按媒体源选择的播放器后端导出。
@Project : SCP-cv
@File : ppt_preview.py
@Author : Qintsg
@Date : 2026-05-26
'''
from __future__ import annotations

import logging
import os
import zipfile
from pathlib import Path
from typing import Optional

from django.conf import settings

from scp_cv import libreoffice as lo_runtime
from scp_cv.ppt_backend import DEFAULT_PPT_BACKEND, normalize_ppt_backend

logger = logging.getLogger(__name__)

_PPT_ALERTS_NONE = 1
_PPT_BACKEND_LIBREOFFICE = "libreoffice"
_PPT_BACKEND_POWERPOINT = "powerpoint"


def export_ppt_slide_previews(file_path: Path, source_id: int) -> list[str]:
    """
    导出 PPT 每页 PNG 预览。
    :param file_path: PPT 文件路径
    :param source_id: 媒体源 ID，用于隔离导出目录
    :return: 按页码排序的媒体 URL 列表；不可导出时返回空列表
    """
    if os.name != "nt" or not file_path.is_file() or not _is_ppt_export_candidate(file_path):
        return []
    backend = _source_ppt_backend(source_id)
    if backend == _PPT_BACKEND_POWERPOINT:
        return export_ppt_slide_previews_with_powerpoint(file_path, source_id)
    return export_ppt_slide_previews_with_libreoffice(file_path, source_id)


def export_ppt_slide_previews_with_libreoffice(file_path: Path, source_id: int) -> list[str]:
    """
    使用 LibreOffice UNO 导出 PPT PNG 预览。
    :param file_path: PPT 文件路径
    :param source_id: 媒体源 ID
    :return: 按页码排序的媒体 URL 列表
    """
    relative_dir, preview_dir = _prepare_preview_dir(source_id)
    session: Optional[lo_runtime.LibreOfficeSession] = None
    document: Optional[object] = None
    try:
        session = lo_runtime.start_libreoffice_session(headless=True)
        document = lo_runtime.load_document(session, file_path, hidden=True, readonly=True)
        draw_pages = document.getDrawPages()
        slide_count = int(draw_pages.getCount())
        exporter = session.create_instance("com.sun.star.drawing.GraphicExportFilter")
        preview_paths: list[str] = []
        for page_index in range(slide_count):
            output_path = preview_dir / f"slide-{page_index + 1}.png"
            draw_page = draw_pages.getByIndex(page_index)
            exporter.setSourceDocument(draw_page)
            exporter.filter(
                (
                    session.property_value("URL", session.path_to_file_url(output_path)),
                    session.property_value("MediaType", "image/png"),
                )
            )
            if not output_path.is_file():
                raise lo_runtime.LibreOfficeError(f"LibreOffice 未生成预览文件：{output_path}")
            preview_paths.append(_media_url(relative_dir / output_path.name))
        return preview_paths
    except Exception as export_error:
        logger.info("LibreOffice PPT 预览导出失败：%s", export_error)
        _clear_preview_dir(preview_dir)
        return []
    finally:
        if document is not None:
            lo_runtime.close_document(document)
        if session is not None:
            session.close()


def export_ppt_slide_previews_with_powerpoint(file_path: Path, source_id: int) -> list[str]:
    """
    使用本机 PowerPoint 将每页幻灯片导出为 PNG 预览。
    :param file_path: PPT 文件路径
    :param source_id: 媒体源 ID
    :return: 按页码排序的媒体 URL 列表
    """
    if not _is_powerpoint_export_candidate(file_path):
        return []
    try:
        import pythoncom
        import win32com.client
    except ImportError as import_error:
        logger.info("PPT 预览导出跳过，缺少 COM 依赖：%s", import_error)
        return []

    relative_dir, preview_dir = _prepare_preview_dir(source_id)
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
            preview_paths.append(_media_url(relative_dir / output_path.name))
        return preview_paths
    except Exception as export_error:
        logger.info("PowerPoint PPT 预览导出失败：%s", export_error)
        _clear_preview_dir(preview_dir)
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


def _source_ppt_backend(source_id: int) -> str:
    """
    读取媒体源选择的 PPT 预览后端。
    :param source_id: 媒体源 ID
    :return: libreoffice 或 powerpoint
    """
    try:
        from scp_cv.apps.playback.models import MediaSource

        source = MediaSource.objects.filter(pk=source_id).only("ppt_backend").first()
        return normalize_ppt_backend(getattr(source, "ppt_backend", DEFAULT_PPT_BACKEND))
    except Exception as backend_error:
        logger.info("PPT 预览后端读取失败，使用 LibreOffice：%s", backend_error)
        return DEFAULT_PPT_BACKEND


def _is_ppt_export_candidate(file_path: Path) -> bool:
    """
    粗略判断文件是否适合导出，避免测试用简化 zip 触发外部程序修复弹窗。
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


def _is_powerpoint_export_candidate(file_path: Path) -> bool:
    """
    判断文件是否适合交给 PowerPoint COM 导出。
    :param file_path: 待导出的 PPT 文件路径
    :return: True 表示可尝试 PowerPoint 导出
    """
    return _is_ppt_export_candidate(file_path)


__all__ = [
    "export_ppt_slide_previews",
    "export_ppt_slide_previews_with_libreoffice",
    "export_ppt_slide_previews_with_powerpoint",
]
