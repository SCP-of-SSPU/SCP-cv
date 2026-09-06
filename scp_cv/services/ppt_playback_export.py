#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PPT 放映格式导出后端：统一使用 Microsoft PowerPoint COM。
@Project : SCP-cv
@File : ppt_playback_export.py
@Author : Qintsg
@Date : 2026-05-31
'''
from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable

from django.conf import settings

from scp_cv.ppt_com import POWERPOINT_COM_PROG_IDS

logger = logging.getLogger(__name__)

_POWERPOINT_SAVE_AS_OPEN_XML_SHOW = 28
_POWERPOINT_SAVE_AS_SHOW = 7
_PPT_ALERTS_NONE = 1


class PptPlaybackExportError(RuntimeError):
    """PPT 放映格式导出失败。"""


def export_show_file(
    source_path: Path,
    target_path: Path,
    target_extension: str,
    preferred_backend: str = "powerpoint",
) -> str:
    """
    使用 PowerPoint 导出 show-format 文件。

    :param source_path: 源文件路径
    :param target_path: 目标 .ppsx/.pps 路径
    :param target_extension: 目标扩展名
    :param preferred_backend: 旧参数兼容；当前忽略并始终使用 PowerPoint
    :return: 实际成功导出的后端，固定为 powerpoint
    """
    target_path.unlink(missing_ok=True)
    _export_with_com(source_path, target_path, target_extension, POWERPOINT_COM_PROG_IDS, "PowerPoint")
    if not target_path.is_file():
        raise PptPlaybackExportError("PowerPoint 未生成目标文件")
    logger.info("PPT 放映格式缓存导出成功：%s -> %s（powerpoint）", source_path, target_path)
    return "powerpoint"


def _export_with_com(
    source_path: Path,
    target_path: Path,
    target_extension: str,
    prog_ids: Iterable[str],
    app_label: str,
) -> None:
    """
    使用 PowerPoint COM SaveAs 导出 show-format 文件。

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

    :param app: PowerPoint COM 应用
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
