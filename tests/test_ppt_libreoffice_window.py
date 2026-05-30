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

from scp_cv.player.adapters import ppt_libreoffice_window as lo_window
from scp_cv.player.adapters.ppt_libreoffice_window import (
    find_libreoffice_slideshow_hwnd,
    snapshot_libreoffice_hwnds,
)


FakeWindow = tuple[str, bool, tuple[int, int, int, int]] | tuple[
    str,
    bool,
    tuple[int, int, int, int],
    str,
]


def _install_fake_win32gui(
    monkeypatch: MonkeyPatch,
    windows: dict[int, FakeWindow],
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

    def get_window_text(hwnd: int) -> str:
        """
        返回伪窗口标题。
        :param hwnd: 窗口句柄
        :return: Win32 窗口标题
        """
        window = windows[hwnd]
        if len(window) < 4:
            return ""
        return window[3]

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
    fake_win32gui.GetWindowText = get_window_text
    fake_win32gui.EnumWindows = enum_windows
    monkeypatch.setitem(sys.modules, "win32gui", fake_win32gui)


def test_snapshot_libreoffice_hwnds_collects_sal_windows(
    monkeypatch: MonkeyPatch,
) -> None:
    """快照只应包含可见 LibreOffice SAL 候选窗口。"""
    _install_fake_win32gui(
        monkeypatch,
        {
            101: ("SALFRAME", True, (0, 0, 100, 100)),
            202: ("SALSUBFRAME", True, (0, 0, 100, 100)),
            303: ("SALTMPSUBFRAME", True, (0, 0, 100, 100)),
            404: ("Chrome_WidgetWin_1", True, (0, 0, 100, 100)),
            505: ("SALFRAME", False, (0, 0, 100, 100)),
        },
    )

    hwnds = snapshot_libreoffice_hwnds(logging.getLogger(__name__))

    assert hwnds == {101, 202, 303}


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


def test_find_libreoffice_hwnd_prefers_subframe_over_outer_frame(
    monkeypatch: MonkeyPatch,
) -> None:
    """同时存在外层框架和内层放映框架时，应选择内层放映画面。"""
    _install_fake_win32gui(
        monkeypatch,
        {
            101: ("SALFRAME", True, (0, 0, 1920, 1080)),
            202: ("SALSUBFRAME", True, (10, 10, 1910, 1070)),
        },
    )

    hwnd = find_libreoffice_slideshow_hwnd(
        logging.getLogger(__name__),
        existing_hwnds=set(),
    )

    assert hwnd == 202


def test_find_libreoffice_hwnd_prefers_temp_subframe_over_outer_frame(
    monkeypatch: MonkeyPatch,
) -> None:
    """LibreOffice 直启放映常见的 SALTMPSUBFRAME 应优先于外层框架。"""
    _install_fake_win32gui(
        monkeypatch,
        {
            101: ("SALFRAME", True, (0, 0, 1920, 1080)),
            202: ("SALSUBFRAME", True, (730, 433, 863, 820)),
            303: ("SALTMPSUBFRAME", True, (0, 0, 1463, 915)),
        },
    )

    hwnd = find_libreoffice_slideshow_hwnd(
        logging.getLogger(__name__),
        existing_hwnds=set(),
    )

    assert hwnd == 303


def test_find_libreoffice_hwnd_ignores_impress_editor_window(
    monkeypatch: MonkeyPatch,
) -> None:
    """LibreOffice Impress 编辑主窗口不应被当作放映窗口。"""
    _install_fake_win32gui(
        monkeypatch,
        {
            101: ("SALFRAME", True, (0, 0, 1920, 1080), "demo.pptx - LibreOffice Impress"),
            202: ("SALSUBFRAME", True, (0, 0, 1280, 720), "LibreOffice Slide Show"),
        },
    )

    hwnd = find_libreoffice_slideshow_hwnd(
        logging.getLogger(__name__),
        existing_hwnds=set(),
    )

    assert hwnd == 202


def test_find_libreoffice_hwnd_returns_zero_for_editor_only(
    monkeypatch: MonkeyPatch,
) -> None:
    """只存在 Impress 编辑主窗口时，不应返回可铺满的放映 HWND。"""
    _install_fake_win32gui(
        monkeypatch,
        {
            101: ("SALFRAME", True, (0, 0, 1920, 1080), "demo.pptx - LibreOffice Impress"),
        },
    )
    monkeypatch.setattr(lo_window.time, "sleep", lambda _seconds: None)

    hwnd = find_libreoffice_slideshow_hwnd(
        logging.getLogger(__name__),
        existing_hwnds=set(),
        timeout_seconds=0.1,
        poll_interval_seconds=0.1,
    )

    assert hwnd == 0


def test_find_libreoffice_hwnd_ignores_editor_filename_with_slideshow_keyword(
    monkeypatch: MonkeyPatch,
) -> None:
    """文件名包含“放映”时，Impress 编辑窗口仍不应被误判为放映窗口。"""
    _install_fake_win32gui(
        monkeypatch,
        {
            101: (
                "SALFRAME",
                True,
                (0, 0, 1920, 1080),
                "2026放映方案.pptx - LibreOffice Impress",
            ),
        },
    )
    monkeypatch.setattr(lo_window.time, "sleep", lambda _seconds: None)

    hwnd = find_libreoffice_slideshow_hwnd(
        logging.getLogger(__name__),
        existing_hwnds=set(),
        timeout_seconds=0.1,
        poll_interval_seconds=0.1,
    )

    assert hwnd == 0


def test_find_libreoffice_hwnd_keeps_slideshow_title_with_app_name(
    monkeypatch: MonkeyPatch,
) -> None:
    """带 LibreOffice Impress 字样的放映标题不应被编辑窗口过滤误伤。"""
    _install_fake_win32gui(
        monkeypatch,
        {
            101: ("SALFRAME", True, (0, 0, 1920, 1080), "Slide Show - LibreOffice Impress"),
        },
    )

    hwnd = find_libreoffice_slideshow_hwnd(
        logging.getLogger(__name__),
        existing_hwnds=set(),
    )

    assert hwnd == 101


def test_find_libreoffice_hwnd_waits_until_window_visible(monkeypatch: MonkeyPatch) -> None:
    """LibreOffice 放映窗口稍后可见时应轮询等待，而不是立即失败。"""
    windows = {
        101: ("SALFRAME", False, (0, 0, 800, 600)),
    }
    sleep_calls: list[float] = []

    def fake_sleep(seconds: float) -> None:
        """
        模拟等待后 LibreOffice 放映窗口变为可见。
        :param seconds: 等待秒数
        :return: None
        """
        sleep_calls.append(seconds)
        windows[101] = ("SALFRAME", True, (0, 0, 800, 600))

    _install_fake_win32gui(monkeypatch, windows)
    monkeypatch.setattr(lo_window.time, "sleep", fake_sleep)

    hwnd = find_libreoffice_slideshow_hwnd(
        logging.getLogger(__name__),
        existing_hwnds=set(),
        timeout_seconds=0.5,
        poll_interval_seconds=0.1,
    )

    assert hwnd == 101
    assert sleep_calls == [0.1]
