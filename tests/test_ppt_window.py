#!/user/bin/env python
# -*- coding: UTF-8 -*-
"""
    PPT 放映窗口查找测试，覆盖多窗口同时放映时的 HWND 归属过滤。
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
from scp_cv.player.adapters import ppt_window
from scp_cv.player.adapters.ppt_window import (
    find_slideshow_hwnd,
    snapshot_slideshow_hwnds,
)


def _install_fake_win32gui(
    monkeypatch: MonkeyPatch,
    windows: dict[int, tuple[str, bool] | tuple[str, bool, str]],
) -> None:
    """
    安装可控的 win32gui 替身，避免测试依赖真实 Windows 桌面窗口。
    :param monkeypatch: pytest monkeypatch fixture
    :param windows: HWND 到 (class_name, visible[, title]) 的映射
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

    def get_window_text(hwnd: int) -> str:
        """
        返回伪窗口标题。
        :param hwnd: 窗口句柄
        :return: Win32 窗口标题
        """
        return windows[hwnd][2] if len(windows[hwnd]) > 2 else ""

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
    fake_win32gui.GetWindowText = get_window_text
    fake_win32gui.EnumWindows = enum_windows
    monkeypatch.setitem(sys.modules, "win32gui", fake_win32gui)


def _install_fake_win32process(
    monkeypatch: MonkeyPatch,
    window_process_ids: dict[int, int],
) -> None:
    """安装可控的 win32process 替身。"""
    fake_win32process = ModuleType("win32process")

    def get_window_thread_process_id(hwnd: int) -> tuple[int, int]:
        """
        返回伪窗口所属进程。
        :param hwnd: 窗口句柄
        :return: 线程 ID 与进程 ID
        """
        return 1, window_process_ids[hwnd]

    fake_win32process.GetWindowThreadProcessId = get_window_thread_process_id
    monkeypatch.setitem(sys.modules, "win32process", fake_win32process)


def test_snapshot_slideshow_hwnds_collects_visible_powerpoint_windows(
    monkeypatch: MonkeyPatch,
) -> None:
    """快照只应包含可见的默认 PPT 放映窗口。"""
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


def test_find_slideshow_hwnd_prefers_com_hwnd(monkeypatch: MonkeyPatch) -> None:
    """COM 直接返回新且有效的 HWND 时应直接使用，避免 Win32 枚举误判。"""
    logger = logging.getLogger(__name__)
    slideshow_window = type("_SlideShowWindowStub", (), {"HWND": 101})()
    _install_fake_win32gui(monkeypatch, {101: ("screenClass", True)})
    hwnd = find_slideshow_hwnd(slideshow_window, logger, existing_hwnds=set())
    assert hwnd == 101


def test_find_slideshow_hwnd_waits_when_com_returns_existing_hwnd(
    monkeypatch: MonkeyPatch,
) -> None:
    """COM 返回旧 HWND 时应优先等待本次 Run 后新出现的放映窗口。"""
    windows = {
        101: ("screenClass", True),
        202: ("screenClass", False),
    }
    now = [0.0]
    sleep_calls: list[float] = []
    slideshow_window = type("_SlideShowWindowStub", (), {"HWND": 101})()
    _install_fake_win32gui(monkeypatch, windows)

    def fake_sleep(seconds: float) -> None:
        """
        模拟等待期间新放映窗口出现。
        :param seconds: 等待秒数
        :return: None
        """
        sleep_calls.append(seconds)
        now[0] += seconds
        windows[202] = ("screenClass", True)

    monkeypatch.setattr(ppt_window.time, "monotonic", lambda: now[0])
    monkeypatch.setattr(ppt_window.time, "sleep", fake_sleep)

    hwnd = find_slideshow_hwnd(
        slideshow_window,
        logging.getLogger(__name__),
        existing_hwnds={101},
        timeout_seconds=1.0,
        poll_interval_seconds=0.1,
        allow_existing_when_unique=True,
    )

    assert hwnd == 202
    assert sleep_calls == [0.1]


def test_find_slideshow_hwnd_can_reuse_existing_com_hwnd_after_grace(
    monkeypatch: MonkeyPatch,
) -> None:
    """PowerPoint 复用当前进程唯一旧 HWND 时，应等待稳定后再接受。"""
    windows = {101: ("screenClass", True)}
    now = [0.0]
    sleep_calls: list[float] = []
    slideshow_window = type("_SlideShowWindowStub", (), {"HWND": 101})()
    _install_fake_win32gui(monkeypatch, windows)
    _install_fake_win32process(monkeypatch, {101: 900})

    def fake_sleep(seconds: float) -> None:
        """
        推进虚拟时钟但不创建新窗口。
        :param seconds: 等待秒数
        :return: None
        """
        sleep_calls.append(seconds)
        now[0] += seconds

    monkeypatch.setattr(ppt_window.time, "monotonic", lambda: now[0])
    monkeypatch.setattr(ppt_window.time, "sleep", fake_sleep)

    hwnd = find_slideshow_hwnd(
        slideshow_window,
        logging.getLogger(__name__),
        existing_hwnds={101},
        timeout_seconds=1.0,
        poll_interval_seconds=0.1,
        process_id=900,
        allow_existing_when_unique=True,
        existing_com_grace_seconds=0.25,
    )

    assert hwnd == 101
    assert sleep_calls == [0.1, 0.1, 0.1]


