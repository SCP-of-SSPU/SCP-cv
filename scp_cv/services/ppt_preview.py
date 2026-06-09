#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PPT 页面预览导出服务，统一通过 Microsoft PowerPoint COM 导出。
@Project : SCP-cv
@File : ppt_preview.py
@Author : Qintsg
@Date : 2026-05-26
'''
from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import zipfile
from collections.abc import Iterable
from pathlib import Path
from typing import Optional

from django.conf import settings

from scp_cv.ppt_com import POWERPOINT_COM_PROG_IDS

logger = logging.getLogger(__name__)

_PPT_ALERTS_NONE = 1
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
    return _export_ppt_slide_previews_with_worker(file_path, source_id)


def export_ppt_slide_previews_in_process(
    file_path: Path,
    source_id: int,
    backend: Optional[str] = None,
) -> list[str]:
    """
    在当前进程内导出 PPT 预览，供隔离 worker 调用。
    :param file_path: PPT 文件路径
    :param source_id: 媒体源 ID，用于隔离导出目录
    :param backend: 旧 worker 参数兼容；当前忽略并始终使用 PowerPoint
    :return: 按页码排序的媒体 URL 列表；不可导出时返回空列表
    """
    if os.name != "nt" or not file_path.is_file() or not _is_ppt_export_candidate(file_path):
        return []
    return export_ppt_slide_previews_with_powerpoint(file_path, source_id)


def _export_ppt_slide_previews_with_worker(file_path: Path, source_id: int) -> list[str]:
    """
    通过独立 Python 子进程导出 PPT 预览，隔离 Office/UNO 原生库副作用。
    :param file_path: PPT 文件路径
    :param source_id: 媒体源 ID
    :return: 按页码排序的媒体 URL 列表；worker 失败时返回空列表
    """
    worker_script = Path(__file__).with_name("ppt_preview_worker.py")
    command = [
        sys.executable,
        str(worker_script),
        str(file_path),
        str(source_id),
    ]
    env = os.environ.copy()
    env.setdefault("DJANGO_SETTINGS_MODULE", "scp_cv.settings")
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
            creationflags=_subprocess_creation_flags(),
            check=False,
        )
    except subprocess.TimeoutExpired:
        logger.info("PowerPoint 预览 worker 超时：source_id=%d", source_id)
        return []
    except OSError as worker_error:
        logger.info("PowerPoint 预览 worker 启动失败：%s", worker_error)
        return []

    if completed.returncode != 0:
        logger.info(
            "PowerPoint 预览 worker 失败：source_id=%d, returncode=%s, stderr=%s",
            source_id,
            completed.returncode,
            completed.stderr.strip(),
        )
        return []
    return _parse_worker_preview_output(completed.stdout)


def _prepend_pythonpath(path: str, current_pythonpath: str) -> str:
    """
    将项目根目录加入 PYTHONPATH 前部，确保 worker 可导入 scp_cv 包。
    :param path: 需要加入的路径
    :param current_pythonpath: 当前 PYTHONPATH
    :return: 合并后的 PYTHONPATH
    """
    if not current_pythonpath:
        return path
    entries = [entry for entry in current_pythonpath.split(os.pathsep) if entry]
    if path in entries:
        return current_pythonpath
    return os.pathsep.join([path, *entries])


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
    :return: worker payload；无法解析或失败时返回空字典
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
    logger.info("PPT 预览 worker 未输出有效 JSON")
    return {}


def _preview_worker_timeout_seconds() -> float:
    """
    获取 PPT 预览 worker 超时时间。
    :return: 超时秒数
    """
    raw_value = getattr(settings, "PPT_PREVIEW_WORKER_TIMEOUT_SECONDS", _PREVIEW_WORKER_TIMEOUT_SECONDS)
    try:
        return max(1.0, float(raw_value))
    except (TypeError, ValueError):
        return _PREVIEW_WORKER_TIMEOUT_SECONDS


def _subprocess_creation_flags() -> int:
    """
    返回 PPT 预览 worker 的 Windows 子进程创建标志。
    :return: subprocess creationflags
    """
    if os.name != "nt":
        return 0
    return getattr(subprocess, "CREATE_NO_WINDOW", 0)


def export_ppt_slide_previews_with_powerpoint(file_path: Path, source_id: int) -> list[str]:
    """
    使用本机 PowerPoint 将每页幻灯片导出为 PNG 预览。
    :param file_path: PPT 文件路径
    :param source_id: 媒体源 ID
    :return: 按页码排序的媒体 URL 列表
    """
    return _export_ppt_slide_previews_with_com(
        file_path,
        source_id,
        POWERPOINT_COM_PROG_IDS,
        "PowerPoint",
    )


def _export_ppt_slide_previews_with_com(
    file_path: Path,
    source_id: int,
    com_prog_ids: Iterable[str],
    app_label: str,
) -> list[str]:
    """
    使用本机 PPT COM 应用将每页幻灯片导出为 PNG 预览。
    :param file_path: PPT 文件路径
    :param source_id: 媒体源 ID
    :param com_prog_ids: 同一后端可尝试的 COM ProgID 候选
    :param app_label: 日志展示名称
    :return: 按页码排序的媒体 URL 列表
    """
    if not _is_com_export_candidate(file_path):
        return []
    try:
        import pythoncom
        import win32com.client
    except ImportError as import_error:
        logger.info("%s PPT 预览导出跳过，缺少 COM 依赖：%s", app_label, import_error)
        return []

    relative_dir, preview_dir = _prepare_preview_dir(source_id)
    pythoncom.CoInitialize()
    ppt_app: Optional[object] = None
    presentation: Optional[object] = None
    try:
        ppt_app = _dispatch_ppt_preview_app(win32com.client, com_prog_ids, app_label)
        ppt_app.DisplayAlerts = _PPT_ALERTS_NONE
        presentation = _open_com_presentation_readonly(ppt_app, str(file_path))
        preview_paths: list[str] = []
        slide_count = int(presentation.Slides.Count)
        for page_index in range(1, slide_count + 1):
            output_path = preview_dir / f"slide-{page_index}.png"
            presentation.Slides(page_index).Export(str(output_path), "PNG")
            preview_paths.append(_media_url(relative_dir / output_path.name))
        return preview_paths
    except Exception as export_error:
        logger.info("%s PPT 预览导出失败：%s", app_label, export_error)
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


def _dispatch_ppt_preview_app(
    win32com_client: object,
    com_prog_ids: Iterable[str],
    app_label: str,
) -> object:
    """
    按候选 ProgID 创建 PPT 预览导出 COM 应用。
    :param win32com_client: win32com.client 模块对象
    :param com_prog_ids: 同一后端可尝试的 ProgID 候选
    :param app_label: 日志展示名称
    :return: PPT 应用 COM 对象
    :raises RuntimeError: 所有 ProgID 均不可用时
    """
    last_error: Optional[Exception] = None
    prog_id_tuple = tuple(com_prog_ids)
    for prog_id in prog_id_tuple:
        try:
            return win32com_client.DispatchEx(prog_id)
        except Exception as dispatch_error:
            last_error = dispatch_error
            logger.debug(
                "%s 预览导出 COM ProgID 不可用：%s，原因：%s",
                app_label,
                prog_id,
                dispatch_error,
            )
    supported_prog_ids = ", ".join(prog_id_tuple)
    raise RuntimeError(
        f"未找到 {app_label} COM 自动化对象：{supported_prog_ids}"
    ) from last_error


def _open_com_presentation_readonly(ppt_app: object, file_path: str) -> object:
    """
    以只读、无编辑窗口方式打开演示文稿。
    :param ppt_app: PPT 应用 COM 对象
    :param file_path: PPT 文件路径
    :return: Presentation COM 对象
    """
    presentations = ppt_app.Presentations
    try:
        return presentations.Open(
            file_path,
            ReadOnly=True,
            Untitled=False,
            WithWindow=False,
        )
    except Exception as keyword_error:
        try:
            return presentations.Open(file_path, True, False, False)
        except Exception:
            raise keyword_error


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


def _is_com_export_candidate(file_path: Path) -> bool:
    """
    判断文件是否适合交给本机 PPT COM 应用导出。
    :param file_path: 待导出的 PPT 文件路径
    :return: True 表示可尝试 COM 导出
    """
    return _is_ppt_export_candidate(file_path)


__all__ = [
    "export_ppt_slide_previews",
    "export_ppt_slide_previews_in_process",
    "export_ppt_slide_previews_with_powerpoint",
]
