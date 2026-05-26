#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
LibreOffice 放映窗口查找测试，覆盖 SALFRAME/SALSUBFRAME 候选与启动前快照过滤。
@Project : SCP-cv
@File : test_ppt_libreoffice_window.py
@Author : Qintsg
@Date : 2026-05-26
'''
from __future__ import annotations

import logging
import sys
from types import ModuleType

from pytest import MonkeyPatch

from scp_cv.player.adapters.ppt_libreoffice_window import (
    find_libreoffice_slideshow_hwnd,
    snapshot_libreoffice_hwnds,
)


def _install_fake_win32gui(
    monkeypatch: MonkeyPatch,
    windows: dict[int, tuple[str, bool, tuple[int, int, int, int]]],
) -> None:
    """
    安装可控的 win32gui 替身。
    :param monkeypatch: pytest monkeypatch fixture
    :param windows: HWND 到 (class_name, visible, rect) 的映射
    :return: None
    """
    fake_win32gui = ModuleType("win32gui")

    def is_window_visible(hwnd: int) -> bool:
        """
        返回伪窗口可见性。
        :param hwnd: 窗口句柄
        :return: True 表示可见
        """
        return windows[hwnd][1]

    def get_class_name(hwnd: int) -> str:
        """
        返回伪窗口类名。
        :param hwnd: 窗口句柄
        :return: Win32 窗口类名
        """
        return windows[hwnd][0]

    def get_window_rect(hwnd: int) -> tuple[int, int, int, int]:
        """
        返回伪窗口矩形。
        :param hwnd: 窗口句柄
        :return: left/top/right/bottom
        """
        return windows[hwnd][2]

    def enum_windows(callback: object, extra: object) -> None:
        """
        按插入顺序枚举窗口。
        :param callback: 枚举回调
        :param extra: 回调透传参数
        :return: None
        """
        for hwnd in windows:
            if callback(hwnd, extra) is False:
                break

    fake_win32gui.IsWindowVisible = is_window_visible
    fake_win32gui.GetClassName = get_class_name
    fake_win32gui.GetWindowRect = get_window_rect
    fake_win32gui.EnumWindows = enum_windows
    monkeypatch.setitem(sys.modules, "win32gui", fake_win32gui)


def test_snapshot_libreoffice_hwnds_collects_sal_windows(
    monkeypatch: MonkeyPatch,
) -> None:
    """快照只应包含可见 LibreOffice SALFRAME/SALSUBFRAME 窗口。"""
    _install_fake_win32gui(
        monkeypatch,
        {
            101: ("SALFRAME", True, (0, 0, 100, 100)),
            202: ("SALSUBFRAME", True, (0, 0, 100, 100)),
            303: ("Chrome_WidgetWin_1", True, (0, 0, 100, 100)),
            404: ("SALFRAME", False, (0, 0, 100, 100)),
        },
    )

    hwnds = snapshot_libreoffice_hwnds(logging.getLogger(__name__))

    assert hwnds == {101, 202}


def test_find_libreoffice_hwnd_excludes_existing_windows(
    monkeypatch: MonkeyPatch,
) -> None:
    """回退枚举应排除本次放映前已存在的 LibreOffice 窗口。"""
    _install_fake_win32gui(
        monkeypatch,
        {
            101: ("SALFRAME", True, (0, 0, 100, 100)),
            202: ("SALFRAME", True, (0, 0, 100, 100)),
        },
    )

    hwnd = find_libreoffice_slideshow_hwnd(
        logging.getLogger(__name__),
        existing_hwnds={101},
    )

    assert hwnd == 202


def test_find_libreoffice_hwnd_prefers_largest_new_window(
    monkeypatch: MonkeyPatch,
) -> None:
    """多个新增 LibreOffice 窗口时应选择面积最大的放映窗口。"""
    _install_fake_win32gui(
        monkeypatch,
        {
            101: ("SALFRAME", True, (0, 0, 200, 100)),
            202: ("SALFRAME", True, (0, 0, 800, 600)),
        },
    )

    hwnd = find_libreoffice_slideshow_hwnd(
        logging.getLogger(__name__),
        existing_hwnds=set(),
    )

    assert hwnd == 202
