#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
LibreOffice Impress 放映窗口 Win32 操作工具，负责 HWND 查找、嵌入和尺寸同步。
@Project : SCP-cv
@File : ppt_libreoffice_window.py
@Author : Qintsg
@Date : 2026-05-26
'''
from __future__ import annotations

import logging
from typing import Optional

from scp_cv.player.adapters.ppt_window import (
    detach_slideshow_window,
    embed_slideshow_window,
    resize_slideshow_window,
)

LIBREOFFICE_SLIDESHOW_CLASS_NAMES = frozenset({"SALFRAME", "SALSUBFRAME"})


def snapshot_libreoffice_hwnds(
    logger: Optional[logging.Logger] = None,
    process_id: Optional[int] = None,
) -> set[int]:
    """
    获取当前可见 LibreOffice 放映候选窗口快照。
    :param logger: 可选日志器
    :param process_id: 可选 soffice 进程 ID；传入时只记录该进程窗口
    :return: HWND 集合
    """
    try:
        import win32gui
    except Exception as import_error:
        if logger is not None:
            logger.debug("Win32 模块不可用，跳过 LibreOffice 窗口快照：%s", import_error)
        return set()

    slideshow_hwnds: set[int] = set()

    def enum_callback(hwnd: int, _extra: object) -> bool:
        if _is_libreoffice_window(win32gui, hwnd, process_id):
            slideshow_hwnds.add(int(hwnd))
        return True

    try:
        win32gui.EnumWindows(enum_callback, None)
    except Exception as enum_error:
        if logger is not None:
            logger.debug("枚举 LibreOffice 窗口快照失败：%s", enum_error)
    return slideshow_hwnds


def find_libreoffice_slideshow_hwnd(
    logger: logging.Logger,
    existing_hwnds: Optional[set[int]] = None,
    process_id: Optional[int] = None,
) -> int:
    """
    查找本次 LibreOffice 放映新增的 HWND。
    :param logger: 适配器日志器
    :param existing_hwnds: 启动放映前已存在的候选 HWND
    :param process_id: soffice 进程 ID；传入时优先过滤到当前实例
    :return: 本次放映窗口句柄，无法确定时返回 0
    """
    try:
        import win32gui
    except Exception as import_error:
        logger.warning("Win32 模块不可用，无法查找 LibreOffice 放映窗口：%s", import_error)
        return 0

    excluded_hwnds = existing_hwnds or set()
    matched_hwnds: list[int] = []

    def enum_callback(hwnd: int, _extra: object) -> bool:
        if int(hwnd) not in excluded_hwnds and _is_libreoffice_window(
            win32gui,
            hwnd,
            process_id,
        ):
            matched_hwnds.append(int(hwnd))
        return True

    try:
        win32gui.EnumWindows(enum_callback, None)
    except Exception as enum_error:
        logger.debug("枚举 LibreOffice 放映窗口失败：%s", enum_error)

    if not matched_hwnds:
        logger.warning("未能找到 LibreOffice 放映窗口")
        return 0
    if len(matched_hwnds) == 1:
        logger.debug("通过枚举窗口找到 LibreOffice 放映 HWND=%d", matched_hwnds[0])
        return matched_hwnds[0]
    selected_hwnd = _largest_window(win32gui, matched_hwnds)
    if selected_hwnd:
        logger.debug(
            "找到多个 LibreOffice 候选窗口，选择最大窗口 HWND=%d，候选=%s",
            selected_hwnd,
            matched_hwnds,
        )
        return selected_hwnd
    logger.warning("找到多个 LibreOffice 候选窗口，无法唯一确定：%s", matched_hwnds)
    return 0


def _is_libreoffice_window(
    win32gui: object,
    hwnd: int,
    process_id: Optional[int],
) -> bool:
    """
    判断窗口是否属于 LibreOffice 放映候选。
    :param win32gui: win32gui 模块或测试替身
    :param hwnd: 窗口句柄
    :param process_id: 可选进程 ID 过滤条件
    :return: True 表示可作为候选窗口
    """
    try:
        if not win32gui.IsWindowVisible(hwnd):  # type: ignore[attr-defined]
            return False
        class_name = win32gui.GetClassName(hwnd)  # type: ignore[attr-defined]
    except Exception:
        return False
    if class_name not in LIBREOFFICE_SLIDESHOW_CLASS_NAMES:
        return False
    if process_id is None:
        return True
    try:
        import win32process

        _, window_process_id = win32process.GetWindowThreadProcessId(hwnd)
    except Exception:
        return True
    return int(window_process_id) == int(process_id)


def _largest_window(win32gui: object, hwnds: list[int]) -> int:
    """
    从候选窗口中选择面积最大的可见窗口。
    :param win32gui: win32gui 模块或测试替身
    :param hwnds: 候选 HWND 列表
    :return: 面积最大的 HWND；无法读取尺寸时返回 0
    """
    best_hwnd = 0
    best_area = -1
    for hwnd in hwnds:
        try:
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)  # type: ignore[attr-defined]
        except Exception:
            continue
        area = max(0, right - left) * max(0, bottom - top)
        if area > best_area:
            best_area = area
            best_hwnd = hwnd
    return best_hwnd


__all__ = [
    "LIBREOFFICE_SLIDESHOW_CLASS_NAMES",
    "detach_slideshow_window",
    "embed_slideshow_window",
    "find_libreoffice_slideshow_hwnd",
    "resize_slideshow_window",
    "snapshot_libreoffice_hwnds",
]
