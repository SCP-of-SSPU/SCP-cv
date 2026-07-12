#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PowerPoint Broker 放映窗口认领测试。
@Project : SCP-cv
@File : test_ppt_broker_windows.py
@Author : Qintsg
@Date : 2026-07-11
'''
from __future__ import annotations

from collections.abc import Callable

import pytest

from scp_cv.player.ppt_broker.windows import (
    SystemWindowPort,
    WindowResolutionError,
    read_com_slideshow_hwnd,
)


class _AmbiguousWin32Gui:
    """同时出现两个合格放映窗口的 Win32 替身。"""

    @staticmethod
    def EnumWindows(
        callback: Callable[[int, object], bool],
        extra: object,
    ) -> None:
        callback(101, extra)
        callback(202, extra)

    @staticmethod
    def IsWindow(_hwnd: int) -> bool:
        return True

    @staticmethod
    def IsWindowVisible(_hwnd: int) -> bool:
        return True

    @staticmethod
    def GetClassName(_hwnd: int) -> str:
        return "screenClass"

    @staticmethod
    def GetWindowText(hwnd: int) -> str:
        return f"PowerPoint 幻灯片放映 - candidate-{hwnd}"


class _PowerPointProcess:
    """所有候选均属于同一个 PowerPoint 进程。"""

    @staticmethod
    def GetWindowThreadProcessId(_hwnd: int) -> tuple[int, int]:
        return 1, 4242


class _NoComHwnd:
    """模拟 COM 暂时无法返回 HWND。"""

    HWND = 0


class _DelayedWin32Gui(_AmbiguousWin32Gui):
    """前两次枚举为空，第三次才出现唯一放映窗口。"""

    calls = 0

    @classmethod
    def EnumWindows(
        cls,
        callback: Callable[[int, object], bool],
        extra: object,
    ) -> None:
        cls.calls += 1
        if cls.calls >= 3:
            callback(303, extra)


class _EmptyTitleWin32Gui(_AmbiguousWin32Gui):
    """只有 PID/class 合格但标题为空的窗口。"""

    @staticmethod
    def EnumWindows(
        callback: Callable[[int, object], bool],
        extra: object,
    ) -> None:
        callback(404, extra)

    @staticmethod
    def GetWindowText(_hwnd: int) -> str:
        return ""


class _MixedPresentationTitleWin32Gui(_AmbiguousWin32Gui):
    """同一 PowerPoint PID 内同时出现项目放映与用户放映。"""

    @staticmethod
    def GetWindowText(hwnd: int) -> str:
        if hwnd == 101:
            return "PowerPoint 幻灯片放映  - 演示文稿1 - PowerPoint"
        return "PowerPoint 幻灯片放映 - user-document"


class _FailingEmbedWin32Gui:
    """嵌入修改完成后让 HWND 校验失败的 Win32 替身。"""

    def __init__(self) -> None:
        self.hwnd = 101
        self.parent = 700
        self.style = 0x80CF0000
        self.extended_style = 0x00040008
        self.is_window_calls = 0

    def IsWindow(self, _hwnd: int) -> bool:
        self.is_window_calls += 1
        return self.is_window_calls == 1

    def ShowWindow(self, *_args: object) -> None:
        return

    def GetWindowLong(self, _hwnd: int, index: int) -> int:
        return self.style if index == -16 else self.extended_style

    def SetWindowLong(self, _hwnd: int, index: int, value: int) -> None:
        if index == -16:
            self.style = value
        else:
            self.extended_style = value

    def GetParent(self, _hwnd: int) -> int:
        return self.parent

    def SetParent(self, _hwnd: int, parent_hwnd: int) -> None:
        self.parent = parent_hwnd

    @staticmethod
    def GetClientRect(_hwnd: int) -> tuple[int, int, int, int]:
        return 0, 0, 960, 540

    @staticmethod
    def SetWindowPos(*_args: object) -> None:
        return


class _ZeroSizedChildWin32Gui(_FailingEmbedWin32Gui):
    """父容器尺寸有效，但嵌入后的子窗口实际尺寸仍为零。"""

    def IsWindow(self, _hwnd: int) -> bool:
        return True

    def GetClientRect(self, hwnd: int) -> tuple[int, int, int, int]:
        if hwnd == self.hwnd:
            return 0, 0, 0, 0
        return 0, 0, 960, 540


class _IntermediateHostWin32Gui:
    """支持创建 Broker 本进程原生宿主的 Win32 替身。"""

    slideshow_hwnd = 101
    player_parent_hwnd = 900
    host_hwnd = 501

    def __init__(self) -> None:
        self.parents = {
            self.slideshow_hwnd: 0,
            self.player_parent_hwnd: 0,
        }
        self.styles = {
            self.slideshow_hwnd: 0x80CF0000,
            self.player_parent_hwnd: 0,
        }
        self.extended_styles = {
            self.slideshow_hwnd: 0x00040008,
            self.player_parent_hwnd: 0,
        }
        self.rectangles = {
            self.slideshow_hwnd: (0, 0, 960, 540),
            self.player_parent_hwnd: (0, 0, 960, 540),
        }
        self.created_host_parent = -1

    def CreateWindowEx(self, *_args: object) -> int:
        self.created_host_parent = int(_args[8])
        self.parents[self.host_hwnd] = self.created_host_parent
        self.styles[self.host_hwnd] = int(_args[3])
        self.extended_styles[self.host_hwnd] = int(_args[0])
        self.rectangles[self.host_hwnd] = (0, 0, 960, 540)
        return self.host_hwnd

    def IsWindow(self, hwnd: int) -> bool:
        return hwnd in self.parents

    @staticmethod
    def ShowWindow(*_args: object) -> None:
        return

    def GetWindowLong(self, hwnd: int, index: int) -> int:
        return self.styles[hwnd] if index == -16 else self.extended_styles[hwnd]

    def SetWindowLong(self, hwnd: int, index: int, value: int) -> None:
        if index == -16:
            self.styles[hwnd] = value
        else:
            self.extended_styles[hwnd] = value

    def GetParent(self, hwnd: int) -> int:
        return self.parents[hwnd]

    def SetParent(self, hwnd: int, parent_hwnd: int) -> None:
        self.parents[hwnd] = parent_hwnd

    def GetClientRect(self, hwnd: int) -> tuple[int, int, int, int]:
        return self.rectangles[hwnd]

    def SetWindowPos(
        self,
        hwnd: int,
        _insert_after: int,
        _x: int,
        _y: int,
        width: int,
        height: int,
        _flags: int,
    ) -> None:
        self.rectangles[hwnd] = (0, 0, width, height)

    def DestroyWindow(self, hwnd: int) -> None:
        self.parents.pop(hwnd, None)


class _CloseIdentityWin32Gui:
    """记录 close 是否把 WM_CLOSE 误发给已复用的 Application frame。"""

    def __init__(self, title: str) -> None:
        self.title = title
        self.posted: list[tuple[int, int]] = []

    @staticmethod
    def IsWindow(_hwnd: int) -> bool:
        return True

    @staticmethod
    def GetProp(_hwnd: int, _name: str) -> int:
        return 42

    @staticmethod
    def ShowWindow(*_args: object) -> None:
        return

    def GetWindowText(self, _hwnd: int) -> str:
        return self.title

    def PostMessage(
        self,
        hwnd: int,
        message: int,
        _wparam: int,
        _lparam: int,
    ) -> None:
        self.posted.append((hwnd, message))


def test_embed_uses_broker_owned_intermediate_host_when_available() -> None:
    """PowerPoint 的直接父窗口应由 Broker 创建，再嵌入远端 Player 容器。"""
    gui = _IntermediateHostWin32Gui()
    windows = SystemWindowPort(gui, _PowerPointProcess())

    windows.embed(gui.slideshow_hwnd, gui.player_parent_hwnd, owner_token=42)

    assert gui.created_host_parent == 0
    assert gui.parents[gui.host_hwnd] == gui.player_parent_hwnd
    assert gui.parents[gui.slideshow_hwnd] == gui.host_hwnd


def test_prepare_close_restores_slideshow_to_top_level_and_destroys_host() -> None:
    """View.Exit 前应恢复 PowerPoint 顶层窗口语义并释放 Broker host。"""
    gui = _IntermediateHostWin32Gui()
    windows = SystemWindowPort(gui, _PowerPointProcess())
    windows.embed(gui.slideshow_hwnd, gui.player_parent_hwnd, owner_token=42)

    windows.prepare_close(gui.slideshow_hwnd, owner_token=42)

    assert gui.parents[gui.slideshow_hwnd] == 0
    assert gui.host_hwnd not in gui.parents
    assert gui.styles[gui.slideshow_hwnd] & 0x40000000 == 0
    assert gui.styles[gui.slideshow_hwnd] & 0x80000000


def test_close_never_posts_wm_close_to_reused_powerpoint_application_frame() -> None:
    """旧放映 HWND 变成普通 PowerPoint frame 后不得关闭外部 Application。"""
    application_frame = _CloseIdentityWin32Gui("PowerPoint")
    windows = SystemWindowPort(application_frame, _PowerPointProcess())

    windows.close(101, owner_token=42)

    assert application_frame.posted == []

    slideshow = _CloseIdentityWin32Gui(
        "PowerPoint 幻灯片放映  -  演示文稿4"
    )
    windows = SystemWindowPort(slideshow, _PowerPointProcess())
    windows.close(101, owner_token=42)

    assert slideshow.posted == [(101, 0x0010)]


def test_resize_resynchronizes_broker_host_and_slideshow_geometry() -> None:
    """Player 容器变化后应同步两级父链的宿主和放映子窗口尺寸。"""
    gui = _IntermediateHostWin32Gui()
    windows = SystemWindowPort(gui, _PowerPointProcess())
    windows.embed(gui.slideshow_hwnd, gui.player_parent_hwnd, owner_token=42)
    gui.rectangles[gui.player_parent_hwnd] = (0, 0, 640, 360)

    windows.resize(gui.slideshow_hwnd, gui.player_parent_hwnd)

    assert gui.rectangles[gui.host_hwnd] == (0, 0, 640, 360)
    assert gui.rectangles[gui.slideshow_hwnd] == (0, 0, 640, 360)


def test_multiple_new_candidates_fail_instead_of_selecting_largest_window() -> None:
    """两个同等候选必须返回带诊断的错误，禁止按尺寸猜测。"""
    windows = SystemWindowPort(_AmbiguousWin32Gui(), _PowerPointProcess())

    with pytest.raises(WindowResolutionError) as captured:
        windows.resolve(_NoComHwnd(), {}, 4242, forbidden_hwnds=())

    message = str(captured.value)
    assert "HWND=101" in message
    assert "HWND=202" in message
    assert "无法唯一确定" in message


def test_resolve_waits_for_delayed_unique_slideshow_window() -> None:
    """PowerPoint Run 返回后异步出现的唯一窗口应在超时内被认领。"""
    _DelayedWin32Gui.calls = 0
    windows = SystemWindowPort(
        _DelayedWin32Gui(),
        _PowerPointProcess(),
        timeout_seconds=0.2,
        poll_interval_seconds=0.001,
    )

    assert windows.resolve(_NoComHwnd(), {}, 4242, forbidden_hwnds=()) == 303


def test_fallback_only_claims_window_matching_requested_presentation() -> None:
    """COM HWND 不可用时不得误认同 PID 中用户新启动的其它放映。"""
    windows = SystemWindowPort(
        _MixedPresentationTitleWin32Gui(),
        _PowerPointProcess(),
        timeout_seconds=0.0,
    )

    assert windows.resolve(
        _NoComHwnd(),
        {},
        4242,
        forbidden_hwnds=(),
        expected_presentation_name="演示文稿1",
    ) == 101


def test_resolve_rejects_candidate_with_empty_title() -> None:
    """PID 与 class 匹配但标题为空时不得认领为 PowerPoint 放映窗口。"""
    windows = SystemWindowPort(
        _EmptyTitleWin32Gui(),
        _PowerPointProcess(),
        timeout_seconds=0.0,
    )

    with pytest.raises(WindowResolutionError, match="无法唯一确定"):
        windows.resolve(_NoComHwnd(), {}, 4242, forbidden_hwnds=())


def test_resolve_accepts_valid_com_hwnd_without_top_level_title() -> None:
    """COM 明确返回的 HWND 只需校验窗口、PID 与 class，不依赖顶层标题。"""

    class _ComSlideShowWindow:
        HWND = 404

    windows = SystemWindowPort(
        _EmptyTitleWin32Gui(),
        _PowerPointProcess(),
        timeout_seconds=0.0,
    )

    assert windows.resolve(
        _ComSlideShowWindow(),
        {},
        4242,
        forbidden_hwnds=(),
    ) == 404


def test_embed_validation_failure_restores_original_parent_and_styles() -> None:
    """嵌入后验证失败必须撤销 SetParent 以及普通/扩展样式修改。"""
    gui = _FailingEmbedWin32Gui()
    original_parent = gui.parent
    original_style = gui.style
    original_extended_style = gui.extended_style
    windows = SystemWindowPort(gui, _PowerPointProcess())

    with pytest.raises(RuntimeError, match="嵌入后失效"):
        windows.embed(gui.hwnd, 900, owner_token=42)

    assert gui.parent == original_parent
    assert gui.style == original_style
    assert gui.extended_style == original_extended_style


def test_embed_rejects_zero_sized_actual_child_window() -> None:
    """父容器有尺寸但实际子 HWND 仍为零时，嵌入必须失败并回滚。"""
    gui = _ZeroSizedChildWin32Gui()
    original_parent = gui.parent
    windows = SystemWindowPort(gui, _PowerPointProcess())

    with pytest.raises(RuntimeError, match="实际尺寸无效"):
        windows.embed(gui.hwnd, 900, owner_token=42)

    assert gui.parent == original_parent


def test_read_com_hwnd_unwraps_value_wrapper() -> None:
    """pywin32/ctypes 风格 `.value` 包装的有符号 HWND 应被归一。"""

    class _HwndValue:
        value = -268_435_455

    class _WrappedSlideShowWindow:
        HWND = _HwndValue()

    assert read_com_slideshow_hwnd(_WrappedSlideShowWindow()) == (
        -268_435_455 & 0xFFFFFFFF
    )


def test_read_com_hwnd_falls_back_to_idispatch_property() -> None:
    """直接属性不可读时，应通过 IDispatch PROPERTYGET 取得 HWND。"""

    class _HwndValue:
        value = -268_435_455

    class _OleDispatch:
        """匹配 pywin32 PyIDispatch 的 GetIDsOfNames/Invoke 约定。"""

        def __init__(self) -> None:
            self.invocations: list[tuple[int, int, int, int]] = []

        @staticmethod
        def GetIDsOfNames(name: str) -> int:
            assert name == "HWND"
            return 901

        def Invoke(
            self,
            dispatch_id: int,
            locale_id: int,
            dispatch_flag: int,
            result_wanted: int,
        ) -> object:
            self.invocations.append(
                (dispatch_id, locale_id, dispatch_flag, result_wanted)
            )
            if dispatch_flag != 2:
                raise RuntimeError("PROPERTYGET required")
            return _HwndValue()

    class _DispatchOnlySlideShowWindow:
        def __init__(self, ole_dispatch: _OleDispatch) -> None:
            self._oleobj_ = ole_dispatch

        def __getattr__(self, name: str) -> object:
            if name.casefold() == "hwnd":
                raise AttributeError(name)
            raise AttributeError(name)

    ole_dispatch = _OleDispatch()

    hwnd = read_com_slideshow_hwnd(_DispatchOnlySlideShowWindow(ole_dispatch))

    assert hwnd == (-268_435_455 & 0xFFFFFFFF)
    assert ole_dispatch.invocations == [(901, 0, 2, 1)]
