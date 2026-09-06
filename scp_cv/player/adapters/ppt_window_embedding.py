#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''PPT 放映窗口嵌入、定位和 Win32 清理辅助。'''

from __future__ import annotations

from scp_cv.player.adapters.ppt_window_registry import (
    mark_embedded_slideshow_window,
    read_embedded_slideshow_owner,
    unmark_embedded_slideshow_window,
)


def _window_exists(win32gui: object, hwnd: int) -> bool:
    """判断窗口句柄是否存在。"""
    is_window = getattr(win32gui, "IsWindow", None)
    if not callable(is_window):
        return True
    try:
        return bool(is_window(hwnd))
    except Exception:
        return True


def resize_slideshow_window(ppt_hwnd: int, parent_hwnd: int) -> tuple[int, int]:
    """调整 PPT 放映窗口填满播放器容器。"""
    import win32con
    import win32gui

    container_rect = win32gui.GetClientRect(parent_hwnd)
    width = container_rect[2] - container_rect[0]
    height = container_rect[3] - container_rect[1]
    win32gui.SetWindowPos(
        ppt_hwnd, win32con.HWND_TOP, 0, 0, width, height,
        win32con.SWP_NOZORDER | getattr(win32con, "SWP_NOACTIVATE", 0)
        | win32con.SWP_FRAMECHANGED | win32con.SWP_SHOWWINDOW,
    )
    move_window = getattr(win32gui, "MoveWindow", None)
    if callable(move_window):
        move_window(ppt_hwnd, 0, 0, width, height, True)
    return width, height


def embed_slideshow_window(ppt_hwnd: int, parent_hwnd: int, owner_token: int = 0) -> tuple[int, int]:
    """将 PPT 放映窗口嵌入播放器原生窗口。"""
    import win32con
    import win32gui

    if ppt_hwnd == 0 or parent_hwnd == 0:
        raise RuntimeError("PPT 放映窗口或父容器 HWND 无效，无法嵌入")
    show_window = getattr(win32gui, "ShowWindow", None)
    if callable(show_window):
        show_window(ppt_hwnd, win32con.SW_HIDE)
    style = win32gui.GetWindowLong(ppt_hwnd, win32con.GWL_STYLE)
    style = style & ~win32con.WS_POPUP & ~win32con.WS_OVERLAPPEDWINDOW | win32con.WS_CHILD | win32con.WS_VISIBLE
    win32gui.SetWindowLong(ppt_hwnd, win32con.GWL_STYLE, style)
    extended = win32gui.GetWindowLong(ppt_hwnd, win32con.GWL_EXSTYLE)
    extended &= ~win32con.WS_EX_TOPMOST
    extended &= ~win32con.WS_EX_APPWINDOW
    win32gui.SetWindowLong(ppt_hwnd, win32con.GWL_EXSTYLE, extended)
    win32gui.SetParent(ppt_hwnd, parent_hwnd)
    mark_embedded_slideshow_window(ppt_hwnd, owner_token or parent_hwnd)
    return resize_slideshow_window(ppt_hwnd, parent_hwnd)


def hide_embedded_slideshow_window(ppt_hwnd: int) -> None:
    """隐藏嵌入式 PPT 放映窗口。"""
    if ppt_hwnd == 0:
        return
    try:
        import win32con
        import win32gui
        if _window_exists(win32gui, ppt_hwnd):
            win32gui.ShowWindow(ppt_hwnd, win32con.SW_HIDE)
    except Exception:
        return


def show_embedded_slideshow_window(ppt_hwnd: int, parent_hwnd: int) -> tuple[int, int]:
    """恢复显示已嵌入的 PPT 放映窗口。"""
    if ppt_hwnd == 0 or parent_hwnd == 0:
        return 0, 0
    try:
        import win32con
        import win32gui
        if not _window_exists(win32gui, ppt_hwnd):
            return 0, 0
        win32gui.ShowWindow(ppt_hwnd, win32con.SW_SHOW)
        return resize_slideshow_window(ppt_hwnd, parent_hwnd)
    except Exception:
        return 0, 0


def close_embedded_slideshow_window(ppt_hwnd: int, owner_token: int = 0) -> None:
    """关闭属于当前适配器的 PPT 放映窗口。"""
    if ppt_hwnd == 0:
        return
    try:
        import win32con
        import win32gui
        if owner_token:
            current_owner = read_embedded_slideshow_owner(win32gui, ppt_hwnd)
            if current_owner and current_owner != int(owner_token):
                return
        hide_embedded_slideshow_window(ppt_hwnd)
        if not _window_exists(win32gui, ppt_hwnd):
            unmark_embedded_slideshow_window(ppt_hwnd)
            return
        post_message = getattr(win32gui, "PostMessage", None)
        if callable(post_message):
            post_message(ppt_hwnd, win32con.WM_CLOSE, 0, 0)
            return
        send_message = getattr(win32gui, "SendMessage", None)
        if callable(send_message):
            send_message(ppt_hwnd, win32con.WM_CLOSE, 0, 0)
    except Exception:
        return


def detach_slideshow_window(ppt_hwnd: int) -> None:
    """解除 PPT 放映窗口与播放器容器的父子关系。"""
    if ppt_hwnd == 0:
        return
    import win32gui
    hide_embedded_slideshow_window(ppt_hwnd)
    unmark_embedded_slideshow_window(ppt_hwnd)
    win32gui.SetParent(ppt_hwnd, 0)


__all__ = [
    "close_embedded_slideshow_window", "detach_slideshow_window",
    "embed_slideshow_window", "hide_embedded_slideshow_window",
    "resize_slideshow_window", "show_embedded_slideshow_window",
]
