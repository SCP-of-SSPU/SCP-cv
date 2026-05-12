#!/user/bin/env python
# -*- coding: UTF-8 -*-
"""
PowerPoint 放映窗口查找测试，覆盖多窗口同时放映时的 HWND 归属过滤。
@Project : SCP-cv
@File : test_ppt_window.py
@Author : Qintsg
@Date : 2026-05-12
"""

from __future__ import annotations
import logging
import sys
from types import ModuleType
from pytest import MonkeyPatch
from scp_cv.player.adapters.ppt_window import (
    find_slideshow_hwnd,
    snapshot_slideshow_hwnds,
)


def _install_fake_win32gui(
    monkeypatch: MonkeyPatch,
    windows: dict[int, tuple[str, bool]],
) -> None:
    """
    安装可控的 win32gui 替身，避免测试依赖真实 Windows 桌面窗口。
    :param monkeypatch: pytest monkeypatch fixture
    :param windows: HWND 到 (class_name, visible) 的映射
    :return: None
    """
    fake_win32gui = ModuleType("win32gui")

    def is_window_visible(hwnd: int) -> bool:
        """
        返回伪窗口可见性。
        :param hwnd: 窗口句柄
        :return: True 表示窗口可见
        """
        return windows[hwnd][1]

    def get_class_name(hwnd: int) -> str:
        """
        返回伪窗口类名。
        :param hwnd: 窗口句柄
        :return: Win32 窗口类名
        """
        return windows[hwnd][0]

    def enum_windows(callback: object, extra: object) -> None:
        """
        按插入顺序枚举伪窗口，模拟 win32gui.EnumWindows。
        :param callback: 枚举回调
        :param extra: 回调透传参数
        :return: None
        """
        for hwnd in windows:
            if callback(hwnd, extra) is False:
                break

    fake_win32gui.IsWindowVisible = is_window_visible
    fake_win32gui.GetClassName = get_class_name
    fake_win32gui.EnumWindows = enum_windows
    monkeypatch.setitem(sys.modules, "win32gui", fake_win32gui)


def test_snapshot_slideshow_hwnds_collects_visible_powerpoint_windows(
    monkeypatch: MonkeyPatch,
) -> None:
    """快照只应包含可见的 PowerPoint 放映窗口。"""
    _install_fake_win32gui(
        monkeypatch,
        {
            101: ("screenClass", True),
            202: ("paneClassDC", True),
            303: ("Chrome_WidgetWin_1", True),
            404: ("screenClass", False),
        },
    )
    slideshow_hwnds = snapshot_slideshow_hwnds(logging.getLogger(__name__))
    assert slideshow_hwnds == {101, 202}


def test_find_slideshow_hwnd_prefers_com_hwnd() -> None:
    """COM 直接返回 HWND 时应直接使用，避免 Win32 枚举误判。"""
    logger = logging.getLogger(__name__)
    slideshow_window = type("_SlideShowWindowStub", (), {"HWND": 101})()
    hwnd = find_slideshow_hwnd(slideshow_window, logger, existing_hwnds={101})
    assert hwnd == 101


def test_find_slideshow_hwnd_excludes_existing_windows(
    monkeypatch: MonkeyPatch,
) -> None:
    """回退枚举应排除本次放映前已存在的 PPT 窗口。"""
    _install_fake_win32gui(
        monkeypatch,
        {
            101: ("screenClass", True),
            202: ("screenClass", True),
        },
    )
    hwnd = find_slideshow_hwnd(
        None,
        logging.getLogger(__name__),
        existing_hwnds={101},
    )
    assert hwnd == 202


def test_find_slideshow_hwnd_returns_zero_when_only_existing_window_found(
    monkeypatch: MonkeyPatch,
) -> None:
    """仅枚举到已有放映窗口时不应把别的窗口重新嵌入当前播放器。"""
    _install_fake_win32gui(monkeypatch, {101: ("screenClass", True)})
    hwnd = find_slideshow_hwnd(
        None,
        logging.getLogger(__name__),
        existing_hwnds={101},
    )
    assert hwnd == 0


def test_find_slideshow_hwnd_returns_zero_for_ambiguous_new_windows(
    monkeypatch: MonkeyPatch,
) -> None:
    """多个新增候选窗口时宁可不嵌入，也不随机占用其他放映窗口。"""
    _install_fake_win32gui(
        monkeypatch,
        {
            101: ("screenClass", True),
            202: ("paneClassDC", True),
        },
    )
    hwnd = find_slideshow_hwnd(None, logging.getLogger(__name__), existing_hwnds=set())
    assert hwnd == 0
