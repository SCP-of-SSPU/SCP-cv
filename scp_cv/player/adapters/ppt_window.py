#!/user/bin/env python
# -*- coding: UTF-8 -*-
"""
PPT 放映窗口 Win32 操作工具，封装 HWND 查找、嵌入和尺寸同步。
@Project : SCP-cv
@File : ppt_window.py
@Author : Qintsg
@Date : 2026-05-02
"""

from __future__ import annotations

import logging
import time
from collections.abc import Iterable
from typing import Optional

from scp_cv.player.adapters.ppt_constants import PP_SLIDE_SHOW_WINDOW

SLIDESHOW_CLASS_NAMES = frozenset({"screenClass", "paneClassDC", "PPTFrameClass"})
_SLIDESHOW_TITLE_PREFIXES = (
    "powerpoint slide show -",
    "powerpoint slide show:",
    "powerpoint slide show：",
    "powerpoint 幻灯片放映 -",
    "powerpoint 幻灯片放映:",
    "powerpoint 幻灯片放映：",
    "powerpoint 幻灯片放映—",
    "powerpoint 幻灯片放映–",
    "powerpoint幻灯片放映 -",
    "powerpoint幻灯片放映:",
    "powerpoint幻灯片放映：",
    "powerpoint幻灯片放映—",
    "powerpoint幻灯片放映–",
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
_EDITOR_TITLE_KEYWORDS = (
    "powerpoint",
)


def configure_windowed_slideshow(
    settings: object, start_slide: int, total_slides: int
) -> object:
    """
    配置 PPT 为窗口化放映，允许多个播放器窗口同时嵌入各自 PPT。
    :param settings: PPT SlideShowSettings COM 对象
    :param start_slide: 起始页码
    :param total_slides: 总页数
    :return: 原始 settings 对象，便于调用方继续 Run
    """
    settings.ShowType = PP_SLIDE_SHOW_WINDOW
    settings.StartingSlide = max(1, min(start_slide, total_slides or 1))
    settings.EndingSlide = total_slides
    return settings


def snapshot_slideshow_hwnds(
    logger: Optional[logging.Logger] = None,
    class_names: Optional[Iterable[str]] = None,
    process_id: Optional[int] = None,
) -> set[int]:
    """
    获取当前系统中可见的 PPT 放映窗口句柄快照。
    :param logger: 可选日志器；导入 Win32 失败时记录调试信息
    :param class_names: 可识别为放映窗口的 Win32 class name 集合
    :param process_id: 可选进程 ID；传入时只记录当前 PowerPoint 实例窗口
    :return: 可见放映窗口 HWND 集合
    """
    try:
        import win32gui
    except Exception as import_error:
        if logger is not None:
            logger.debug("Win32 模块不可用，跳过放映窗口快照：%s", import_error)
        return set()

    slideshow_hwnds: set[int] = set()
    selected_class_names = _selected_slideshow_class_names(class_names)

    def enum_callback(hwnd: int, _extra: object) -> bool:
        if _is_candidate_slideshow_window(
            win32gui,
            hwnd,
            selected_class_names,
            process_id,
        ):
            slideshow_hwnds.add(int(hwnd))
        return True

    try:
        win32gui.EnumWindows(enum_callback, None)
    except Exception as enum_error:
        if logger is not None:
            logger.debug("枚举 PPT 放映窗口快照失败：%s", enum_error)
    return slideshow_hwnds


def find_slideshow_hwnd(
    slideshow_window: Optional[object],
    logger: logging.Logger,
    existing_hwnds: Optional[set[int]] = None,
    class_names: Optional[Iterable[str]] = None,
    timeout_seconds: float = 0.0,
    poll_interval_seconds: float = 0.1,
    process_id: Optional[int] = None,
    allow_existing_when_unique: bool = False,
) -> int:
    """
    查找 PPT 放映窗口的 HWND。
    :param slideshow_window: COM SlideShowWindow 对象
    :param logger: 适配器日志器
    :param existing_hwnds: 启动本次放映前已存在的放映 HWND，用于排除其他窗口
    :param class_names: 可识别为放映窗口的 Win32 class name 集合
    :param timeout_seconds: 等待异步创建窗口的最长秒数；0 表示只查一次
    :param poll_interval_seconds: 重试间隔秒数
    :param process_id: 可选进程 ID；用于确认候选窗口属于当前 PowerPoint 实例
    :param allow_existing_when_unique: 进程可确认时，允许使用启动前已存在的唯一候选窗口
    :return: 本次放映窗口句柄，无法唯一确定时返回 0
    """
    try:
        import win32gui
    except Exception as import_error:
        win32gui = None
        logger.debug("Win32 模块不可用，将仅通过 COM 查找 PPT 放映窗口：%s", import_error)

    deadline = time.monotonic() + max(0.0, timeout_seconds)
    retry_interval = max(0.01, poll_interval_seconds)
    matched_hwnds: list[int] = []
    while True:
        ppt_hwnd = _read_com_slideshow_hwnd(slideshow_window, logger)
        if ppt_hwnd != 0:
            return ppt_hwnd

        if win32gui is not None:
            matched_hwnds = _find_matching_slideshow_hwnds(
                win32gui,
                logger,
                existing_hwnds,
                class_names,
                process_id=process_id,
            )
            if len(matched_hwnds) == 1:
                logger.debug("通过枚举窗口找到本次放映 HWND=%d", matched_hwnds[0])
                return matched_hwnds[0]
            if len(matched_hwnds) > 1:
                break

        now = time.monotonic()
        if now >= deadline:
            break
        time.sleep(min(retry_interval, deadline - now))

    if win32gui is not None and allow_existing_when_unique and process_id is not None:
        scoped_hwnds = _find_matching_slideshow_hwnds(
            win32gui,
            logger,
            existing_hwnds=None,
            class_names=class_names,
            process_id=process_id,
        )
        if len(scoped_hwnds) == 1:
            logger.debug(
                "使用当前进程中已存在的唯一放映 HWND=%d",
                scoped_hwnds[0],
            )
            return scoped_hwnds[0]
        selected_hwnd = _largest_window(win32gui, scoped_hwnds)
        if selected_hwnd:
            logger.debug(
                "当前进程存在多个候选放映窗口，选择最大窗口 HWND=%d，候选=%s",
                selected_hwnd,
                scoped_hwnds,
            )
            return selected_hwnd

    if win32gui is not None and allow_existing_when_unique and process_id is None:
        all_hwnds = _find_matching_slideshow_hwnds(
            win32gui,
            logger,
            existing_hwnds=None,
            class_names=class_names,
        )
        if len(all_hwnds) == 1:
            logger.debug(
                "进程 ID 不可用，使用系统中唯一放映 HWND=%d",
                all_hwnds[0],
            )
            return all_hwnds[0]

    if win32gui is None:
        logger.warning("Win32 模块不可用，无法查找 PPT 放映窗口")
        return 0

    if len(matched_hwnds) > 1:
        logger.warning(
            "找到多个候选 PPT 放映窗口，无法唯一确定：%s", matched_hwnds
        )
    else:
        logger.warning("未能找到 PPT 放映窗口")
    return 0


def _read_com_slideshow_hwnd(
    slideshow_window: Optional[object],
    logger: logging.Logger,
) -> int:
    """
    从 COM SlideShowWindow 读取 HWND。
    :param slideshow_window: COM SlideShowWindow 对象
    :param logger: 日志器
    :return: 有效 HWND；读取失败返回 0
    """
    if slideshow_window is None:
        return 0
    try:
        ppt_hwnd = slideshow_window.HWND
        if ppt_hwnd and ppt_hwnd > 0:
            logger.debug("通过 COM 获取到放映 HWND=%d", ppt_hwnd)
            return int(ppt_hwnd)
    except Exception as com_error:
        logger.debug("COM 获取 HWND 失败：%s，尝试枚举窗口", com_error)
    return 0


def _find_matching_slideshow_hwnds(
    win32gui: object,
    logger: logging.Logger,
    existing_hwnds: Optional[set[int]] = None,
    class_names: Optional[Iterable[str]] = None,
    process_id: Optional[int] = None,
) -> list[int]:
    """
    枚举匹配当前放映 class 且不属于启动前快照的窗口。
    :param win32gui: win32gui 模块或测试替身
    :param logger: 日志器
    :param existing_hwnds: 启动前已存在的 HWND
    :param class_names: 放映窗口 class name 候选集合
    :param process_id: 可选进程 ID；传入时只匹配当前 PowerPoint 实例窗口
    :return: 候选 HWND 列表
    """
    excluded_hwnds = existing_hwnds or set()
    matched_hwnds: list[int] = []
    selected_class_names = _selected_slideshow_class_names(class_names)

    def enum_callback(hwnd: int, _extra: object) -> bool:
        if int(hwnd) not in excluded_hwnds and _is_candidate_slideshow_window(
            win32gui,
            hwnd,
            selected_class_names,
            process_id,
        ):
            matched_hwnds.append(int(hwnd))
        return True

    try:
        win32gui.EnumWindows(enum_callback, None)
    except Exception as enum_error:
        logger.debug("枚举 PPT 放映窗口失败：%s", enum_error)
    return matched_hwnds


def _selected_slideshow_class_names(
    class_names: Optional[Iterable[str]] = None,
) -> frozenset[str]:
    """
    解析调用方指定的 PPT 放映窗口 class name 候选集合。
    :param class_names: 调用方传入的候选集合；为空时使用 PowerPoint 默认集合
    :return: 可用于匹配窗口的 class name 集合
    """
    if class_names is None:
        return SLIDESHOW_CLASS_NAMES
    return frozenset(class_names)


def _is_candidate_slideshow_window(
    win32gui: object,
    hwnd: int,
    selected_class_names: frozenset[str],
    process_id: Optional[int],
) -> bool:
    """
    判断 Win32 窗口是否可作为 PowerPoint 放映窗口候选。
    :param win32gui: win32gui 模块或测试替身
    :param hwnd: 窗口句柄
    :param selected_class_names: 可接受的窗口 class name 集合
    :param process_id: 可选进程 ID
    :return: True 表示可作为放映窗口候选
    """
    if not win32gui.IsWindowVisible(hwnd):
        return False
    class_name = win32gui.GetClassName(hwnd)
    if class_name not in selected_class_names:
        return False
    if _is_presentation_editor_window(win32gui, hwnd):
        return False
    return _window_belongs_to_process(hwnd, process_id)


def _is_presentation_editor_window(win32gui: object, hwnd: int) -> bool:
    """
    通过窗口标题排除 PowerPoint 编辑主窗口。
    :param win32gui: win32gui 模块或测试替身
    :param hwnd: 窗口句柄
    :return: True 表示该窗口更像编辑器而非放映窗口
    """
    try:
        title = str(win32gui.GetWindowText(hwnd))  # type: ignore[attr-defined]
    except Exception:
        return False
    normalized_title = title.casefold().strip()
    if not normalized_title:
        return False
    if _looks_like_slideshow_title(normalized_title):
        return False
    return any(keyword in normalized_title for keyword in _EDITOR_TITLE_KEYWORDS)


def _looks_like_slideshow_title(normalized_title: str) -> bool:
    """
    判断窗口标题是否使用明确的放映窗口标题格式。
    :param normalized_title: 已 casefold 和 strip 的窗口标题
    :return: True 表示标题明显属于放映窗口
    """
    return any(
        normalized_title.startswith(prefix) for prefix in _SLIDESHOW_TITLE_PREFIXES
    )


def _window_belongs_to_process(hwnd: int, process_id: Optional[int]) -> bool:
    """
    判断窗口是否属于指定进程。
    :param hwnd: 窗口句柄
    :param process_id: 目标进程 ID；为空时不做过滤
    :return: True 表示可作为当前进程候选
    """
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
    从候选窗口中选择面积最大的窗口。
    :param win32gui: win32gui 模块或测试替身
    :param hwnds: 候选 HWND 列表
    :return: 最大窗口 HWND；无法读取尺寸时返回 0
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
            best_hwnd = int(hwnd)
    return best_hwnd


def embed_slideshow_window(ppt_hwnd: int, parent_hwnd: int) -> None:
    """
    将 PPT 放映窗口嵌入播放器的原生窗口。
    :param ppt_hwnd: PPT 放映窗口句柄
    :param parent_hwnd: PySide 播放器窗口句柄
    :return: None
    """
    import win32con
    import win32gui

    original_style = win32gui.GetWindowLong(ppt_hwnd, win32con.GWL_STYLE)
    embedded_style = original_style & ~win32con.WS_OVERLAPPEDWINDOW | win32con.WS_CHILD
    win32gui.SetWindowLong(ppt_hwnd, win32con.GWL_STYLE, embedded_style)

    extended_style = win32gui.GetWindowLong(ppt_hwnd, win32con.GWL_EXSTYLE)
    extended_style &= ~win32con.WS_EX_TOPMOST
    extended_style &= ~win32con.WS_EX_APPWINDOW
    win32gui.SetWindowLong(ppt_hwnd, win32con.GWL_EXSTYLE, extended_style)
    win32gui.SetParent(ppt_hwnd, parent_hwnd)


def resize_slideshow_window(ppt_hwnd: int, parent_hwnd: int) -> tuple[int, int]:
    """
    调整 PPT 放映窗口大小以填满播放器容器。
    :param ppt_hwnd: PPT 放映窗口句柄
    :param parent_hwnd: PySide 播放器窗口句柄
    :return: 调整后的宽高
    """
    import win32con
    import win32gui

    container_rect = win32gui.GetClientRect(parent_hwnd)
    container_width = container_rect[2] - container_rect[0]
    container_height = container_rect[3] - container_rect[1]
    win32gui.SetWindowPos(
        ppt_hwnd,
        win32con.HWND_TOP,
        0,
        0,
        container_width,
        container_height,
        win32con.SWP_NOZORDER | win32con.SWP_SHOWWINDOW,
    )
    return container_width, container_height


def detach_slideshow_window(ppt_hwnd: int) -> None:
    """
    解除 PPT 放映窗口和播放器窗口的父子关系。
    :param ppt_hwnd: PPT 放映窗口句柄
    :return: None
    """
    if ppt_hwnd == 0:
        return
    import win32gui

    win32gui.SetParent(ppt_hwnd, 0)
