#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PPT 外部放映窗口 Win32 操作工具，将 Office 放映窗口铺满目标显示区域。
@Project : SCP-cv
@File : ppt_external_window.py
@Author : Qintsg
@Date : 2026-05-28
'''
from __future__ import annotations


def present_external_slideshow_window(slideshow_hwnd: int, anchor_hwnd: int) -> tuple[int, int]:
    """
    将放映窗口从 PySide 父子嵌入模式切换为外部顶层窗口并铺满目标区域。
    :param slideshow_hwnd: Office/LibreOffice 放映窗口 HWND
    :param anchor_hwnd: PySide 播放器渲染容器 HWND，用于定位目标屏幕区域
    :return: 调整后的宽高
    """
    import win32api
    import win32con
    import win32gui

    left, top, right, bottom = _target_rect_from_anchor(
        win32gui,
        win32con,
        anchor_hwnd,
        win32api,
    )
    width = max(1, right - left)
    height = max(1, bottom - top)

    win32gui.SetParent(slideshow_hwnd, 0)
    _restore_window_for_resize(win32gui, win32con, slideshow_hwnd)
    _set_external_window_styles(win32gui, win32con, slideshow_hwnd)
    _restore_window_for_resize(win32gui, win32con, slideshow_hwnd)
    win32gui.SetWindowPos(
        slideshow_hwnd,
        win32con.HWND_TOPMOST,
        left,
        top,
        width,
        height,
        win32con.SWP_FRAMECHANGED | win32con.SWP_SHOWWINDOW,
    )
    _move_window(win32gui, slideshow_hwnd, left, top, width, height)
    return width, height


def release_external_slideshow_window(slideshow_hwnd: int) -> None:
    """
    释放外部放映窗口的置顶状态，关闭后端前尽量恢复为普通顶层窗口。
    :param slideshow_hwnd: Office/LibreOffice 放映窗口 HWND
    :return: None
    """
    if slideshow_hwnd == 0:
        return
    import win32con
    import win32gui

    try:
        win32gui.SetParent(slideshow_hwnd, 0)
        win32gui.SetWindowPos(
            slideshow_hwnd,
            win32con.HWND_NOTOPMOST,
            0,
            0,
            0,
            0,
            win32con.SWP_NOMOVE
            | win32con.SWP_NOSIZE
            | win32con.SWP_NOACTIVATE,
        )
    except Exception:
        return


def libreoffice_display_index_from_anchor_window(anchor_hwnd: int) -> int:
    """
    根据播放器锚点窗口计算 LibreOffice Presentation.Display 的 1-based 显示器序号。
    :param anchor_hwnd: PySide 播放器容器 HWND
    :return: LibreOffice Display 属性序号；0 表示使用 LibreOffice 默认外部屏
    """
    try:
        import win32api
        import win32con
    except Exception:
        return 0
    try:
        target_monitor = win32api.MonitorFromWindow(  # type: ignore[attr-defined]
            anchor_hwnd,
            getattr(win32con, "MONITOR_DEFAULTTONEAREST", 2),
        )
    except Exception:
        return 0

    try:
        monitor_entries = win32api.EnumDisplayMonitors(None, None)  # type: ignore[attr-defined]
    except Exception:
        return 0
    target_identity = _monitor_identity(target_monitor)
    for index, monitor_entry in enumerate(monitor_entries, start=1):
        monitor = monitor_entry[0] if isinstance(monitor_entry, tuple) else monitor_entry
        if _monitor_identity(monitor) == target_identity:
            return index
    return 0


def _target_rect_from_anchor(
    win32gui: object,
    win32con: object,
    anchor_hwnd: int,
    win32api: object | None = None,
) -> tuple[int, int, int, int]:
    """
    从播放器容器 HWND 读取目标屏幕矩形，失败时回退到最近显示器矩形。
    :param win32gui: win32gui 模块或测试替身
    :param win32con: win32con 模块或测试替身
    :param anchor_hwnd: PySide 播放器容器 HWND
    :param win32api: win32api 模块或测试替身
    :return: (left, top, right, bottom)
    """
    try:
        left, top, right, bottom = win32gui.GetWindowRect(anchor_hwnd)  # type: ignore[attr-defined]
        if right > left and bottom > top:
            return int(left), int(top), int(right), int(bottom)
    except Exception:
        pass

    try:
        root_hwnd = win32gui.GetAncestor(  # type: ignore[attr-defined]
            anchor_hwnd,
            getattr(win32con, "GA_ROOT", 2),
        )
        left, top, right, bottom = win32gui.GetWindowRect(root_hwnd)  # type: ignore[attr-defined]
        if right > left and bottom > top:
            return int(left), int(top), int(right), int(bottom)
    except Exception:
        pass

    if win32api is None:
        try:
            import win32api as imported_win32api
        except Exception:
            return 0, 0, 1, 1
        win32api = imported_win32api
    monitor_default = getattr(win32con, "MONITOR_DEFAULTTONEAREST", 2)
    try:
        monitor = win32api.MonitorFromWindow(anchor_hwnd, monitor_default)  # type: ignore[attr-defined]
        monitor_info = win32api.GetMonitorInfo(monitor)  # type: ignore[attr-defined]
    except Exception:
        return 0, 0, 1, 1
    monitor_rect = monitor_info.get("Monitor") or monitor_info.get("Work")
    if monitor_rect is None:
        return 0, 0, 1, 1
    left, top, right, bottom = monitor_rect
    return int(left), int(top), int(right), int(bottom)


def _monitor_identity(monitor: object) -> object:
    """
    归一化 pywin32 HMONITOR 句柄，兼容测试替身和真实 PyHANDLE。
    :param monitor: 显示器句柄
    :return: 可比较的句柄标识
    """
    try:
        return int(monitor)  # type: ignore[arg-type]
    except Exception:
        return monitor


def _set_external_window_styles(
    win32gui: object,
    win32con: object,
    slideshow_hwnd: int,
) -> None:
    """
    去除边框和子窗口样式，确保放映窗口作为无边框顶层窗口显示。
    :param win32gui: win32gui 模块或测试替身
    :param win32con: win32con 模块或测试替身
    :param slideshow_hwnd: 放映窗口 HWND
    :return: None
    """
    original_style = win32gui.GetWindowLong(  # type: ignore[attr-defined]
        slideshow_hwnd,
        win32con.GWL_STYLE,
    )
    external_style = original_style
    external_style &= ~win32con.WS_CHILD
    external_style &= ~win32con.WS_OVERLAPPEDWINDOW
    external_style |= win32con.WS_POPUP | win32con.WS_VISIBLE
    win32gui.SetWindowLong(  # type: ignore[attr-defined]
        slideshow_hwnd,
        win32con.GWL_STYLE,
        external_style,
    )

    extended_style = win32gui.GetWindowLong(  # type: ignore[attr-defined]
        slideshow_hwnd,
        win32con.GWL_EXSTYLE,
    )
    extended_style &= ~win32con.WS_EX_APPWINDOW
    extended_style |= win32con.WS_EX_TOPMOST
    win32gui.SetWindowLong(  # type: ignore[attr-defined]
        slideshow_hwnd,
        win32con.GWL_EXSTYLE,
        extended_style,
    )


def _restore_window_for_resize(win32gui: object, win32con: object, slideshow_hwnd: int) -> None:
    """
    退出最大化/全屏状态，避免 LibreOffice 忽略后续目标区域定位。
    :param win32gui: win32gui 模块或测试替身
    :param win32con: win32con 模块或测试替身
    :param slideshow_hwnd: 放映窗口 HWND
    :return: None
    """
    show_window = getattr(win32gui, "ShowWindow", None)
    if not callable(show_window):
        return
    try:
        show_window(slideshow_hwnd, getattr(win32con, "SW_RESTORE", 9))
    except Exception:
        return


def _move_window(
    win32gui: object,
    slideshow_hwnd: int,
    left: int,
    top: int,
    width: int,
    height: int,
) -> None:
    """
    使用 MoveWindow 兜底应用目标矩形。
    :param win32gui: win32gui 模块或测试替身
    :param slideshow_hwnd: 放映窗口 HWND
    :param left: 目标左侧坐标
    :param top: 目标顶部坐标
    :param width: 目标宽度
    :param height: 目标高度
    :return: None
    """
    move_window = getattr(win32gui, "MoveWindow", None)
    if not callable(move_window):
        return
    try:
        move_window(slideshow_hwnd, left, top, width, height, True)
    except Exception:
        return


__all__ = [
    "libreoffice_display_index_from_anchor_window",
    "present_external_slideshow_window",
    "release_external_slideshow_window",
]
