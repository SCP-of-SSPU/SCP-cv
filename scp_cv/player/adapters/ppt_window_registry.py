#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PPT 嵌入窗口归属注册表，避免已嵌入 HWND 被后续放映误认领。
@Project : SCP-cv
@File : ppt_window_registry.py
@Author : Qintsg
@Date : 2026-06-10
'''
from __future__ import annotations

EMBEDDED_SLIDESHOW_PROP = "SCP_CV_EMBEDDED_PPT_SLIDESHOW"
_EMBEDDED_SLIDESHOW_HWNDS: set[int] = set()


def mark_embedded_slideshow_window(ppt_hwnd: int, parent_hwnd: int) -> None:
    """
    给已嵌入的 PPT 放映窗口加跨进程 Win32 标记。
    :param ppt_hwnd: PPT 放映窗口句柄
    :param parent_hwnd: PySide 嵌入容器句柄
    :return: None
    """
    if ppt_hwnd == 0:
        return
    _EMBEDDED_SLIDESHOW_HWNDS.add(int(ppt_hwnd))
    try:
        import win32gui

        set_prop = getattr(win32gui, "SetProp", None)
        if callable(set_prop):
            set_prop(ppt_hwnd, EMBEDDED_SLIDESHOW_PROP, int(parent_hwnd or 1))
    except Exception:
        return


def unmark_embedded_slideshow_window(ppt_hwnd: int) -> None:
    """
    移除 PPT 放映窗口嵌入标记，供测试或诊断性解除嵌入时使用。
    :param ppt_hwnd: PPT 放映窗口句柄
    :return: None
    """
    if ppt_hwnd == 0:
        return
    _EMBEDDED_SLIDESHOW_HWNDS.discard(int(ppt_hwnd))
    try:
        import win32gui

        remove_prop = getattr(win32gui, "RemoveProp", None)
        if callable(remove_prop):
            remove_prop(ppt_hwnd, EMBEDDED_SLIDESHOW_PROP)
    except Exception:
        return


def has_embedded_slideshow_marker(win32gui: object, hwnd: int) -> bool:
    """
    判断 HWND 是否已经被本系统嵌入到某个 PySide 容器。
    :param win32gui: win32gui 模块或测试替身
    :param hwnd: 待判断窗口句柄
    :return: True 表示该 HWND 已归属播放器容器
    """
    get_prop = getattr(win32gui, "GetProp", None)
    if not callable(get_prop):
        return int(hwnd) in _EMBEDDED_SLIDESHOW_HWNDS
    try:
        marked = bool(get_prop(hwnd, EMBEDDED_SLIDESHOW_PROP))
    except Exception:
        return int(hwnd) in _EMBEDDED_SLIDESHOW_HWNDS
    if not marked:
        _EMBEDDED_SLIDESHOW_HWNDS.discard(int(hwnd))
    return marked


__all__ = [
    "EMBEDDED_SLIDESHOW_PROP",
    "has_embedded_slideshow_marker",
    "mark_embedded_slideshow_window",
    "unmark_embedded_slideshow_window",
]
