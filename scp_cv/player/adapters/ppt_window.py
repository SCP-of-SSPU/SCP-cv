#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PowerPoint 放映窗口 Win32 操作工具，封装 HWND 查找、嵌入和尺寸同步。
@Project : SCP-cv
@File : ppt_window.py
@Author : Qintsg
@Date : 2026-05-02
'''
from __future__ import annotations

import logging
from typing import Optional


def find_slideshow_hwnd(slideshow_window: Optional[object], logger: logging.Logger) -> int:
    """
    查找 PowerPoint 放映窗口的 HWND。
    :param slideshow_window: COM SlideShowWindow 对象
    :param logger: 适配器日志器
    :return: 放映窗口句柄，找不到返回 0
    """
    if slideshow_window is not None:
        try:
            ppt_hwnd = slideshow_window.HWND
            if ppt_hwnd and ppt_hwnd > 0:
                logger.debug("通过 COM 获取到放映 HWND=%d", ppt_hwnd)
                return int(ppt_hwnd)
        except Exception as com_error:
            logger.debug("COM 获取 HWND 失败：%s，尝试枚举窗口", com_error)

    import win32gui

    found_hwnd = 0
    slideshow_class_names = ["screenClass", "paneClassDC"]

    def enum_callback(hwnd: int, _extra: object) -> bool:
        nonlocal found_hwnd
        if win32gui.IsWindowVisible(hwnd):
            class_name = win32gui.GetClassName(hwnd)
            if class_name in slideshow_class_names:
                found_hwnd = hwnd
                return False
        return True

    try:
        win32gui.EnumWindows(enum_callback, None)
    except Exception:
        # EnumWindows 在回调返回 False 时会抛异常，属于停止枚举的正常路径。
        pass

    if found_hwnd > 0:
        logger.debug("通过枚举窗口找到放映 HWND=%d", found_hwnd)
    else:
        logger.warning("未能找到 PowerPoint 放映窗口")
    return found_hwnd


def embed_slideshow_window(ppt_hwnd: int, parent_hwnd: int) -> None:
    """
    将 PowerPoint 放映窗口嵌入播放器的原生窗口。
    :param ppt_hwnd: PowerPoint 放映窗口句柄
    :param parent_hwnd: PySide 播放器窗口句柄
    :return: None
    """
    import win32con
    import win32gui

    original_style = win32gui.GetWindowLong(ppt_hwnd, win32con.GWL_STYLE)
    embedded_style = (
        original_style
        & ~win32con.WS_OVERLAPPEDWINDOW
        | win32con.WS_CHILD
    )
    win32gui.SetWindowLong(ppt_hwnd, win32con.GWL_STYLE, embedded_style)

    extended_style = win32gui.GetWindowLong(ppt_hwnd, win32con.GWL_EXSTYLE)
    extended_style &= ~win32con.WS_EX_TOPMOST
    extended_style &= ~win32con.WS_EX_APPWINDOW
    win32gui.SetWindowLong(ppt_hwnd, win32con.GWL_EXSTYLE, extended_style)
    win32gui.SetParent(ppt_hwnd, parent_hwnd)


def resize_slideshow_window(ppt_hwnd: int, parent_hwnd: int) -> tuple[int, int]:
    """
    调整 PowerPoint 放映窗口大小以填满播放器容器。
    :param ppt_hwnd: PowerPoint 放映窗口句柄
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
    解除 PowerPoint 放映窗口和播放器窗口的父子关系。
    :param ppt_hwnd: PowerPoint 放映窗口句柄
    :return: None
    """
    if ppt_hwnd == 0:
        return
    import win32gui

    win32gui.SetParent(ppt_hwnd, 0)
