#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
播放器 Win32 顶层窗口清理工具。
@Project : SCP-cv
@File : window_cleanup.py
@Author : Qintsg
@Date : 2026-06-08
'''
from __future__ import annotations

import logging
from collections.abc import Iterable

logger = logging.getLogger(__name__)
_POWERPOINT_SLIDESHOW_CLASS_NAMES = frozenset({
    "screenClass",
    "paneClassDC",
    "PPTFrameClass",
})
_POWERPOINT_SLIDESHOW_TITLE_MARKERS = (
    "slide show",
    "slideshow",
    "幻灯片放映",
)


def minimize_unprotected_top_level_windows(protected_hwnds: Iterable[int]) -> list[int]:
    """
    最小化除受保护 HWND 外的所有可见顶层窗口。

    :param protected_hwnds: 需要保留可见状态的顶层窗口句柄集合
    :return: 已尝试最小化的 HWND 列表
    """
    try:
        import win32con
        import win32gui
    except Exception as import_error:
        logger.debug("Win32 模块不可用，跳过窗口最小化：%s", import_error)
        return []

    protected_roots = _normalized_protected_roots(
        protected_hwnds,
        win32gui=win32gui,
        win32con=win32con,
    )
    if not protected_roots:
        return []

    minimized: list[int] = []

    def enum_callback(hwnd: int, _extra: object) -> bool:
        root_hwnd = _root_window(win32gui, win32con, int(hwnd))
        if root_hwnd in protected_roots:
            return True
        if _is_powerpoint_slideshow_window(win32gui, int(hwnd), root_hwnd):
            return True
        if not _is_minimizable_top_level_window(win32gui, win32con, int(hwnd), root_hwnd):
            return True
        try:
            win32gui.ShowWindow(root_hwnd, win32con.SW_MINIMIZE)
            minimized.append(root_hwnd)
        except Exception as minimize_error:
            logger.debug("最小化窗口失败：hwnd=%s, error=%s", root_hwnd, minimize_error)
        return True

    try:
        win32gui.EnumWindows(enum_callback, None)
    except Exception as enum_error:
        logger.debug("枚举顶层窗口失败：%s", enum_error)
    if minimized:
        logger.info("PPT 放映期间已最小化未保护窗口：%s", minimized)
    return minimized


def _is_powerpoint_slideshow_window(win32gui: object, hwnd: int, root_hwnd: int) -> bool:
    """
    判断窗口是否为 PowerPoint 放映窗口；放映窗口即使未在保护列表中也不应被清理。

    :param win32gui: win32gui 模块或测试替身
    :param hwnd: 枚举到的窗口句柄
    :param root_hwnd: 根窗口句柄
    :return: True 表示应保留该 PowerPoint 放映窗口
    """
    if hwnd != root_hwnd:
        return False
    try:
        if not win32gui.IsWindowVisible(root_hwnd):  # type: ignore[attr-defined]
            return False
    except Exception:
        return False
    try:
        class_name = str(win32gui.GetClassName(root_hwnd))  # type: ignore[attr-defined]
    except Exception:
        class_name = ""
    if class_name not in _POWERPOINT_SLIDESHOW_CLASS_NAMES:
        return False
    try:
        title = str(win32gui.GetWindowText(root_hwnd))  # type: ignore[attr-defined]
    except Exception:
        title = ""
    normalized_title = title.casefold()
    if not normalized_title:
        return True
    return any(marker in normalized_title for marker in _POWERPOINT_SLIDESHOW_TITLE_MARKERS)


def _normalized_protected_roots(
    protected_hwnds: Iterable[int],
    win32gui: object | None = None,
    win32con: object | None = None,
) -> set[int]:
    """
    归一化受保护窗口句柄。

    :param protected_hwnds: 原始 HWND 集合
    :param win32gui: 可选 win32gui 模块；传入时将子窗口归一到顶层根窗口
    :param win32con: 可选 win32con 模块；传入时将子窗口归一到顶层根窗口
    :return: 去除 0 后的整数集合
    """
    normalized_roots: set[int] = set()
    for raw_hwnd in protected_hwnds:
        try:
            hwnd = int(raw_hwnd or 0)
        except (TypeError, ValueError):
            continue
        if hwnd <= 0:
            continue
        if win32gui is not None and win32con is not None:
            hwnd = _root_window(win32gui, win32con, hwnd)
        normalized_roots.add(hwnd)
    return normalized_roots


def _root_window(win32gui: object, win32con: object, hwnd: int) -> int:
    """
    获取窗口根 HWND。

    :param win32gui: win32gui 模块或测试替身
    :param win32con: win32con 模块或测试替身
    :param hwnd: 原始窗口句柄
    :return: 根窗口句柄
    """
    try:
        return int(win32gui.GetAncestor(hwnd, getattr(win32con, "GA_ROOT", 2)))  # type: ignore[attr-defined]
    except Exception:
        return int(hwnd)


def _is_minimizable_top_level_window(win32gui: object, win32con: object, hwnd: int, root_hwnd: int) -> bool:
    """
    判断窗口是否应被最小化。

    :param win32gui: win32gui 模块或测试替身
    :param win32con: win32con 模块或测试替身
    :param hwnd: 枚举到的窗口句柄
    :param root_hwnd: 根窗口句柄
    :return: True 表示可最小化
    """
    if hwnd != root_hwnd:
        return False
    try:
        if not win32gui.IsWindowVisible(root_hwnd):  # type: ignore[attr-defined]
            return False
    except Exception:
        return False
    try:
        if win32gui.IsIconic(root_hwnd):  # type: ignore[attr-defined]
            return False
    except Exception:
        pass
    try:
        owner = win32gui.GetWindow(root_hwnd, getattr(win32con, "GW_OWNER", 4))  # type: ignore[attr-defined]
        if owner:
            return False
    except Exception:
        pass
    return True


__all__ = ["minimize_unprotected_top_level_windows"]
