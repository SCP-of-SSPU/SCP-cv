#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PowerPoint 放映 HWND 的 pywin32/IDispatch 解码。
@Project : SCP-cv
@File : window_handles.py
@Author : Qintsg
@Date : 2026-07-11
'''
from __future__ import annotations


def normalize_hwnd(value: object) -> int:
    """把 pywin32 包装值和有符号 32 位 HWND 归一为有效整数。"""
    current = value
    for _ in range(4):
        if callable(current):
            current = current()
            continue
        wrapped = getattr(current, "value", current)
        if wrapped is current:
            break
        current = wrapped
    if current is None or isinstance(current, bool):
        return 0
    try:
        hwnd = int(current)
    except (TypeError, ValueError, OverflowError):
        return 0
    if hwnd < 0:
        hwnd &= 0xFFFFFFFF
    return hwnd if hwnd > 0 else 0


def read_com_slideshow_hwnd(slideshow_window: object | None) -> int:
    """兼容属性、可调用成员、包装值和 IDispatch 的 HWND 读取。"""
    if slideshow_window is None:
        return 0
    for attribute_name in ("HWND", "Hwnd", "hwnd"):
        try:
            hwnd = normalize_hwnd(getattr(slideshow_window, attribute_name))
        except Exception:
            continue
        if hwnd:
            return hwnd

    ole_object = getattr(slideshow_window, "_oleobj_", None)
    if ole_object is None:
        return 0
    try:
        dispatch_id = ole_object.GetIDsOfNames("HWND")
        if isinstance(dispatch_id, (tuple, list)):
            dispatch_id = dispatch_id[0]
        for dispatch_flag in (2, 1):
            try:
                hwnd = normalize_hwnd(
                    ole_object.Invoke(int(dispatch_id), 0, dispatch_flag, 1)
                )
            except Exception:
                continue
            if hwnd:
                return hwnd
    except Exception:
        return 0
    return 0


__all__ = ["normalize_hwnd", "read_com_slideshow_hwnd"]
