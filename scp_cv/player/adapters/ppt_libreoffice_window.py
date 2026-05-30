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
import time
from typing import Optional

from scp_cv.player.adapters.ppt_window import (
    detach_slideshow_window,
    embed_slideshow_window,
    resize_slideshow_window,
)

LIBREOFFICE_FRAME_CLASS_NAME = "SALFRAME"
LIBREOFFICE_SUBFRAME_CLASS_NAME = "SALSUBFRAME"
LIBREOFFICE_TEMP_SUBFRAME_CLASS_NAME = "SALTMPSUBFRAME"
LIBREOFFICE_SLIDESHOW_CLASS_NAMES = frozenset(
    {
        LIBREOFFICE_FRAME_CLASS_NAME,
        LIBREOFFICE_SUBFRAME_CLASS_NAME,
        LIBREOFFICE_TEMP_SUBFRAME_CLASS_NAME,
    }
)


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
    timeout_seconds: float = 8.0,
    poll_interval_seconds: float = 0.1,
    warn_on_failure: bool = True,
) -> int:
    """
    查找本次 LibreOffice 放映新增的 HWND。
    :param logger: 适配器日志器
    :param existing_hwnds: 启动放映前已存在的候选 HWND
    :param process_id: soffice 进程 ID；传入时优先过滤到当前实例
    :param timeout_seconds: 最长等待秒数，LibreOffice 放映窗口常在控制器返回后才变为可见
    :param poll_interval_seconds: 轮询间隔秒数
    :param warn_on_failure: 找不到窗口时是否记录 warning
    :return: 本次放映窗口句柄，无法确定时返回 0
    """
    try:
        import win32gui
    except Exception as import_error:
        logger.warning("Win32 模块不可用，无法查找 LibreOffice 放映窗口：%s", import_error)
        return 0

    deadline = time.monotonic() + max(0.1, timeout_seconds)
    selected_hwnd = 0
    last_matched_hwnds: list[int] = []
    excluded_hwnds = existing_hwnds or set()

    while time.monotonic() < deadline:
        selected_hwnd, last_matched_hwnds = _find_visible_libreoffice_hwnd(
            win32gui,
            logger,
            excluded_hwnds,
            process_id,
        )
        if selected_hwnd:
            return selected_hwnd
        time.sleep(max(0.02, poll_interval_seconds))

    if not last_matched_hwnds:
        if not warn_on_failure:
            return 0
        logger.warning("未能找到 LibreOffice 放映窗口")
        return 0
    if not warn_on_failure:
        return 0
    logger.warning("找到多个 LibreOffice 候选窗口，无法唯一确定：%s", last_matched_hwnds)
    return 0


def _find_visible_libreoffice_hwnd(
    win32gui: object,
    logger: logging.Logger,
    excluded_hwnds: set[int],
    process_id: Optional[int],
) -> tuple[int, list[int]]:
    """
    枚举当前可见 LibreOffice 放映候选窗口。
    :param win32gui: win32gui 模块或测试替身
    :param logger: 适配器日志器
    :param excluded_hwnds: 启动放映前已有窗口集合
    :param process_id: soffice 进程 ID；传入时优先过滤到当前实例
    :return: (选中的 HWND，候选列表)
    """
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
        return 0, matched_hwnds
    if len(matched_hwnds) == 1:
        logger.debug("通过枚举窗口找到 LibreOffice 放映 HWND=%d", matched_hwnds[0])
        return matched_hwnds[0], matched_hwnds
    selected_hwnd = _select_best_libreoffice_hwnd(win32gui, matched_hwnds)
    if selected_hwnd:
        logger.debug(
            "找到多个 LibreOffice 候选窗口，选择最大窗口 HWND=%d，候选=%s",
            selected_hwnd,
            matched_hwnds,
        )
        return selected_hwnd, matched_hwnds
    return 0, matched_hwnds


def _select_best_libreoffice_hwnd(win32gui: object, hwnds: list[int]) -> int:
    """
    从 LibreOffice 候选窗口中选择最可能的真实放映画面。
    :param win32gui: win32gui 模块或测试替身
    :param hwnds: 候选 HWND 列表
    :return: 选中的 HWND；无法选择时返回 0
    """
    for class_name in (
        LIBREOFFICE_TEMP_SUBFRAME_CLASS_NAME,
        LIBREOFFICE_SUBFRAME_CLASS_NAME,
    ):
        class_hwnds = _filter_hwnds_by_class_name(win32gui, hwnds, class_name)
        selected_hwnd = _largest_window(win32gui, class_hwnds)
        if selected_hwnd:
            return selected_hwnd
    return _largest_window(win32gui, hwnds)


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
    if _is_libreoffice_impress_editor_window(win32gui, hwnd):
        return False
    if process_id is None:
        return True
    try:
        import win32process

        _, window_process_id = win32process.GetWindowThreadProcessId(hwnd)
    except Exception:
        return True
    return int(window_process_id) == int(process_id)


def _is_libreoffice_impress_editor_window(win32gui: object, hwnd: int) -> bool:
    """
    判断 HWND 是否为 LibreOffice Impress 编辑主窗口。
    :param win32gui: win32gui 模块或测试替身
    :param hwnd: 窗口句柄
    :return: True 表示编辑窗口，不应作为放映窗口
    """
    try:
        title = win32gui.GetWindowText(hwnd)  # type: ignore[attr-defined]
    except Exception:
        return False
    normalized_title = str(title).casefold()
    if not normalized_title or "libreoffice impress" not in normalized_title:
        return False
    return not _looks_like_slideshow_title(normalized_title)


def _looks_like_slideshow_title(normalized_title: str) -> bool:
    """
    判断窗口标题是否明显指向放映窗口。
    :param normalized_title: 已 casefold 的窗口标题
    :return: True 表示标题更像放映窗口
    """
    slideshow_prefixes = (
        "slide show -",
        "slide show:",
        "slide show：",
        "slideshow -",
        "slideshow:",
        "slideshow：",
        "幻灯片放映 -",
        "幻灯片放映:",
        "幻灯片放映：",
    )
    return any(normalized_title.startswith(prefix) for prefix in slideshow_prefixes)


def _filter_hwnds_by_class_name(
    win32gui: object,
    hwnds: list[int],
    class_name: str,
) -> list[int]:
    """
    按 Win32 class name 过滤候选 HWND。
    :param win32gui: win32gui 模块或测试替身
    :param hwnds: 候选 HWND 列表
    :param class_name: 目标 class name
    :return: 匹配目标 class name 的 HWND 列表
    """
    filtered_hwnds: list[int] = []
    for hwnd in hwnds:
        try:
            if win32gui.GetClassName(hwnd) == class_name:  # type: ignore[attr-defined]
                filtered_hwnds.append(hwnd)
        except Exception:
            continue
    return filtered_hwnds


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
