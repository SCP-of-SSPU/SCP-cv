#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PDF 页面预览导出服务，使用 QtPdf 在隔离子进程中渲染每页 PNG。
@Project : SCP-cv
@File : pdf_preview.py
@Author : Qintsg
@Date : 2026-08-05
'''
from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path

from django.conf import settings

logger = logging.getLogger(__name__)

_PREVIEW_WORKER_TIMEOUT_SECONDS = 180.0
_RENDER_SCALE = 2.0


def export_pdf_slide_previews(file_path: Path, source_id: int) -> list[str]:
    """
    导出 PDF 每页 PNG 预览。
    :param file_path: PDF 文件路径
    :param source_id: 媒体源 ID，用于隔离输出目录
    :return: 按页码排序的媒体 URL 列表；不可导出时返回空列表
    """
    if not file_path.is_file() or file_path.suffix.lower() != ".pdf":
        return []
    return _export_with_worker(file_path, source_id)


def export_pdf_slide_previews_in_process(file_path: Path, source_id: int) -> list[str]:
    """
    在当前进程内使用 QtPdf 渲染 PDF 页面，供隔离 worker 调用。
    :param file_path: PDF 文件路径
    :param source_id: 媒体源 ID
    :return: 按页码排序的媒体 URL 列表
    """
    if not file_path.is_file() or file_path.suffix.lower() != ".pdf":
        return []
    relative_dir, preview_dir = _prepare_preview_dir(source_id)
    try:
        from PySide6.QtCore import QSize
        from PySide6.QtGui import QGuiApplication
        from PySide6.QtPdf import QPdfDocument
    except ImportError as import_error:
        logger.info("PDF 预览导出跳过，缺少 QtPdf 依赖：%s", import_error)
        return []

    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication([])

    document = QPdfDocument()
    document.load(str(file_path))
    try:
        deadline = time.monotonic() + 5.0
        while document.status() == QPdfDocument.Status.Loading and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(0.05)
        if document.status() != QPdfDocument.Status.Ready:
            logger.info("PDF 文档加载失败：%s，status=%s", file_path, document.status())
            return []
        page_count = int(document.pageCount())
        preview_paths: list[str] = []
        for page_index in range(page_count):
            page_size = document.pagePointSize(page_index)
            target_size = QSize(
                max(1, int(page_size.width() * _RENDER_SCALE)),
                max(1, int(page_size.height() * _RENDER_SCALE)),
            )
            image = document.render(page_index, target_size)
            if image.isNull():
                logger.info("PDF 第 %d 页渲染为空：%s", page_index + 1, file_path)
                return []
            output_path = preview_dir / f"slide-{page_index + 1}.png"
            image.save(str(output_path), "PNG")
            preview_paths.append(_media_url(relative_dir / output_path.name))
        return preview_paths
    finally:
        document.close()


def _export_with_worker(file_path: Path, source_id: int) -> list[str]:
    """
    通过独立 Python 子进程渲染 PDF 预览。
    :param file_path: PDF 文件路径
    :param source_id: 媒体源 ID
    :return: 预览 URL 列表；worker 失败时返回空列表
    """
    worker_script = Path(__file__).with_name("pdf_preview_worker.py")
    command = [
        sys.executable,
        str(worker_script),
        str(file_path),
        str(source_id),
    ]
    env = os.environ.copy()
    env.setdefault("DJANGO_SETTINGS_MODULE", "scp_cv.settings")
    env["QT_QPA_PLATFORM"] = "offscreen"
    env["PYTHONPATH"] = _prepend_pythonpath(str(settings.BASE_DIR), env.get("PYTHONPATH", ""))
    try:
        completed = subprocess.run(
            command,
            cwd=str(settings.BASE_DIR),
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=_preview_worker_timeout_seconds(),
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            check=False,
        )
    except subprocess.TimeoutExpired:
        logger.info("PDF 预览 worker 超时：source_id=%d", source_id)
        return []
    except OSError as worker_error:
        logger.info("PDF 预览 worker 启动失败：%s", worker_error)
        return []

    if completed.returncode != 0:
        logger.info(
            "PDF 预览 worker 失败：source_id=%d, returncode=%s, stderr=%s",
            source_id,
            completed.returncode,
            completed.stderr.strip(),
        )
        return []
    return _parse_worker_preview_output(completed.stdout)


def _parse_worker_preview_output(stdout: str) -> list[str]:
    """
    从 worker 标准输出解析预览路径 JSON。
    :param stdout: worker 标准输出
    :return: 预览 URL 列表；无法解析时返回空列表
    """
    payload = _parse_worker_payload(stdout)
    previews = payload.get("previews", [])
    if not isinstance(previews, list):
        return []
    return [str(preview) for preview in previews if isinstance(preview, str)]


def _parse_worker_payload(stdout: str) -> dict[str, object]:
    """
    从 worker 标准输出解析最后一行有效 JSON payload。
    :param stdout: worker 标准输出
    :return: worker payload；失败时返回空字典
    """
    for line in reversed(stdout.splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict) or not payload.get("success"):
            return {}
        return payload
    return {}


def _prepare_preview_dir(source_id: int) -> tuple[Path, Path]:
    """
    创建并清空 PDF 预览输出目录。
    :param source_id: 媒体源 ID
    :return: 相对目录和绝对目录
    """
    relative_dir = Path("pdf_previews") / str(source_id)
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


def _preview_worker_timeout_seconds() -> float:
    """
    获取 PDF 预览 worker 超时时间。
    :return: 超时秒数
    """
    raw_value = getattr(settings, "PDF_PREVIEW_WORKER_TIMEOUT_SECONDS", _PREVIEW_WORKER_TIMEOUT_SECONDS)
    try:
        return max(1.0, float(raw_value))
    except (TypeError, ValueError):
        return _PREVIEW_WORKER_TIMEOUT_SECONDS


def _prepend_pythonpath(path: str, current_pythonpath: str) -> str:
    """
    将项目根目录加入 PYTHONPATH 前部。
    :param path: 项目根目录
    :param current_pythonpath: 当前 PYTHONPATH
    :return: 合并后的 PYTHONPATH
    """
    if not current_pythonpath:
        return path
    entries = [entry for entry in current_pythonpath.split(os.pathsep) if entry]
    if path in entries:
        return current_pythonpath
    return os.pathsep.join([path, *entries])


__all__ = [
    "export_pdf_slide_previews",
    "export_pdf_slide_previews_in_process",
]
