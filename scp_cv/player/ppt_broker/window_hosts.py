#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PowerPoint Broker 本进程原生宿主窗口注册表。
@Project : SCP-cv
@File : window_hosts.py
@Author : Qintsg
@Date : 2026-07-11
'''
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_HOST_CLASS_NAME = "SCP_cv_PptBrokerHost"
_WS_CLIPCHILDREN = 0x02000000
_WS_CLIPSIBLINGS = 0x04000000


class BrokerWindowHostRegistry:
    """让 PowerPoint 始终以 Broker 自有 HWND 作为直接父窗口。"""

    def __init__(self, win32gui: object, win32con: object) -> None:
        self._gui = win32gui
        self._con = win32con
        self._hosts: dict[int, int] = {}
        self._window_class: tuple[str, int] | None = None

    def create_for(self, slideshow_hwnd: int, player_parent_hwnd: int) -> int:
        """创建 Broker 自有宿主并把它嵌入远端 Player 容器。"""
        create_window = getattr(self._gui, "CreateWindowEx", None)
        if not callable(create_window):
            return player_parent_hwnd
        existing = self._hosts.get(slideshow_hwnd, 0)
        if existing and self._is_window(existing):
            return existing

        class_name, instance_handle = self._ensure_window_class()
        left, top, right, bottom = self._gui.GetClientRect(player_parent_hwnd)  # type: ignore[attr-defined]
        width = max(1, int(right) - int(left))
        height = max(1, int(bottom) - int(top))
        popup_style = int(getattr(self._con, "WS_POPUP", 0x80000000))
        host_hwnd = int(
            create_window(
                0,
                class_name,
                "SCP-cv PowerPoint Broker Host",
                popup_style,
                0,
                0,
                width,
                height,
                0,
                0,
                instance_handle,
                None,
            )
        )
        if host_hwnd <= 0:
            raise RuntimeError("无法创建 PowerPoint Broker 原生宿主窗口")
        try:
            child_style = (
                int(getattr(self._con, "WS_CHILD", 0x40000000))
                | int(getattr(self._con, "WS_VISIBLE", 0x10000000))
                | _WS_CLIPCHILDREN
                | _WS_CLIPSIBLINGS
            )
            self._gui.SetWindowLong(  # type: ignore[attr-defined]
                host_hwnd,
                self._con.GWL_STYLE,
                child_style,
            )
            self._gui.SetParent(host_hwnd, player_parent_hwnd)  # type: ignore[attr-defined]
            self._resize_host(host_hwnd, player_parent_hwnd)
            if not self._is_window(host_hwnd):
                raise RuntimeError("PowerPoint Broker 原生宿主窗口创建后失效")
            actual_parent = int(self._gui.GetParent(host_hwnd) or 0)  # type: ignore[attr-defined]
            if actual_parent != player_parent_hwnd:
                raise RuntimeError(
                    "PowerPoint Broker 宿主父句柄校验失败："
                    f"expected={player_parent_hwnd}, actual={actual_parent}"
                )
            self._gui.ShowWindow(host_hwnd, self._con.SW_SHOW)  # type: ignore[attr-defined]
        except Exception:
            self._destroy_window(host_hwnd)
            raise
        self._hosts[slideshow_hwnd] = host_hwnd
        return host_hwnd

    def render_parent(self, slideshow_hwnd: int, player_parent_hwnd: int) -> int:
        """返回放映窗口的直接父 HWND，并同步中间宿主尺寸。"""
        host_hwnd = self._hosts.get(slideshow_hwnd, 0)
        if not host_hwnd or not self._is_window(host_hwnd):
            return player_parent_hwnd
        self._resize_host(host_hwnd, player_parent_hwnd)
        return host_hwnd

    def show_for(self, slideshow_hwnd: int) -> None:
        """显示仍存在的 Broker 宿主。"""
        host_hwnd = self._hosts.get(slideshow_hwnd, 0)
        if host_hwnd and self._is_window(host_hwnd):
            self._gui.ShowWindow(host_hwnd, self._con.SW_SHOW)  # type: ignore[attr-defined]

    def hide_for(self, slideshow_hwnd: int) -> None:
        """隐藏仍存在的 Broker 宿主。"""
        host_hwnd = self._hosts.get(slideshow_hwnd, 0)
        if host_hwnd and self._is_window(host_hwnd):
            self._gui.ShowWindow(host_hwnd, self._con.SW_HIDE)  # type: ignore[attr-defined]

    def destroy_for(self, slideshow_hwnd: int) -> None:
        """销毁放映对应的中间宿主，幂等清理注册表。"""
        host_hwnd = self._hosts.pop(slideshow_hwnd, 0)
        if host_hwnd:
            self._destroy_window(host_hwnd)

    def detach_for_close(self, slideshow_hwnd: int) -> bool:
        """隐藏宿主并切断到远端 Player 的父链，供 View.Exit 前调用。"""
        host_hwnd = self._hosts.get(slideshow_hwnd, 0)
        if not host_hwnd or not self._is_window(host_hwnd):
            return False
        self._gui.ShowWindow(host_hwnd, self._con.SW_HIDE)  # type: ignore[attr-defined]
        current_style = int(
            self._gui.GetWindowLong(host_hwnd, self._con.GWL_STYLE)  # type: ignore[attr-defined]
        )
        detached_style = (
            current_style
            & ~int(getattr(self._con, "WS_CHILD", 0x40000000))
            & ~int(getattr(self._con, "WS_VISIBLE", 0x10000000))
            | int(getattr(self._con, "WS_POPUP", 0x80000000))
        )
        self._gui.SetWindowLong(  # type: ignore[attr-defined]
            host_hwnd,
            self._con.GWL_STYLE,
            detached_style,
        )
        self._gui.SetParent(host_hwnd, 0)  # type: ignore[attr-defined]
        actual_parent = int(self._gui.GetParent(host_hwnd) or 0)  # type: ignore[attr-defined]
        if actual_parent != 0:
            raise RuntimeError(
                "PowerPoint Broker 宿主关闭前无法脱离 Player："
                f"host_hwnd={host_hwnd}, actual_parent={actual_parent}"
            )
        return True

    def host_for(self, slideshow_hwnd: int) -> int:
        """返回仍存在的 Broker 宿主 HWND。"""
        host_hwnd = self._hosts.get(slideshow_hwnd, 0)
        return host_hwnd if host_hwnd and self._is_window(host_hwnd) else 0

    def _ensure_window_class(self) -> tuple[str, int]:
        if self._window_class is not None:
            return self._window_class
        wnd_class = getattr(self._gui, "WNDCLASS", None)
        register_class = getattr(self._gui, "RegisterClass", None)
        def_window_proc = getattr(self._gui, "DefWindowProc", None)
        if not callable(wnd_class) or not callable(register_class) or def_window_proc is None:
            self._window_class = ("Static", 0)
            return self._window_class
        try:
            import win32api

            instance_handle = int(win32api.GetModuleHandle(None))
            window_class = wnd_class()
            window_class.hInstance = instance_handle
            window_class.lpszClassName = _HOST_CLASS_NAME
            window_class.lpfnWndProc = def_window_proc
            try:
                register_class(window_class)
            except Exception as register_error:
                if "already exists" not in str(register_error).casefold():
                    raise
            self._window_class = (_HOST_CLASS_NAME, instance_handle)
        except Exception as class_error:
            logger.warning(
                "注册 PowerPoint Broker 宿主窗口类失败，回退 Static：%s",
                class_error,
            )
            self._window_class = ("Static", 0)
        return self._window_class

    def _resize_host(self, host_hwnd: int, player_parent_hwnd: int) -> None:
        left, top, right, bottom = self._gui.GetClientRect(player_parent_hwnd)  # type: ignore[attr-defined]
        self._gui.SetWindowPos(  # type: ignore[attr-defined]
            host_hwnd,
            self._con.HWND_TOP,
            0,
            0,
            max(1, int(right) - int(left)),
            max(1, int(bottom) - int(top)),
            self._con.SWP_NOZORDER
            | self._con.SWP_NOACTIVATE
            | self._con.SWP_FRAMECHANGED
            | self._con.SWP_SHOWWINDOW,
        )

    def _destroy_window(self, hwnd: int) -> None:
        destroy_window = getattr(self._gui, "DestroyWindow", None)
        if not callable(destroy_window) or not self._is_window(hwnd):
            return
        try:
            destroy_window(hwnd)
        except Exception as destroy_error:
            logger.warning("销毁 PowerPoint Broker 宿主 HWND=%d 失败：%s", hwnd, destroy_error)

    def _is_window(self, hwnd: int) -> bool:
        try:
            return bool(self._gui.IsWindow(hwnd))  # type: ignore[attr-defined]
        except Exception:
            return False


__all__ = ["BrokerWindowHostRegistry"]
