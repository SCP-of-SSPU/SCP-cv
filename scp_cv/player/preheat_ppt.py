#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PowerPoint 应用预热资源管理。
@Project : SCP-cv
@File : preheat_ppt.py
@Author : Qintsg
@Date : 2026-06-08
'''
from __future__ import annotations

import logging

from scp_cv.player.adapters.ppt_focus import conceal_ppt_editor_window
from scp_cv.player.adapters.ppt_process import (
    read_ppt_app_process_id,
    record_spawned_ppt_process,
    snapshot_candidate_process_ids_for_prog_ids,
)
from scp_cv.player.preheat_types import PreheatedPptApplication
from scp_cv.ppt_com import POWERPOINT_COM_PROG_IDS

logger = logging.getLogger(__name__)
_POWERPOINT_BACKEND_KEY = "powerpoint"


class PptApplicationPreheater:
    """PowerPoint COM 应用预热池。"""

    def __init__(self) -> None:
        """
        初始化 COM 预热池。
        :return: None
        """
        self._items: dict[str, PreheatedPptApplication] = {}
        self._com_initialized = False

    def preheat(self) -> None:
        """
        预热 PowerPoint COM 应用。
        :return: None
        """
        if _POWERPOINT_BACKEND_KEY in self._items:
            return
        self._ensure_com_initialized()
        try:
            import win32com.client
        except Exception as import_error:
            logger.warning("PowerPoint COM 预热不可用：%s", import_error)
            return
        existing_process_ids = snapshot_candidate_process_ids_for_prog_ids(
            POWERPOINT_COM_PROG_IDS
        )
        last_error: BaseException | None = None
        for prog_id in POWERPOINT_COM_PROG_IDS:
            try:
                app = win32com.client.DispatchEx(prog_id)
                process_id = read_ppt_app_process_id(app, prog_id, existing_process_ids)
                spawned_process = (
                    process_id != 0 and process_id not in existing_process_ids
                )
                if spawned_process:
                    record_spawned_ppt_process(process_id)
                    # 隐藏由预热拉起的编辑窗口，避免任务栏出现 PowerPoint 按钮。
                    conceal_ppt_editor_window(app, logger)
                self._items[_POWERPOINT_BACKEND_KEY] = PreheatedPptApplication(
                    _POWERPOINT_BACKEND_KEY,
                    app,
                    prog_id,
                    process_id=process_id,
                    spawned_process=spawned_process,
                )
                logger.info(
                    "PowerPoint 已预热：prog_id=%s, pid=%d, spawned=%s",
                    prog_id,
                    process_id,
                    spawned_process,
                )
                return
            except BaseException as dispatch_error:
                last_error = dispatch_error
        logger.warning("PowerPoint 预热失败：%s", last_error)

    def preheat_source(self, source_id: int, uri: str) -> None:
        """
        文件级预热指定 PPT 源：启动 PowerPoint 并预打开 Presentation。
        :param source_id: 媒体源 ID
        :param uri: PPT 文件路径
        :return: None
        """
        if source_id <= 0 or not uri:
            return
        self.preheat()
        item = self._items.pop(_POWERPOINT_BACKEND_KEY, None)
        if item is None:
            return
        try:
            presentation = _open_presentation(item.app, uri)
            _mark_presentation_clean(presentation)
        except Exception as open_error:
            logger.warning("PowerPoint 文件级预热失败：source_id=%d, error=%s", source_id, open_error)
            self._items[_POWERPOINT_BACKEND_KEY] = item
            return
        existing = self._items.pop(_source_key(source_id, uri), None)
        if existing is not None and existing.presentation is not presentation:
            _close_presentation(existing.presentation)
            if existing.app is not item.app:
                quit_ppt_app_if_idle(existing.app)
        self._items[_source_key(source_id, uri)] = PreheatedPptApplication(
            _POWERPOINT_BACKEND_KEY,
            item.app,
            item.prog_id,
            source_id=source_id,
            uri=uri,
            presentation=presentation,
            process_id=item.process_id,
            spawned_process=item.spawned_process,
        )
        logger.info("PowerPoint 文件已预热：source_id=%d", source_id)

    def take(self, source_id: int = 0, uri: str = "") -> PreheatedPptApplication | None:
        """
        取出 PowerPoint 预热应用。
        :param source_id: 可选媒体源 ID，用于取出文件级预热项
        :param uri: 可选文件路径，用于取出文件级预热项
        :return: 预热应用或 None
        """
        if source_id > 0 and uri:
            item = self._items.pop(_source_key(source_id, uri), None)
            if item is not None:
                return item
        return self._items.pop(_POWERPOINT_BACKEND_KEY, None)

    def return_item(self, item: PreheatedPptApplication) -> None:
        """
        归还预热应用。
        :param item: 预热应用
        :return: None
        """
        self._ensure_com_initialized()
        _close_presentation(item.presentation)
        item.source_id = 0
        item.uri = ""
        item.presentation = None
        if item.spawned_process:
            # 放映结束后 PowerPoint 可能重新显示编辑窗口，归还时再次隐藏。
            conceal_ppt_editor_window(item.app, logger)
        existing = self._items.pop(_POWERPOINT_BACKEND_KEY, None)
        if existing is not None:
            _dispose_item(existing, quit_app=existing.app is not item.app)
        self._items[_POWERPOINT_BACKEND_KEY] = item

    def close_all(self) -> None:
        """
        关闭全部预热应用。
        :return: None
        """
        for item in list(self._items.values()):
            _dispose_item(item, quit_app=True)
        self._items.clear()
        self._uninitialize_com()

    def _ensure_com_initialized(self) -> None:
        """确保当前线程已初始化 COM。"""
        if self._com_initialized:
            return
        try:
            import pythoncom

            pythoncom.CoInitialize()
            self._com_initialized = True
        except Exception as init_error:
            logger.debug("COM 预热初始化失败：%s", init_error)

    def _uninitialize_com(self) -> None:
        """释放预热池持有的 COM 初始化。"""
        if not self._com_initialized:
            return
        try:
            import pythoncom

            pythoncom.CoUninitialize()
        except Exception:
            pass
        self._com_initialized = False


def quit_ppt_app(app: object) -> None:
    """
    尽力退出 PowerPoint 应用。
    :param app: COM Application 对象
    :return: None
    """
    try:
        app.Quit()
    except Exception:
        pass


def quit_ppt_app_if_idle(app: object) -> bool:
    """
    仅在 PowerPoint 没有其它打开演示文稿时退出应用。
    PowerPoint 是单实例进程，其它播放窗口或用户文档可能仍在使用。
    :param app: COM Application 对象
    :return: True 表示已尝试退出
    """
    try:
        presentation_count = int(app.Presentations.Count)
    except Exception:
        presentation_count = 0
    if presentation_count > 0:
        logger.info("PowerPoint 仍有 %d 个演示文稿打开，跳过退出", presentation_count)
        return False
    quit_ppt_app(app)
    return True


def _open_presentation(app: object, uri: str) -> object:
    """
    以无编辑窗口方式预打开演示文稿。
    :param app: PowerPoint COM Application 对象
    :param uri: PPT 文件路径
    :return: Presentation COM 对象
    """
    presentations = app.Presentations
    try:
        return presentations.Open(uri, ReadOnly=False, Untitled=True, WithWindow=False)
    except Exception as keyword_error:
        try:
            return presentations.Open(uri, False, True, False)
        except Exception:
            raise keyword_error


def _mark_presentation_clean(presentation: object | None) -> None:
    """
    标记演示文稿无需保存，避免关闭确认。
    :param presentation: Presentation COM 对象
    :return: None
    """
    if presentation is None:
        return
    try:
        presentation.Saved = True
    except Exception:
        pass


def _close_presentation(presentation: object | None) -> None:
    """
    关闭预热演示文稿。
    :param presentation: Presentation COM 对象
    :return: None
    """
    if presentation is None:
        return
    _mark_presentation_clean(presentation)
    try:
        presentation.Close(False)
    except TypeError:
        presentation.Close()
    except Exception:
        pass


def _dispose_item(item: PreheatedPptApplication, quit_app: bool) -> None:
    """
    释放预热项持有的演示文稿和应用。
    :param item: 预热项
    :param quit_app: 是否退出 COM 应用
    :return: None
    """
    _close_presentation(item.presentation)
    if quit_app:
        quit_ppt_app_if_idle(item.app)


def _source_key(source_id: int, uri: str) -> str:
    """
    构造文件级预热项键。
    :param source_id: 媒体源 ID
    :param uri: 文件路径
    :return: 字典键
    """
    return f"{_POWERPOINT_BACKEND_KEY}:{source_id}:{uri}"


__all__ = [
    "PptApplicationPreheater",
    "quit_ppt_app",
    "quit_ppt_app_if_idle",
]
