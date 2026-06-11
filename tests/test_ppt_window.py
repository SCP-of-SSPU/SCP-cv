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
    close_embedded_slideshow_window,
    EMBEDDED_SLIDESHOW_PROP,
    embed_slideshow_window,
    find_slideshow_hwnd,
    hide_embedded_slideshow_window,
    show_embedded_slideshow_window,
    snapshot_slideshow_hwnds,
)


def _install_fake_win32gui(
    monkeypatch: MonkeyPatch,
    windows: dict[int, tuple[str, bool] | tuple[str, bool, str]],
    embedded_hwnds: set[int] | None = None,
) -> None:
    """
    安装可控的 win32gui 替身，避免测试依赖真实 Windows 桌面窗口。
    :param monkeypatch: pytest monkeypatch fixture
    :param windows: HWND 到 (class_name, visible[, title]) 的映射
    :param embedded_hwnds: 已被 PySide 认领的 PPT 放映 HWND
    :return: None
    """
    fake_win32gui = ModuleType("win32gui")
    embedded = embedded_hwnds or set()

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

    def get_prop(hwnd: int, name: str) -> int:
        """
        返回伪 Win32 窗口属性。
        :param hwnd: 窗口句柄
        :param name: 属性名
        :return: 属性值；0 表示不存在
        """
        if name == EMBEDDED_SLIDESHOW_PROP and hwnd in embedded:
            return 1
        return 0

    fake_win32gui.IsWindowVisible = is_window_visible
    fake_win32gui.GetClassName = get_class_name
    fake_win32gui.GetWindowText = get_window_text
    fake_win32gui.EnumWindows = enum_windows
    fake_win32gui.GetProp = get_prop
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


