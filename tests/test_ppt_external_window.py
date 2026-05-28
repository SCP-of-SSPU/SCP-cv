#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PPT 外部放映窗口工具测试，覆盖铺满目标区域的 Win32 调用参数。
@Project : SCP-cv
@File : test_ppt_external_window.py
@Author : Qintsg
@Date : 2026-05-28
'''
from __future__ import annotations

import sys
from types import ModuleType

from pytest import MonkeyPatch

from scp_cv.player.adapters.ppt_external_window import (
    present_external_slideshow_window,
    release_external_slideshow_window,
)


def _install_fake_win32_modules(monkeypatch: MonkeyPatch) -> dict[str, object]:
    """
    安装可控 Win32 替身，避免测试依赖真实桌面窗口。
    :param monkeypatch: pytest monkeypatch fixture
    :return: 调用记录
    """
    calls: dict[str, object] = {
        "set_parent": [],
        "set_window_long": [],
        "set_window_pos": [],
    }
    fake_win32con = ModuleType("win32con")
    fake_win32con.GWL_STYLE = -16
    fake_win32con.GWL_EXSTYLE = -20
    fake_win32con.WS_CHILD = 0x40000000
    fake_win32con.WS_OVERLAPPEDWINDOW = 0x00CF0000
    fake_win32con.WS_POPUP = 0x80000000
    fake_win32con.WS_VISIBLE = 0x10000000
    fake_win32con.WS_EX_APPWINDOW = 0x00040000
    fake_win32con.WS_EX_TOPMOST = 0x00000008
    fake_win32con.HWND_TOPMOST = -1
    fake_win32con.HWND_NOTOPMOST = -2
    fake_win32con.SWP_FRAMECHANGED = 0x0020
    fake_win32con.SWP_SHOWWINDOW = 0x0040
    fake_win32con.SWP_NOMOVE = 0x0002
    fake_win32con.SWP_NOSIZE = 0x0001
    fake_win32con.SWP_NOACTIVATE = 0x0010
    fake_win32con.MONITOR_DEFAULTTONEAREST = 2
    fake_win32con.GA_ROOT = 2

    fake_win32gui = ModuleType("win32gui")

    def get_window_rect(hwnd: int) -> tuple[int, int, int, int]:
        """
        返回伪窗口矩形。
        :param hwnd: 窗口句柄
        :return: 矩形
        """
        if hwnd == 2001:
            return 100, 200, 1380, 920
        return 0, 0, 300, 200

    def get_window_long(hwnd: int, index: int) -> int:
        """
        返回伪窗口样式。
        :param hwnd: 窗口句柄
        :param index: 样式索引
        :return: 样式值
        """
        if index == fake_win32con.GWL_STYLE:
            return fake_win32con.WS_CHILD | fake_win32con.WS_OVERLAPPEDWINDOW
        return fake_win32con.WS_EX_APPWINDOW

    def set_parent(hwnd: int, parent_hwnd: int) -> None:
        """
        记录父窗口设置。
        :param hwnd: 窗口句柄
        :param parent_hwnd: 父窗口句柄
        :return: None
        """
        calls["set_parent"].append((hwnd, parent_hwnd))  # type: ignore[attr-defined]

    def set_window_long(hwnd: int, index: int, style: int) -> None:
        """
        记录样式设置。
        :param hwnd: 窗口句柄
        :param index: 样式索引
        :param style: 样式值
        :return: None
        """
        calls["set_window_long"].append((hwnd, index, style))  # type: ignore[attr-defined]

    def set_window_pos(
        hwnd: int,
        insert_after: int,
        x: int,
        y: int,
        width: int,
        height: int,
        flags: int,
    ) -> None:
        """
        记录窗口定位。
        :param hwnd: 窗口句柄
        :param insert_after: Z 序参数
        :param x: X 坐标
        :param y: Y 坐标
        :param width: 宽度
        :param height: 高度
        :param flags: Win32 flags
        :return: None
        """
        calls["set_window_pos"].append((hwnd, insert_after, x, y, width, height, flags))  # type: ignore[attr-defined]

    fake_win32gui.GetWindowRect = get_window_rect
    fake_win32gui.GetWindowLong = get_window_long
    fake_win32gui.SetWindowLong = set_window_long
    fake_win32gui.SetParent = set_parent
    fake_win32gui.SetWindowPos = set_window_pos
    monkeypatch.setitem(sys.modules, "win32con", fake_win32con)
    monkeypatch.setitem(sys.modules, "win32gui", fake_win32gui)
    return calls


def test_present_external_slideshow_window_uses_anchor_rect(monkeypatch: MonkeyPatch) -> None:
    """外部放映窗口应解除父子关系并铺满 PySide 目标区域。"""
    calls = _install_fake_win32_modules(monkeypatch)

    size = present_external_slideshow_window(909, 2001)

    assert size == (1280, 720)
    assert calls["set_parent"] == [(909, 0)]
    assert calls["set_window_pos"][-1][:6] == (909, -1, 100, 200, 1280, 720)


def test_release_external_slideshow_window_clears_topmost(monkeypatch: MonkeyPatch) -> None:
    """释放外部窗口时应清理置顶状态。"""
    calls = _install_fake_win32_modules(monkeypatch)

    release_external_slideshow_window(909)

    assert calls["set_parent"] == [(909, 0)]
    assert calls["set_window_pos"][-1][1] == -2
