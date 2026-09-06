#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PPT 嵌入窗口归属注册表，避免已嵌入 HWND 被后续放映误认领，
并通过归属 token 防止旧适配器误关闭已被新放映复用的窗口。
@Project : SCP-cv
@File : ppt_window_registry.py
@Author : Qintsg
@Date : 2026-06-10
'''
from __future__ import annotations

EMBEDDED_SLIDESHOW_PROP = "SCP_CV_EMBEDDED_PPT_SLIDESHOW"
_EMBEDDED_SLIDESHOW_OWNERS: dict[int, int] = {}


def mark_embedded_slideshow_window(ppt_hwnd: int, owner_token: int) -> None:
    """
    给已嵌入的 PPT 放映窗口加跨进程 Win32 标记并记录归属 token。
    :param ppt_hwnd: PPT 放映窗口句柄
    :param owner_token: 归属适配器 token（非零）；同一窗口被复用时覆盖旧归属
    :return: None
    """
    if ppt_hwnd == 0:
        return
    normalized_token = int(owner_token or 1)
    _EMBEDDED_SLIDESHOW_OWNERS[int(ppt_hwnd)] = normalized_token
    try:
        import win32gui

        set_prop = getattr(win32gui, "SetProp", None)
        if callable(set_prop):
            set_prop(ppt_hwnd, EMBEDDED_SLIDESHOW_PROP, normalized_token)
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
    _EMBEDDED_SLIDESHOW_OWNERS.pop(int(ppt_hwnd), None)
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
    return read_embedded_slideshow_owner(win32gui, hwnd) != 0


def read_embedded_slideshow_owner(win32gui: object, hwnd: int) -> int:
    """
    读取嵌入窗口当前归属 token。
    :param win32gui: win32gui 模块或测试替身
    :param hwnd: 待判断窗口句柄
    :return: 归属 token；窗口未被嵌入时返回 0
    """
    get_prop = getattr(win32gui, "GetProp", None)
    if not callable(get_prop):
        return _EMBEDDED_SLIDESHOW_OWNERS.get(int(hwnd), 0)
    try:
        owner_token = int(get_prop(hwnd, EMBEDDED_SLIDESHOW_PROP) or 0)
    except Exception:
        return _EMBEDDED_SLIDESHOW_OWNERS.get(int(hwnd), 0)
    if owner_token == 0:
        _EMBEDDED_SLIDESHOW_OWNERS.pop(int(hwnd), None)
    return owner_token


__all__ = [
    "EMBEDDED_SLIDESHOW_PROP",
    "has_embedded_slideshow_marker",
    "mark_embedded_slideshow_window",
    "read_embedded_slideshow_owner",
    "unmark_embedded_slideshow_window",
]
