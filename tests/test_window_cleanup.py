#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
播放器 Win32 顶层窗口清理测试。
@Project : SCP-cv
@File : test_window_cleanup.py
@Author : Qintsg
@Date : 2026-06-08
'''
from __future__ import annotations

import sys
from types import ModuleType

from pytest import MonkeyPatch

from scp_cv.player.window_cleanup import minimize_unprotected_top_level_windows


def test_minimize_unprotected_top_level_windows_keeps_protected_roots(
    monkeypatch: MonkeyPatch,
) -> None:
    """
    PPT 生命周期清理应保留 PySide/PPT 保护窗口，只最小化其它顶层可见窗口。
    :param monkeypatch: pytest monkeypatch 工具
    :return: None
    """
    fake_win32con = ModuleType("win32con")
    fake_win32con.GA_ROOT = 2
    fake_win32con.GW_OWNER = 4
    fake_win32con.SW_MINIMIZE = 6

    roots = {
        10: 10,
        11: 10,
        20: 20,
        30: 30,
        40: 40,
        50: 50,
        60: 60,
        70: 70,
    }
    visible = {
        10: True,
        11: True,
        20: True,
        30: False,
        40: True,
        50: True,
        60: True,
        70: True,
    }
    iconic = {
        10: False,
        20: False,
        30: False,
        40: True,
        50: False,
        60: False,
        70: False,
    }
    owners = {
        10: 0,
        20: 0,
        30: 0,
        40: 0,
        50: 999,
        60: 0,
        70: 0,
    }
    class_names = {
        10: "PlayerWindow",
        20: "Chrome_WidgetWin_1",
        30: "HiddenWindow",
        40: "OtherWindow",
        50: "OwnedWindow",
        60: "screenClass",
        70: "PPTFrameClass",
    }
    titles = {
        10: "SCP-cv 播放器",
        20: "普通窗口",
        30: "",
        40: "",
        50: "",
        60: "PowerPoint Slide Show - A.pptx",
        70: "PowerPoint 幻灯片放映 - B.pptx",
    }
    minimized: list[int] = []

    fake_win32gui = ModuleType("win32gui")
    fake_win32gui.GetAncestor = lambda hwnd, _flag: roots[hwnd]
    fake_win32gui.IsWindowVisible = lambda hwnd: visible[hwnd]
    fake_win32gui.IsIconic = lambda hwnd: iconic[hwnd]
    fake_win32gui.GetWindow = lambda hwnd, _flag: owners[hwnd]
    fake_win32gui.GetClassName = lambda hwnd: class_names[hwnd]
    fake_win32gui.GetWindowText = lambda hwnd: titles[hwnd]
    fake_win32gui.ShowWindow = lambda hwnd, _flag: minimized.append(hwnd)

    def enum_windows(callback: object, extra: object) -> None:
        """
        枚举包含子窗口、受保护窗口、普通窗口和应跳过窗口的假桌面。
        :param callback: Win32 回调
        :param extra: 透传参数
        :return: None
        """
        for hwnd in [10, 11, 20, 30, 40, 50, 60, 70]:
            callback(hwnd, extra)

    fake_win32gui.EnumWindows = enum_windows
    monkeypatch.setitem(sys.modules, "win32con", fake_win32con)
    monkeypatch.setitem(sys.modules, "win32gui", fake_win32gui)

    result = minimize_unprotected_top_level_windows({10})

    assert result == [20]
    assert minimized == [20]