def _install_fake_embed_win32(
    monkeypatch: MonkeyPatch,
    calls: list[tuple[object, ...]],
    *,
    window_exists: bool = True,
) -> ModuleType:
    """
    安装嵌入窗口测试用 win32gui/win32con 替身。
    :param monkeypatch: pytest monkeypatch fixture
    :param calls: 调用记录
    :param window_exists: IsWindow 返回值
    :return: fake win32con 模块
    """
    fake_win32con = ModuleType("win32con")
    fake_win32con.GWL_STYLE = -16
    fake_win32con.GWL_EXSTYLE = -20
    fake_win32con.WS_POPUP = 0x80000000
    fake_win32con.WS_OVERLAPPEDWINDOW = 0x00CF0000
    fake_win32con.WS_CHILD = 0x40000000
    fake_win32con.WS_VISIBLE = 0x10000000
    fake_win32con.WS_EX_TOPMOST = 0x00000008
    fake_win32con.WS_EX_APPWINDOW = 0x00040000
    fake_win32con.HWND_TOP = 0
    fake_win32con.SWP_NOZORDER = 0x0004
    fake_win32con.SWP_NOACTIVATE = 0x0010
    fake_win32con.SWP_FRAMECHANGED = 0x0020
    fake_win32con.SWP_SHOWWINDOW = 0x0040
    fake_win32con.SW_HIDE = 0
    fake_win32con.SW_SHOW = 5
    fake_win32con.WM_CLOSE = 0x0010

    fake_win32gui = ModuleType("win32gui")
    state = {
        "style": fake_win32con.WS_POPUP | fake_win32con.WS_OVERLAPPEDWINDOW,
        "exstyle": fake_win32con.WS_EX_TOPMOST | fake_win32con.WS_EX_APPWINDOW,
        "props": {},
    }

    def get_window_long(hwnd: int, index: int) -> int:
        """
        返回伪窗口样式。
        :param hwnd: 窗口句柄
        :param index: 样式索引
        :return: 样式值
        """
        calls.append(("GetWindowLong", hwnd, index))
        return state["style"] if index == fake_win32con.GWL_STYLE else state["exstyle"]

    def set_window_long(hwnd: int, index: int, value: int) -> None:
        """
        记录样式写入。
        :param hwnd: 窗口句柄
        :param index: 样式索引
        :param value: 样式值
        :return: None
        """
        calls.append(("SetWindowLong", hwnd, index, value))
        if index == fake_win32con.GWL_STYLE:
            state["style"] = value
        else:
            state["exstyle"] = value

    def set_parent(hwnd: int, parent_hwnd: int) -> None:
        """
        记录父窗口绑定。
        :param hwnd: 窗口句柄
        :param parent_hwnd: 父窗口句柄
        :return: None
        """
        calls.append(("SetParent", hwnd, parent_hwnd))

    def get_client_rect(hwnd: int) -> tuple[int, int, int, int]:
        """
        返回父容器客户区。
        :param hwnd: 父窗口句柄
        :return: 客户区矩形
        """
        calls.append(("GetClientRect", hwnd))
        return 0, 0, 1280, 720

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
        记录窗口尺寸调整。
        :param hwnd: 窗口句柄
        :param insert_after: Z 序参数
        :param x: X 坐标
        :param y: Y 坐标
        :param width: 宽度
        :param height: 高度
        :param flags: SetWindowPos 标志
        :return: None
        """
        calls.append(("SetWindowPos", hwnd, insert_after, x, y, width, height, flags))

    def move_window(
        hwnd: int,
        x: int,
        y: int,
        width: int,
        height: int,
        repaint: bool,
    ) -> None:
        """
        记录 MoveWindow 兜底尺寸同步。
        :param hwnd: 窗口句柄
        :param x: X 坐标
        :param y: Y 坐标
        :param width: 宽度
        :param height: 高度
        :param repaint: 是否重绘
        :return: None
        """
        calls.append(("MoveWindow", hwnd, x, y, width, height, repaint))

    def show_window(hwnd: int, command: int) -> None:
        """
        记录 ShowWindow 调用。
        :param hwnd: 窗口句柄
        :param command: 显示命令
        :return: None
        """
        calls.append(("ShowWindow", hwnd, command))

    def is_window(hwnd: int) -> bool:
        """
        返回伪窗口是否存在。
        :param hwnd: 窗口句柄
        :return: True 表示窗口存在
        """
        calls.append(("IsWindow", hwnd))
        return window_exists

    def post_message(hwnd: int, message: int, wparam: int, lparam: int) -> None:
        """
        记录异步关闭消息。
        :param hwnd: 窗口句柄
        :param message: 消息编号
        :param wparam: wParam
        :param lparam: lParam
        :return: None
        """
        calls.append(("PostMessage", hwnd, message, wparam, lparam))

    def set_prop(hwnd: int, name: str, value: int) -> None:
        """
        记录 Win32 窗口属性。
        :param hwnd: 窗口句柄
        :param name: 属性名
        :param value: 属性值
        :return: None
        """
        calls.append(("SetProp", hwnd, name, value))
        state["props"][(hwnd, name)] = value

    def get_prop(hwnd: int, name: str) -> int:
        """
        返回已记录的 Win32 窗口属性。
        :param hwnd: 窗口句柄
        :param name: 属性名
        :return: 属性值；不存在时返回 0
        """
        calls.append(("GetProp", hwnd, name))
        return int(state["props"].get((hwnd, name), 0))

    def remove_prop(hwnd: int, name: str) -> None:
        """
        移除 Win32 窗口属性。
        :param hwnd: 窗口句柄
        :param name: 属性名
        :return: None
        """
        calls.append(("RemoveProp", hwnd, name))
        state["props"].pop((hwnd, name), None)

    fake_win32gui.GetWindowLong = get_window_long
    fake_win32gui.SetWindowLong = set_window_long
    fake_win32gui.SetParent = set_parent
    fake_win32gui.GetClientRect = get_client_rect
    fake_win32gui.SetWindowPos = set_window_pos
    fake_win32gui.MoveWindow = move_window
    fake_win32gui.ShowWindow = show_window
    fake_win32gui.IsWindow = is_window
    fake_win32gui.PostMessage = post_message
    fake_win32gui.SetProp = set_prop
    fake_win32gui.GetProp = get_prop
    fake_win32gui.RemoveProp = remove_prop
    monkeypatch.setitem(sys.modules, "win32con", fake_win32con)
    monkeypatch.setitem(sys.modules, "win32gui", fake_win32gui)
    return fake_win32con


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


def test_embed_slideshow_window_reparents_and_fills_container(
    monkeypatch: MonkeyPatch,
) -> None:
    """嵌入 PPT 时应改成子窗口、清理顶层样式并铺满父容器。"""
    calls: list[tuple[object, ...]] = []
    win32con = _install_fake_embed_win32(monkeypatch, calls)

    size = embed_slideshow_window(909, 2001)

    style_calls = [
        call for call in calls
        if call[0] == "SetWindowLong" and call[2] == win32con.GWL_STYLE
    ]
    exstyle_calls = [
        call for call in calls
        if call[0] == "SetWindowLong" and call[2] == win32con.GWL_EXSTYLE
    ]
    assert size == (1280, 720)
    assert style_calls
    embedded_style = int(style_calls[-1][3])
    assert embedded_style & win32con.WS_CHILD
    assert embedded_style & win32con.WS_VISIBLE
    assert not embedded_style & win32con.WS_POPUP
    assert not embedded_style & win32con.WS_OVERLAPPEDWINDOW
    assert exstyle_calls
    embedded_exstyle = int(exstyle_calls[-1][3])
    assert not embedded_exstyle & win32con.WS_EX_TOPMOST
    assert not embedded_exstyle & win32con.WS_EX_APPWINDOW
    assert ("ShowWindow", 909, win32con.SW_HIDE) in calls
    assert ("SetParent", 909, 2001) in calls
    assert ("SetProp", 909, EMBEDDED_SLIDESHOW_PROP, 2001) in calls
    assert any(
        call[0] == "SetWindowPos"
        and call[1:6] == (909, win32con.HWND_TOP, 0, 0, 1280)
        and call[6] == 720
        and int(call[7]) & win32con.SWP_FRAMECHANGED
        and int(call[7]) & win32con.SWP_SHOWWINDOW
        and int(call[7]) & win32con.SWP_NOACTIVATE
        for call in calls
    )
    assert ("MoveWindow", 909, 0, 0, 1280, 720, True) in calls


def test_embed_slideshow_window_rejects_zero_hwnd() -> None:
    """PPT HWND 或父容器 HWND 为空时应拒绝嵌入。"""
    import pytest

    with pytest.raises(RuntimeError, match="HWND 无效"):
        embed_slideshow_window(0, 2001)
    with pytest.raises(RuntimeError, match="HWND 无效"):
        embed_slideshow_window(909, 0)


def test_hide_embedded_slideshow_window_uses_sw_hide(
    monkeypatch: MonkeyPatch,
) -> None:
    """低延迟切源时应直接隐藏嵌入式子窗口。"""
    calls: list[tuple[object, ...]] = []
    win32con = _install_fake_embed_win32(monkeypatch, calls)

    hide_embedded_slideshow_window(909)

    assert ("ShowWindow", 909, win32con.SW_HIDE) in calls


def test_show_embedded_slideshow_window_restores_and_resizes(
    monkeypatch: MonkeyPatch,
) -> None:
    """新源打开失败后应显示旧 PPT 子窗口并重新同步父容器尺寸。"""
    calls: list[tuple[object, ...]] = []
    win32con = _install_fake_embed_win32(monkeypatch, calls)

    size = show_embedded_slideshow_window(909, 2001)

    assert size == (1280, 720)
    assert ("ShowWindow", 909, win32con.SW_SHOW) in calls
    assert ("MoveWindow", 909, 0, 0, 1280, 720, True) in calls


def test_close_embedded_slideshow_window_hides_and_posts_close(
    monkeypatch: MonkeyPatch,
) -> None:
    """关闭嵌入式 PPT 时不应恢复成可见顶层窗口，只发送关闭请求。"""
    calls: list[tuple[object, ...]] = []
    win32con = _install_fake_embed_win32(monkeypatch, calls)

    close_embedded_slideshow_window(909)

    assert ("ShowWindow", 909, win32con.SW_HIDE) in calls
    assert ("PostMessage", 909, win32con.WM_CLOSE, 0, 0) in calls


def test_find_slideshow_hwnd_prefers_com_hwnd(monkeypatch: MonkeyPatch) -> None:
    """COM 直接返回新且有效的 HWND 时应直接使用，避免 Win32 枚举误判。"""
    logger = logging.getLogger(__name__)
    slideshow_window = type("_SlideShowWindowStub", (), {"HWND": 101})()
    _install_fake_win32gui(monkeypatch, {101: ("screenClass", True)})
    hwnd = find_slideshow_hwnd(slideshow_window, logger, existing_hwnds=set())
    assert hwnd == 101


def test_find_slideshow_hwnd_rejects_embedded_com_hwnd(
    monkeypatch: MonkeyPatch,
) -> None:
    """COM 返回已嵌入旧 HWND 时不应重新认领，避免第二个 PPT 抢占第一个窗口。"""
    logger = logging.getLogger(__name__)
    slideshow_window = type("_SlideShowWindowStub", (), {"HWND": 101})()
    _install_fake_win32gui(
        monkeypatch,
        {101: ("screenClass", True)},
        embedded_hwnds={101},
    )

    hwnd = find_slideshow_hwnd(
        slideshow_window,
        logger,
        existing_hwnds=set(),
        timeout_seconds=0.0,
        allow_existing_when_unique=True,
    )

    assert hwnd == 0


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


def test_embed_marks_owner_token_and_mismatched_close_is_skipped(
    monkeypatch: MonkeyPatch,
) -> None:
    """嵌入时写入归属 token；旧适配器 token 不匹配时不得关闭被复用的窗口。"""
    from scp_cv.player.adapters.ppt_window_registry import (
        unmark_embedded_slideshow_window,
    )

    calls: list[tuple[object, ...]] = []
    win32con = _install_fake_embed_win32(monkeypatch, calls)
    try:
        embed_slideshow_window(909, 2001, 1111)
        assert ("SetProp", 909, EMBEDDED_SLIDESHOW_PROP, 1111) in calls

        calls.clear()
        close_embedded_slideshow_window(909, 2222)
        assert ("ShowWindow", 909, win32con.SW_HIDE) not in calls
        assert ("PostMessage", 909, win32con.WM_CLOSE, 0, 0) not in calls

        close_embedded_slideshow_window(909, 1111)
        assert ("ShowWindow", 909, win32con.SW_HIDE) in calls
        assert ("PostMessage", 909, win32con.WM_CLOSE, 0, 0) in calls
    finally:
        unmark_embedded_slideshow_window(909)


def test_close_without_owner_token_keeps_legacy_behavior(
    monkeypatch: MonkeyPatch,
) -> None:
    """不携带 token 的关闭调用应保持历史行为，不做归属校验。"""
    from scp_cv.player.adapters.ppt_window_registry import (
        unmark_embedded_slideshow_window,
    )

    calls: list[tuple[object, ...]] = []
    win32con = _install_fake_embed_win32(monkeypatch, calls)
    try:
        embed_slideshow_window(909, 2001, 1111)
        calls.clear()

        close_embedded_slideshow_window(909)

        assert ("PostMessage", 909, win32con.WM_CLOSE, 0, 0) in calls
    finally:
        unmark_embedded_slideshow_window(909)