def test_find_slideshow_hwnd_rejects_existing_com_hwnd_without_process(
    monkeypatch: MonkeyPatch,
) -> None:
    """进程不可确认时，不应把启动前已有 HWND 当作本次放映窗口。"""
    slideshow_window = type("_SlideShowWindowStub", (), {"HWND": 101})()
    _install_fake_win32gui(monkeypatch, {101: ("screenClass", True)})

    hwnd = find_slideshow_hwnd(
        slideshow_window,
        logging.getLogger(__name__),
        existing_hwnds={101},
        timeout_seconds=0.0,
        allow_existing_when_unique=True,
        existing_com_grace_seconds=0.0,
    )

    assert hwnd == 0


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


def test_find_slideshow_hwnd_matches_powerpoint_frame_class(
    monkeypatch: MonkeyPatch,
) -> None:
    """新版 PowerPoint 窗口化放映可能只暴露 PPTFrameClass。"""
    _install_fake_win32gui(
        monkeypatch,
        {
            101: ("PPTFrameClass", True),
        },
    )

    hwnd = find_slideshow_hwnd(
        None,
        logging.getLogger(__name__),
        existing_hwnds=set(),
    )

    assert hwnd == 101


def test_find_slideshow_hwnd_ignores_powerpoint_editor_frame(
    monkeypatch: MonkeyPatch,
) -> None:
    """PowerPoint 编辑主窗口不应被当成放映窗口。"""
    _install_fake_win32gui(
        monkeypatch,
        {
            101: ("PPTFrameClass", True, "demo.pptx - PowerPoint"),
            202: ("PPTFrameClass", True, "PowerPoint Slide Show - demo.pptx"),
        },
    )

    hwnd = find_slideshow_hwnd(
        None,
        logging.getLogger(__name__),
        existing_hwnds=set(),
    )

    assert hwnd == 202


def test_find_slideshow_hwnd_accepts_localized_powerpoint_slideshow_title(
    monkeypatch: MonkeyPatch,
) -> None:
    """中文 PowerPoint 放映标题不应被 PowerPoint 关键词误判为编辑窗口。"""
    _install_fake_win32gui(
        monkeypatch,
        {
            101: ("PPTFrameClass", True, "demo.pptx - PowerPoint"),
            202: ("PPTFrameClass", True, "PowerPoint幻灯片放映——demo.pptx"),
        },
    )

    hwnd = find_slideshow_hwnd(
        None,
        logging.getLogger(__name__),
        existing_hwnds=set(),
    )

    assert hwnd == 202


def test_find_slideshow_hwnd_returns_zero_for_powerpoint_editor_only(
    monkeypatch: MonkeyPatch,
) -> None:
    """只有 PowerPoint 编辑主窗口时不应返回 HWND。"""
    _install_fake_win32gui(
        monkeypatch,
        {
            101: ("PPTFrameClass", True, "demo.pptx - PowerPoint"),
        },
    )

    hwnd = find_slideshow_hwnd(
        None,
        logging.getLogger(__name__),
        existing_hwnds=set(),
        allow_existing_when_unique=True,
    )

    assert hwnd == 0


def test_find_slideshow_hwnd_ignores_powerpoint_editor_filename_with_keyword(
    monkeypatch: MonkeyPatch,
) -> None:
    """文件名包含放映关键词时，PowerPoint 编辑窗口仍不应被当成放映窗口。"""
    _install_fake_win32gui(
        monkeypatch,
        {
            101: ("PPTFrameClass", True, "2026放映方案.pptx - PowerPoint"),
        },
    )

    hwnd = find_slideshow_hwnd(
        None,
        logging.getLogger(__name__),
        existing_hwnds=set(),
        allow_existing_when_unique=True,
    )

    assert hwnd == 0


def test_find_slideshow_hwnd_can_use_process_scoped_existing_window(
    monkeypatch: MonkeyPatch,
) -> None:
    """进程可确认时，可使用 Run 前已存在的唯一窗口化放映候选。"""
    _install_fake_win32gui(
        monkeypatch,
        {
            101: ("PPTFrameClass", True),
            202: ("PPTFrameClass", True),
        },
    )
    _install_fake_win32process(monkeypatch, {101: 900, 202: 901})

    hwnd = find_slideshow_hwnd(
        None,
        logging.getLogger(__name__),
        existing_hwnds={101},
        process_id=900,
        allow_existing_when_unique=True,
    )

    assert hwnd == 101


def test_find_slideshow_hwnd_rejects_single_global_existing_window(
    monkeypatch: MonkeyPatch,
) -> None:
    """进程不可读时，不应回收启动前已存在的全局唯一放映候选。"""
    _install_fake_win32gui(
        monkeypatch,
        {
            101: ("PPTFrameClass", True),
        },
    )

    hwnd = find_slideshow_hwnd(
        None,
        logging.getLogger(__name__),
        existing_hwnds={101},
        allow_existing_when_unique=True,
    )

    assert hwnd == 0


def test_find_slideshow_hwnd_waits_for_delayed_window(
    monkeypatch: MonkeyPatch,
) -> None:
    """回退枚举应等待启动后异步出现的放映窗口。"""
    windows = {202: ("screenClass", False)}
    sleep_calls: list[float] = []
    now = [0.0]
    _install_fake_win32gui(monkeypatch, windows)

    def fake_sleep(seconds: float) -> None:
        """
        模拟等待期间 PowerPoint 创建并显示放映窗口。
        :param seconds: 等待秒数
        :return: None
        """
        sleep_calls.append(seconds)
        now[0] += seconds
        windows[202] = ("screenClass", True)

    monkeypatch.setattr(ppt_window.time, "monotonic", lambda: now[0])
    monkeypatch.setattr(ppt_window.time, "sleep", fake_sleep)

    hwnd = find_slideshow_hwnd(
        None,
        logging.getLogger(__name__),
        existing_hwnds=set(),
        timeout_seconds=1.0,
        poll_interval_seconds=0.1,
    )

    assert hwnd == 202
    assert sleep_calls == [0.1]
