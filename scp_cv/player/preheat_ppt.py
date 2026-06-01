#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PPT 后端应用预热资源管理。
@Project : SCP-cv
@File : preheat_ppt.py
@Author : Qintsg
@Date : 2026-05-28
'''
from __future__ import annotations

import logging

from scp_cv.player.preheat_types import PreheatedPptApplication
from scp_cv.ppt_backend import PPT_BACKEND_POWERPOINT, PPT_BACKEND_WPS
from scp_cv.ppt_com import POWERPOINT_COM_PROG_IDS, WPS_COM_PROG_IDS

logger = logging.getLogger(__name__)


class PptApplicationPreheater:
    """PowerPoint/WPS COM 应用预热池。"""

    def __init__(self) -> None:
        """
        初始化 COM 预热池。
        :return: None
        """
        self._items: dict[str, PreheatedPptApplication] = {}
        self._com_initialized = False

    def preheat(self, backend: str) -> None:
        """
        预热指定 PPT COM 后端。
        :param backend: powerpoint 或 wps
        :return: None
        """
        if backend in self._items:
            return
        prog_ids = _backend_prog_ids(backend)
        if not prog_ids:
            return
        self._ensure_com_initialized()
        try:
            import win32com.client
        except Exception as import_error:
            logger.warning("PPT COM 预热不可用：%s", import_error)
            return
        last_error: BaseException | None = None
        for prog_id in prog_ids:
            try:
                app = win32com.client.DispatchEx(prog_id)
                _minimize_app_window(app)
                self._items[backend] = PreheatedPptApplication(backend, app, prog_id)
                logger.info("PPT 后端已预热：backend=%s, prog_id=%s", backend, prog_id)
                return
            except BaseException as dispatch_error:
                last_error = dispatch_error
        logger.warning("PPT 后端预热失败：backend=%s, error=%s", backend, last_error)

    def preheat_source(self, backend: str, source_id: int, uri: str) -> None:
        """
        文件级预热指定 PPT 源：启动 COM 应用并预打开 Presentation。
        :param backend: powerpoint 或 wps
        :param source_id: 媒体源 ID
        :param uri: PPT 文件路径
        :return: None
        """
        if source_id <= 0 or not uri:
            return
        self.preheat(backend)
        item = self._items.pop(backend, None)
        if item is None:
            return
        try:
            presentation = _open_presentation(item.app, uri)
            _mark_presentation_clean(presentation)
        except Exception as open_error:
            logger.warning("PPT 文件级预热失败：backend=%s, source_id=%d, error=%s", backend, source_id, open_error)
            self._items[backend] = item
            return
        existing = self._items.pop(_source_key(backend, source_id, uri), None)
        if existing is not None and existing.presentation is not presentation:
            _close_presentation(existing.presentation)
            if existing.app is not item.app:
                quit_ppt_app(existing.app)
        self._items[_source_key(backend, source_id, uri)] = PreheatedPptApplication(
            backend,
            item.app,
            item.prog_id,
            source_id=source_id,
            uri=uri,
            presentation=presentation,
        )
        logger.info("PPT 文件已预热：backend=%s, source_id=%d", backend, source_id)

    def take(self, backend: str, source_id: int = 0, uri: str = "") -> PreheatedPptApplication | None:
        """
        取出指定后端预热应用。
        :param backend: PPT 后端
        :param source_id: 可选媒体源 ID，用于取出文件级预热项
        :param uri: 可选文件路径，用于取出文件级预热项
        :return: 预热应用或 None
        """
        if source_id > 0 and uri:
            item = self._items.pop(_source_key(backend, source_id, uri), None)
            if item is not None:
                return item
        return self._items.pop(backend, None)

    def return_item(self, item: PreheatedPptApplication) -> None:
        """
        归还预热应用。
        :param item: 预热应用
        :return: None
        """
        _close_presentation(item.presentation)
        item.source_id = 0
        item.uri = ""
        item.presentation = None
        existing = self._items.pop(item.backend, None)
        if existing is not None:
            _dispose_item(existing, quit_app=existing.app is not item.app)
        self._items[item.backend] = item

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
    尽力退出 PowerPoint/WPS 应用。
    :param app: COM Application 对象
    :return: None
    """
    try:
        app.Quit()
    except Exception:
        pass


def _backend_prog_ids(backend: str) -> tuple[str, ...]:
    """
    返回指定后端候选 ProgID。
    :param backend: PPT 后端
    :return: ProgID 元组
    """
    if backend == PPT_BACKEND_POWERPOINT:
        return tuple(POWERPOINT_COM_PROG_IDS)
    if backend == PPT_BACKEND_WPS:
        return tuple(WPS_COM_PROG_IDS)
    return ()


def _minimize_app_window(app: object) -> None:
    """
    预热应用后尽量最小化编辑窗口。
    :param app: COM Application 对象
    :return: None
    """
    try:
        app.WindowState = 2
    except Exception:
        pass


def _open_presentation(app: object, uri: str) -> object:
    """
    以无编辑窗口方式预打开演示文稿。
    :param app: COM Application 对象
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
        quit_ppt_app(item.app)


def _source_key(backend: str, source_id: int, uri: str) -> str:
    """
    构造文件级预热项键。
    :param backend: PPT 后端
    :param source_id: 媒体源 ID
    :param uri: 文件路径
    :return: 字典键
    """
    return f"{backend}:{source_id}:{uri}"


__all__ = [
    "PptApplicationPreheater",
    "quit_ppt_app",
]
