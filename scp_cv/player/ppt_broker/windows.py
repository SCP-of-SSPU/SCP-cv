#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PowerPoint Broker 的 Win32 放映窗口识别与嵌入 Adapter。
@Project : SCP-cv
@File : windows.py
@Author : Qintsg
@Date : 2026-07-11
'''
from __future__ import annotations

import logging
import time
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol

from scp_cv.player.ppt_broker.window_handles import (
    normalize_hwnd,
    read_com_slideshow_hwnd,
)
from scp_cv.player.ppt_broker.window_diagnostics import describe_process_windows
from scp_cv.player.ppt_broker.window_hosts import BrokerWindowHostRegistry
from scp_cv.player.ppt_broker.window_titles import (
    looks_like_slideshow_title,
    matches_expected_presentation_title,
    normalize_window_title,
)

_SLIDESHOW_CLASS_NAMES = frozenset({"screenClass", "paneClassDC", "PPTFrameClass"})
_EMBEDDED_WINDOW_PROPERTY = "SCP_CV_EMBEDDED_PPT_SLIDESHOW"

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class WindowInfo:
    """诊断窗口候选所需的普通数据。"""

    hwnd: int
    class_name: str
    title: str
    process_id: int


class WindowResolutionError(RuntimeError):
    """无法唯一认领本次 PowerPoint 放映窗口。"""


class SlideshowWindowPort(Protocol):
    """PowerPoint 后端所需的 Win32 窗口操作 seam。"""

    def snapshot(self, process_id: int) -> dict[int, WindowInfo]: ...

    def resolve(
        self,
        slideshow_window: object,
        before: dict[int, WindowInfo],
        process_id: int,
        forbidden_hwnds: Iterable[int],
        expected_presentation_name: str = "",
    ) -> int: ...

    def embed(self, hwnd: int, parent_hwnd: int, owner_token: int) -> tuple[int, int]: ...

    def hide(self, hwnd: int) -> None: ...

    def show(self, hwnd: int, parent_hwnd: int) -> None: ...

    def resize(self, hwnd: int, parent_hwnd: int) -> tuple[int, int]: ...

    def prepare_close(self, hwnd: int, owner_token: int) -> None: ...

    def close(self, hwnd: int, owner_token: int) -> None: ...


class _DefaultWin32Constants:
    """测试替身未提供 win32con 时使用的 Win32 常量。"""

    GWL_STYLE = -16
    GWL_EXSTYLE = -20
    WS_POPUP = 0x80000000
    WS_OVERLAPPEDWINDOW = 0x00CF0000
    WS_CHILD = 0x40000000
    WS_VISIBLE = 0x10000000
    WS_EX_TOPMOST = 0x00000008
    WS_EX_APPWINDOW = 0x00040000
    SW_HIDE = 0
    SW_SHOW = 5
    HWND_TOP = 0
    SWP_NOZORDER = 0x0004
    SWP_NOACTIVATE = 0x0010
    SWP_FRAMECHANGED = 0x0020
    SWP_SHOWWINDOW = 0x0040
    WM_CLOSE = 0x0010


class SystemWindowPort:
    """使用 pywin32 严格识别并嵌入 PowerPoint 放映窗口。"""

    def __init__(
        self,
        win32gui: object | None = None,
        win32process: object | None = None,
        win32con: object | None = None,
        *,
        class_names: Iterable[str] | None = None,
        timeout_seconds: float = 12.0,
        poll_interval_seconds: float = 0.05,
    ) -> None:
        if win32gui is None:
            import win32gui as imported_win32gui

            win32gui = imported_win32gui
        if win32process is None:
            import win32process as imported_win32process

            win32process = imported_win32process
        if win32con is None:
            try:
                import win32con as imported_win32con

                win32con = imported_win32con
            except Exception:
                win32con = _DefaultWin32Constants()
        self._gui = win32gui
        self._process = win32process
        self._con = win32con
        self._class_names = frozenset(class_names or _SLIDESHOW_CLASS_NAMES)
        self._timeout_seconds = max(0.0, timeout_seconds)
        self._poll_interval_seconds = max(0.001, poll_interval_seconds)
        self._hosts = BrokerWindowHostRegistry(self._gui, self._con)

    def snapshot(self, process_id: int) -> dict[int, WindowInfo]:
        """枚举当前进程可作为放映窗口的顶层窗口。"""
        candidates: dict[int, WindowInfo] = {}

        def collect(hwnd: int, _extra: object) -> bool:
            info = self._candidate_info(int(hwnd), process_id)
            if info is not None:
                candidates[info.hwnd] = info
            return True

        self._gui.EnumWindows(collect, None)  # type: ignore[attr-defined]
        return candidates

    def resolve(
        self,
        slideshow_window: object,
        before: dict[int, WindowInfo],
        process_id: int,
        forbidden_hwnds: Iterable[int],
        expected_presentation_name: str = "",
    ) -> int:
        """优先验证 COM HWND，否则只接受本次新增的唯一候选。"""
        forbidden = {normalize_hwnd(hwnd) for hwnd in forbidden_hwnds}
        deadline = time.monotonic() + self._timeout_seconds
        new_candidates: list[WindowInfo] = []
        observed_candidates: list[WindowInfo] = []
        com_hwnd = 0
        while True:
            com_hwnd = read_com_slideshow_hwnd(slideshow_window)
            if com_hwnd and com_hwnd not in forbidden:
                if self._com_candidate_info(com_hwnd, process_id) is not None:
                    return com_hwnd

            after = self.snapshot(process_id)
            observed_candidates = [
                info
                for hwnd, info in after.items()
                if hwnd not in before and hwnd not in forbidden
            ]
            new_candidates = [
                info
                for info in observed_candidates
                if matches_expected_presentation_title(
                    info.title,
                    expected_presentation_name,
                )
            ]
            if len(new_candidates) == 1:
                return new_candidates[0].hwnd
            if len(new_candidates) > 1 or time.monotonic() >= deadline:
                break
            time.sleep(
                min(
                    self._poll_interval_seconds,
                    max(0.0, deadline - time.monotonic()),
                )
            )
        details = ", ".join(
            f"HWND={info.hwnd}, class={info.class_name!r}, "
            f"title={info.title!r}, pid={info.process_id}"
            for info in (new_candidates or observed_candidates)
        )
        if not details:
            details = "无新增候选"
        process_windows = describe_process_windows(
            self._gui,
            self._process,
            process_id,
        )
        raise WindowResolutionError(
            f"无法唯一确定本次 PowerPoint 放映窗口：{details}; "
            f"com_hwnd={com_hwnd}; pid_windows={process_windows}"
        )

    def embed(self, hwnd: int, parent_hwnd: int, owner_token: int) -> tuple[int, int]:
        """嵌入放映窗口，并验证 HWND、父窗口、子样式和尺寸。"""
        hwnd = normalize_hwnd(hwnd)
        parent_hwnd = normalize_hwnd(parent_hwnd)
        if not hwnd or not parent_hwnd:
            raise RuntimeError("PPT 放映窗口或父容器 HWND 无效，无法嵌入")
        if not bool(self._gui.IsWindow(hwnd)):  # type: ignore[attr-defined]
            raise RuntimeError(f"PPT 放映窗口 HWND={hwnd} 已失效")
        original_parent = int(self._gui.GetParent(hwnd) or 0)  # type: ignore[attr-defined]
        original_style = int(
            self._gui.GetWindowLong(hwnd, self._con.GWL_STYLE)  # type: ignore[attr-defined]
        )
        original_extended_style = int(
            self._gui.GetWindowLong(hwnd, self._con.GWL_EXSTYLE)  # type: ignore[attr-defined]
        )
        render_parent_hwnd = self._hosts.create_for(hwnd, parent_hwnd)
        embedded_style = (
            original_style
            & ~self._con.WS_POPUP
            & ~self._con.WS_OVERLAPPEDWINDOW
            | self._con.WS_CHILD
            | self._con.WS_VISIBLE
        )
        embedded_extended_style = original_extended_style
        embedded_extended_style &= ~self._con.WS_EX_TOPMOST
        embedded_extended_style &= ~self._con.WS_EX_APPWINDOW
        try:
            self._gui.ShowWindow(hwnd, self._con.SW_HIDE)  # type: ignore[attr-defined]
            self._gui.SetWindowLong(  # type: ignore[attr-defined]
                hwnd,
                self._con.GWL_STYLE,
                embedded_style,
            )
            self._gui.SetWindowLong(  # type: ignore[attr-defined]
                hwnd,
                self._con.GWL_EXSTYLE,
                embedded_extended_style,
            )
            self._gui.SetParent(hwnd, render_parent_hwnd)  # type: ignore[attr-defined]
            set_prop = getattr(self._gui, "SetProp", None)
            if callable(set_prop):
                set_prop(hwnd, _EMBEDDED_WINDOW_PROPERTY, int(owner_token or 1))
            width, height = self._resize(hwnd, render_parent_hwnd)

            if not bool(self._gui.IsWindow(hwnd)):  # type: ignore[attr-defined]
                raise RuntimeError(f"PPT 放映窗口 HWND={hwnd} 在嵌入后失效")
            actual_parent = int(self._gui.GetParent(hwnd) or 0)  # type: ignore[attr-defined]
            if actual_parent != render_parent_hwnd:
                raise RuntimeError(
                    "PPT 放映窗口父句柄校验失败："
                    f"expected={render_parent_hwnd}, actual={actual_parent}"
                )
            host_hwnd = self._hosts.host_for(hwnd)
            if host_hwnd:
                host_parent = int(self._gui.GetParent(host_hwnd) or 0)  # type: ignore[attr-defined]
                if host_parent != parent_hwnd:
                    raise RuntimeError(
                        "PowerPoint Broker 宿主父句柄校验失败："
                        f"expected={parent_hwnd}, actual={host_parent}"
                    )
            actual_style = int(
                self._gui.GetWindowLong(hwnd, self._con.GWL_STYLE)  # type: ignore[attr-defined]
            )
            if actual_style & self._con.WS_CHILD == 0:
                raise RuntimeError(f"PPT 放映窗口 HWND={hwnd} 未设置 WS_CHILD")
            if width <= 0 or height <= 0:
                raise RuntimeError(
                    "PPT 放映子窗口实际尺寸无效："
                    f"width={width}, height={height}"
                )
            self._gui.ShowWindow(hwnd, self._con.SW_SHOW)  # type: ignore[attr-defined]
            return width, height
        except Exception:
            self._rollback_embedding(
                hwnd,
                original_parent,
                original_style,
                original_extended_style,
            )
            self._hosts.destroy_for(hwnd)
            raise

    def hide(self, hwnd: int) -> None:
        """尽力隐藏仍存在的放映窗口。"""
        hwnd = normalize_hwnd(hwnd)
        if hwnd and self._window_exists(hwnd):
            self._gui.ShowWindow(hwnd, self._con.SW_HIDE)  # type: ignore[attr-defined]
            self._hosts.hide_for(hwnd)

    def show(self, hwnd: int, parent_hwnd: int) -> None:
        """恢复已嵌入窗口并重新同步尺寸。"""
        hwnd = normalize_hwnd(hwnd)
        if not hwnd or not self._window_exists(hwnd):
            return
        player_parent_hwnd = normalize_hwnd(parent_hwnd)
        render_parent_hwnd = self._hosts.render_parent(hwnd, player_parent_hwnd)
        self._resize(hwnd, render_parent_hwnd)
        self._hosts.show_for(hwnd)
        self._gui.ShowWindow(hwnd, self._con.SW_SHOW)  # type: ignore[attr-defined]

    def resize(self, hwnd: int, parent_hwnd: int) -> tuple[int, int]:
        """按 Player 容器当前客户区同步 Broker host 与放映窗口。"""
        hwnd = normalize_hwnd(hwnd)
        player_parent_hwnd = normalize_hwnd(parent_hwnd)
        if not hwnd or not player_parent_hwnd or not self._window_exists(hwnd):
            raise RuntimeError("PPT 放映窗口或父容器 HWND 已失效，无法同步尺寸")
        render_parent_hwnd = self._hosts.render_parent(hwnd, player_parent_hwnd)
        width, height = self._resize(hwnd, render_parent_hwnd)
        if width <= 0 or height <= 0:
            raise RuntimeError(
                "PPT 放映子窗口同步后的实际尺寸无效："
                f"width={width}, height={height}"
            )
        return width, height

    def close(self, hwnd: int, owner_token: int) -> None:
        """只关闭 owner_token 仍匹配的嵌入式放映窗口。"""
        hwnd = normalize_hwnd(hwnd)
        if not hwnd or not self._window_exists(hwnd):
            self._hosts.destroy_for(hwnd)
            return
        get_prop = getattr(self._gui, "GetProp", None)
        if callable(get_prop):
            current_owner = int(get_prop(hwnd, _EMBEDDED_WINDOW_PROPERTY) or 0)
            if current_owner and current_owner != int(owner_token):
                return
        self.hide(hwnd)
        get_window_text = getattr(self._gui, "GetWindowText", None)
        if not callable(get_window_text) or not looks_like_slideshow_title(
            normalize_window_title(str(get_window_text(hwnd)))
        ):
            self._hosts.destroy_for(hwnd)
            return
        post_message = getattr(self._gui, "PostMessage", None)
        if callable(post_message):
            post_message(hwnd, self._con.WM_CLOSE, 0, 0)
        self._hosts.destroy_for(hwnd)

    def prepare_close(self, hwnd: int, owner_token: int) -> None:
        """View.Exit 前恢复顶层窗口语义并释放远端 Player 父链。"""
        hwnd = normalize_hwnd(hwnd)
        if not hwnd or not self._window_exists(hwnd):
            self._hosts.destroy_for(hwnd)
            return
        get_prop = getattr(self._gui, "GetProp", None)
        if callable(get_prop):
            current_owner = int(get_prop(hwnd, _EMBEDDED_WINDOW_PROPERTY) or 0)
            if current_owner and current_owner != int(owner_token):
                return
        self.hide(hwnd)
        host_detached = self._hosts.detach_for_close(hwnd)
        current_style = int(
            self._gui.GetWindowLong(hwnd, self._con.GWL_STYLE)  # type: ignore[attr-defined]
        )
        detached_style = (
            current_style
            & ~self._con.WS_CHILD
            & ~self._con.WS_VISIBLE
            | self._con.WS_POPUP
        )
        self._gui.SetWindowLong(  # type: ignore[attr-defined]
            hwnd,
            self._con.GWL_STYLE,
            detached_style,
        )
        self._gui.SetParent(hwnd, 0)  # type: ignore[attr-defined]
        actual_parent = int(self._gui.GetParent(hwnd) or 0)  # type: ignore[attr-defined]
        if actual_parent != 0:
            raise RuntimeError(
                "PowerPoint 放映窗口关闭前无法恢复为顶层窗口："
                f"hwnd={hwnd}, actual_parent={actual_parent}"
            )
        if host_detached:
            self._hosts.destroy_for(hwnd)

    def _candidate_info(self, hwnd: int, process_id: int) -> WindowInfo | None:
        try:
            if not bool(self._gui.IsWindow(hwnd)):  # type: ignore[attr-defined]
                return None
            if not bool(self._gui.IsWindowVisible(hwnd)):  # type: ignore[attr-defined]
                return None
            class_name = str(self._gui.GetClassName(hwnd))  # type: ignore[attr-defined]
            if class_name not in self._class_names:
                return None
            _, window_process_id = self._process.GetWindowThreadProcessId(hwnd)  # type: ignore[attr-defined]
            if process_id and int(window_process_id) != int(process_id):
                return None
            title = str(self._gui.GetWindowText(hwnd))  # type: ignore[attr-defined]
            normalized_title = normalize_window_title(title)
            if not normalized_title or not looks_like_slideshow_title(
                normalized_title
            ):
                return None
            return WindowInfo(hwnd, class_name, title, int(window_process_id))
        except Exception:
            return None

    def _com_candidate_info(self, hwnd: int, process_id: int) -> WindowInfo | None:
        """校验 COM 明确返回的 HWND；标题仅用于诊断，不作为认领前提。"""
        try:
            if not bool(self._gui.IsWindow(hwnd)):  # type: ignore[attr-defined]
                return None
            class_name = str(self._gui.GetClassName(hwnd))  # type: ignore[attr-defined]
            if class_name not in self._class_names:
                return None
            _, window_process_id = self._process.GetWindowThreadProcessId(hwnd)  # type: ignore[attr-defined]
            if process_id and int(window_process_id) != int(process_id):
                return None
            title = str(self._gui.GetWindowText(hwnd))  # type: ignore[attr-defined]
            return WindowInfo(hwnd, class_name, title, int(window_process_id))
        except Exception:
            return None

    def _resize(self, hwnd: int, parent_hwnd: int) -> tuple[int, int]:
        left, top, right, bottom = self._gui.GetClientRect(parent_hwnd)  # type: ignore[attr-defined]
        target_width = max(0, int(right) - int(left))
        target_height = max(0, int(bottom) - int(top))
        self._gui.SetWindowPos(  # type: ignore[attr-defined]
            hwnd,
            self._con.HWND_TOP,
            0,
            0,
            target_width,
            target_height,
            self._con.SWP_NOZORDER
            | self._con.SWP_NOACTIVATE
            | self._con.SWP_FRAMECHANGED
            | self._con.SWP_SHOWWINDOW,
        )
        child_left, child_top, child_right, child_bottom = self._gui.GetClientRect(  # type: ignore[attr-defined]
            hwnd
        )
        actual_width = max(0, int(child_right) - int(child_left))
        actual_height = max(0, int(child_bottom) - int(child_top))
        return actual_width, actual_height

    def _rollback_embedding(
        self,
        hwnd: int,
        original_parent: int,
        original_style: int,
        original_extended_style: int,
    ) -> None:
        """尽力撤销失败嵌入留下的 Win32 parent、property 和样式。"""
        rollback_steps = (
            lambda: self._gui.SetParent(hwnd, original_parent),  # type: ignore[attr-defined]
            lambda: self._gui.SetWindowLong(  # type: ignore[attr-defined]
                hwnd,
                self._con.GWL_STYLE,
                original_style,
            ),
            lambda: self._gui.SetWindowLong(  # type: ignore[attr-defined]
                hwnd,
                self._con.GWL_EXSTYLE,
                original_extended_style,
            ),
        )
        remove_prop = getattr(self._gui, "RemoveProp", None)
        if callable(remove_prop):
            try:
                remove_prop(hwnd, _EMBEDDED_WINDOW_PROPERTY)
            except Exception as rollback_error:
                logger.warning("撤销 PPT 嵌入窗口 property 失败：%s", rollback_error)
        for rollback_step in rollback_steps:
            try:
                rollback_step()
            except Exception as rollback_error:
                logger.warning("撤销 PPT 嵌入窗口 parent/style 失败：%s", rollback_error)

    def _window_exists(self, hwnd: int) -> bool:
        try:
            return bool(self._gui.IsWindow(hwnd))  # type: ignore[attr-defined]
        except Exception:
            return False

__all__ = [
    "SlideshowWindowPort",
    "SystemWindowPort",
    "WindowInfo",
    "WindowResolutionError",
    "normalize_hwnd",
    "normalize_window_title",
    "read_com_slideshow_hwnd",
]
