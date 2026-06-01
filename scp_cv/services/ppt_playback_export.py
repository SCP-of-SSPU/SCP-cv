#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PPT 放映格式导出后端：PowerPoint/WPS COM 与 LibreOffice headless 转换。
@Project : SCP-cv
@File : ppt_playback_export.py
@Author : Qintsg
@Date : 2026-05-31
'''
from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Iterable

from django.conf import settings

from scp_cv.ppt_backend import PPT_BACKEND_LIBREOFFICE, PPT_BACKEND_POWERPOINT, PPT_BACKEND_WPS
from scp_cv.ppt_com import POWERPOINT_COM_PROG_IDS, WPS_COM_PROG_IDS

logger = logging.getLogger(__name__)

_POWERPOINT_SAVE_AS_OPEN_XML_SHOW = 28
_POWERPOINT_SAVE_AS_SHOW = 7
_PPT_ALERTS_NONE = 1
_LIBREOFFICE_FILTERS = {
    ".ppsx": "ppsx:Impress MS PowerPoint 2007 XML AutoPlay",
    ".pps": "pps:MS PowerPoint 97 AutoPlay",
}


class PptPlaybackExportError(RuntimeError):
    """PPT 放映格式导出失败。"""


def export_show_file(
    source_path: Path,
    target_path: Path,
    target_extension: str,
    preferred_backend: str,
) -> str:
    """
    按首选后端导出 show-format 文件，失败时按稳定后端顺序降级。

    :param source_path: 源文件路径
    :param target_path: 目标 .ppsx/.pps 路径
    :param target_extension: 目标扩展名
    :param preferred_backend: 首选后端
    :return: 实际成功导出的后端
    """
    errors: list[str] = []
    for backend in _ordered_export_backends(preferred_backend):
        target_path.unlink(missing_ok=True)
        try:
            if backend == PPT_BACKEND_POWERPOINT:
                _export_with_com(source_path, target_path, target_extension, POWERPOINT_COM_PROG_IDS, "PowerPoint")
            elif backend == PPT_BACKEND_WPS:
                _export_with_com(source_path, target_path, target_extension, WPS_COM_PROG_IDS, "WPS 演示")
            else:
                _export_with_libreoffice(source_path, target_path, target_extension)
            if target_path.is_file():
                logger.info("PPT 放映格式缓存导出成功：%s -> %s（%s）", source_path, target_path, backend)
                return backend
            errors.append(f"{backend}: 未生成目标文件")
        except Exception as export_error:
            errors.append(f"{backend}: {export_error}")
            logger.info("PPT 放映格式缓存导出后端失败：backend=%s, error=%s", backend, export_error)
    raise PptPlaybackExportError("；".join(errors) or "无可用 PPT 导出后端")


def _export_with_com(
    source_path: Path,
    target_path: Path,
    target_extension: str,
    prog_ids: Iterable[str],
    app_label: str,
) -> None:
    """
    使用 PowerPoint/WPS COM SaveAs 导出 show-format 文件。

    :param source_path: 源文件路径
    :param target_path: 目标路径
    :param target_extension: 目标扩展名
    :param prog_ids: COM ProgID 候选
    :param app_label: 日志标签
    :return: None
    """
    try:
        import pythoncom
        import win32com.client
    except ImportError as import_error:
        raise PptPlaybackExportError(f"缺少 {app_label} COM 依赖：{import_error}") from import_error

    pythoncom.CoInitialize()
    app: object | None = None
    presentation: object | None = None
    try:
        app = _dispatch_com_app(win32com.client, prog_ids, app_label)
        try:
            app.DisplayAlerts = _PPT_ALERTS_NONE  # type: ignore[attr-defined]
        except Exception:
            pass
        presentation = _open_com_presentation(app, source_path)
        save_format = _com_save_format(target_extension)
        presentation.SaveAs(str(target_path), save_format)  # type: ignore[attr-defined]
    finally:
        if presentation is not None:
            _close_com_presentation(presentation)
        if app is not None:
            try:
                app.Quit()  # type: ignore[attr-defined]
            except Exception:
                pass
        try:
            pythoncom.CoUninitialize()
        except Exception:
            pass


def _export_with_libreoffice(source_path: Path, target_path: Path, target_extension: str) -> None:
    """
    使用 LibreOffice headless convert-to 导出 show-format 文件。

    :param source_path: 源文件路径
    :param target_path: 目标路径
    :param target_extension: 目标扩展名
    :return: None
    """
    from scp_cv import libreoffice as lo_runtime

    filter_arg = _LIBREOFFICE_FILTERS[target_extension]
    executable = lo_runtime.resolve_libreoffice_executable()
    profile_dir = Path(tempfile.mkdtemp(prefix="scp-cv-lo-export-profile-"))
    output_dir = Path(tempfile.mkdtemp(prefix="scp-cv-lo-export-output-"))
    profile_url = profile_dir.resolve().as_uri()
    command = [
        str(executable),
        "--headless",
        "--norestore",
        "--nodefault",
        "--nolockcheck",
        "--nofirststartwizard",
        "--nologo",
        f"-env:UserInstallation={profile_url}",
        "--convert-to",
        filter_arg,
        "--outdir",
        str(output_dir),
        str(source_path),
    ]
    try:
        completed = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=_export_timeout_seconds(),
            check=False,
        )
        if completed.returncode != 0:
            raise PptPlaybackExportError(completed.stderr.strip() or completed.stdout.strip())
        converted_path = _find_libreoffice_output(output_dir, source_path.stem, target_extension)
        if converted_path is None:
            raise PptPlaybackExportError("LibreOffice 未生成目标文件")
        shutil.copy2(converted_path, target_path)
    finally:
        shutil.rmtree(profile_dir, ignore_errors=True)
        shutil.rmtree(output_dir, ignore_errors=True)


def _dispatch_com_app(win32com_client: object, prog_ids: Iterable[str], app_label: str) -> object:
    """
    按候选 ProgID 创建 COM 应用。

    :param win32com_client: win32com.client 模块
    :param prog_ids: ProgID 候选
    :param app_label: 应用标签
    :return: COM 应用对象
    """
    last_error: Exception | None = None
    for prog_id in tuple(prog_ids):
        try:
            return win32com_client.DispatchEx(prog_id)
        except Exception as dispatch_error:
            last_error = dispatch_error
    raise PptPlaybackExportError(f"未找到 {app_label} COM 自动化对象") from last_error


def _open_com_presentation(app: object, source_path: Path) -> object:
    """
    以无编辑窗口方式打开待导出演示文稿。

    :param app: PowerPoint/WPS COM 应用
    :param source_path: 源文件路径
    :return: Presentation 对象
    """
    presentations = app.Presentations  # type: ignore[attr-defined]
    try:
        return presentations.Open(str(source_path), ReadOnly=True, Untitled=False, WithWindow=False)
    except Exception as keyword_error:
        try:
            return presentations.Open(str(source_path), True, False, False)
        except Exception:
            raise keyword_error


def _close_com_presentation(presentation: object) -> None:
    """
    关闭 COM Presentation 并抑制保存确认。

    :param presentation: Presentation 对象
    :return: None
    """
    try:
        presentation.Saved = True  # type: ignore[attr-defined]
    except Exception:
        pass
    try:
        presentation.Close()  # type: ignore[attr-defined]
    except Exception:
        pass


def _com_save_format(target_extension: str) -> int:
    """
    目标扩展名对应的 PowerPoint SaveAs format。

    :param target_extension: .ppsx 或 .pps
    :return: COM SaveAs format 常量
    """
    if target_extension == ".ppsx":
        return _POWERPOINT_SAVE_AS_OPEN_XML_SHOW
    if target_extension == ".pps":
        return _POWERPOINT_SAVE_AS_SHOW
    raise PptPlaybackExportError(f"不支持的 PPT 放映输出格式：{target_extension}")


def _ordered_export_backends(preferred_backend: str) -> list[str]:
    """
    构造导出后端尝试顺序。

    :param preferred_backend: 首选后端
    :return: 去重后的后端列表
    """
    ordered = [preferred_backend, PPT_BACKEND_POWERPOINT, PPT_BACKEND_LIBREOFFICE]
    if preferred_backend == PPT_BACKEND_WPS:
        ordered.insert(1, PPT_BACKEND_WPS)
    unique_ordered: list[str] = []
    for backend in ordered:
        if backend not in unique_ordered:
            unique_ordered.append(backend)
    return unique_ordered


def _find_libreoffice_output(output_dir: Path, source_stem: str, target_extension: str) -> Path | None:
    """
    查找 LibreOffice convert-to 输出文件。

    :param output_dir: 输出目录
    :param source_stem: 源文件 stem
    :param target_extension: 目标扩展名
    :return: 输出文件或 None
    """
    expected = output_dir / f"{source_stem}{target_extension}"
    if expected.is_file():
        return expected
    matches = sorted(output_dir.glob(f"*{target_extension}"))
    return matches[0] if matches else None


def _export_timeout_seconds() -> float:
    """
    读取 PPT 播放缓存导出超时。

    :return: 超时秒数
    """
    raw_value = getattr(settings, "PPT_PLAYBACK_EXPORT_TIMEOUT_SECONDS", 180.0)
    try:
        return max(1.0, float(raw_value))
    except (TypeError, ValueError):
        return 180.0


__all__ = ["PptPlaybackExportError", "export_show_file"]
