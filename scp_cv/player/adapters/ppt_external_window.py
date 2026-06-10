#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PPT 外部放映窗口 Win32 操作工具，将 PowerPoint 放映窗口铺满目标显示区域。
@Project : SCP-cv
@File : ppt_external_window.py
@Author : Qintsg
@Date : 2026-05-28
'''
from __future__ import annotations

import logging
import time

logger = logging.getLogger(__name__)
_PRESENT_VERIFY_RETRIES = 4
_PRESENT_VERIFY_DELAY_SECONDS = 0.1
_RECT_TOLERANCE_PX = 2
_MIN_TRUSTED_ANCHOR_WIDTH = 640
_MIN_TRUSTED_ANCHOR_HEIGHT = 360


def present_external_slideshow_window(slideshow_hwnd: int, anchor_hwnd: int) -> tuple[int, int]:
    """
    将放映窗口从 PySide 父子嵌入模式切换为外部顶层窗口并铺满目标区域。
    :param slideshow_hwnd: PowerPoint 放映窗口 HWND
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
    last_rect = (0, 0, 0, 0)
    for attempt in range(1, _PRESENT_VERIFY_RETRIES + 1):
        _apply_external_window_rect(
            win32gui,
            win32con,
            slideshow_hwnd,
            left,
            top,
            width,
            height,
        )
        last_rect = _read_window_rect(win32gui, slideshow_hwnd)
        if _rect_matches(last_rect, (left, top, right, bottom)):
            if attempt > 1:
                logger.info(
                    "PowerPoint 外部窗口第 %d 次重试后铺满目标区域：HWND=%d, rect=%s",
                    attempt,
                    slideshow_hwnd,
                    last_rect,
                )
            return width, height
        if attempt < _PRESENT_VERIFY_RETRIES:
            time.sleep(_PRESENT_VERIFY_DELAY_SECONDS)

    raise RuntimeError(
        "PowerPoint 放映窗口未能铺满目标区域："
        f"hwnd={slideshow_hwnd}, target={(left, top, right, bottom)}, actual={last_rect}"
    )


def release_external_slideshow_window(slideshow_hwnd: int) -> None:
    """
    释放外部放映窗口的置顶状态，关闭后端前尽量恢复为普通顶层窗口。
    :param slideshow_hwnd: PowerPoint 放映窗口 HWND
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


def close_external_slideshow_window(slideshow_hwnd: int) -> None:
    """
    请求关闭外部 PowerPoint 放映窗口。
    :param slideshow_hwnd: PowerPoint 放映窗口 HWND
    :return: None
    """
    if slideshow_hwnd == 0:
        return
    try:
        import win32con
        import win32gui

        release_external_slideshow_window(slideshow_hwnd)
        if not _window_exists(win32gui, slideshow_hwnd):
            return
        post_message = getattr(win32gui, "PostMessage", None)
        if callable(post_message):
            post_message(slideshow_hwnd, win32con.WM_CLOSE, 0, 0)
            return
        send_message = getattr(win32gui, "SendMessage", None)
        if callable(send_message):
            send_message(slideshow_hwnd, win32con.WM_CLOSE, 0, 0)
    except Exception as close_error:
        logger.debug("请求关闭 PowerPoint 放映窗口失败：hwnd=%s, error=%s", slideshow_hwnd, close_error)


def _window_exists(win32gui: object, hwnd: int) -> bool:
    """
    判断窗口句柄是否仍存在；替身或旧 Win32 模块不支持时默认继续尝试关闭。
    :param win32gui: win32gui 模块或测试替身
    :param hwnd: 窗口句柄
    :return: True 表示窗口仍存在
    """
    is_window = getattr(win32gui, "IsWindow", None)
    if not callable(is_window):
        return True
    try:
        return bool(is_window(hwnd))
    except Exception:
        return True


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
            anchor_rect = int(left), int(top), int(right), int(bottom)
            fallback_rect = _root_rect_for_small_anchor(
                win32gui,
                win32con,
                anchor_hwnd,
                anchor_rect,
            )
            if fallback_rect is not None:
                return fallback_rect
            return anchor_rect
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


def _root_rect_for_small_anchor(
    win32gui: object,
    win32con: object,
    anchor_hwnd: int,
    anchor_rect: tuple[int, int, int, int],
) -> tuple[int, int, int, int] | None:
    """
    当首次显示时容器 HWND 仍是异常小矩形，回退到播放器顶层窗口矩形。
    :param win32gui: win32gui 模块或测试替身
    :param win32con: win32con 模块或测试替身
    :param anchor_hwnd: PySide 播放器容器 HWND
    :param anchor_rect: 当前读取到的容器矩形
    :return: 可用顶层窗口矩形，或 None
    """
    anchor_width = anchor_rect[2] - anchor_rect[0]
    anchor_height = anchor_rect[3] - anchor_rect[1]
    if (
        anchor_width >= _MIN_TRUSTED_ANCHOR_WIDTH
        and anchor_height >= _MIN_TRUSTED_ANCHOR_HEIGHT
    ):
        return None

    try:
        root_hwnd = win32gui.GetAncestor(  # type: ignore[attr-defined]
            anchor_hwnd,
            getattr(win32con, "GA_ROOT", 2),
        )
        if not root_hwnd or root_hwnd == anchor_hwnd:
            return None
        left, top, right, bottom = win32gui.GetWindowRect(root_hwnd)  # type: ignore[attr-defined]
    except Exception:
        return None

    root_rect = int(left), int(top), int(right), int(bottom)
    root_width = root_rect[2] - root_rect[0]
    root_height = root_rect[3] - root_rect[1]
    if root_width <= anchor_width or root_height <= anchor_height:
        return None
    if root_width < _MIN_TRUSTED_ANCHOR_WIDTH or root_height < _MIN_TRUSTED_ANCHOR_HEIGHT:
        return None
    logger.debug(
        "PPT 锚点矩形过小，改用顶层播放器窗口矩形：anchor=%s, root=%s",
        anchor_rect,
        root_rect,
    )
    return root_rect


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


def _apply_external_window_rect(
    win32gui: object,
    win32con: object,
    slideshow_hwnd: int,
    left: int,
    top: int,
    width: int,
    height: int,
) -> None:
    """
    将 PowerPoint 放映窗口设置为无边框顶层并移动到目标矩形。
    :param win32gui: win32gui 模块或测试替身
    :param win32con: win32con 模块或测试替身
    :param slideshow_hwnd: 放映窗口 HWND
    :param left: 目标左侧坐标
    :param top: 目标顶部坐标
    :param width: 目标宽度
    :param height: 目标高度
    :return: None
    """
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


def _read_window_rect(win32gui: object, slideshow_hwnd: int) -> tuple[int, int, int, int]:
    """
    读取窗口矩形，失败时返回空矩形。
    :param win32gui: win32gui 模块或测试替身
    :param slideshow_hwnd: 放映窗口 HWND
    :return: Win32 窗口矩形
    """
    try:
        left, top, right, bottom = win32gui.GetWindowRect(slideshow_hwnd)  # type: ignore[attr-defined]
    except Exception:
        return 0, 0, 0, 0
    return int(left), int(top), int(right), int(bottom)


def _rect_matches(
    actual_rect: tuple[int, int, int, int],
    expected_rect: tuple[int, int, int, int],
) -> bool:
    """
    判断实际窗口矩形是否与目标矩形足够接近。
    :param actual_rect: 实际窗口矩形
    :param expected_rect: 目标窗口矩形
    :return: True 表示偏差在容差内
    """
    return all(
        abs(actual_value - expected_value) <= _RECT_TOLERANCE_PX
        for actual_value, expected_value in zip(actual_rect, expected_rect)
    )


def _restore_window_for_resize(win32gui: object, win32con: object, slideshow_hwnd: int) -> None:
    """
    退出最大化/全屏状态，确保后续目标区域定位生效。
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
    "close_external_slideshow_window",
    "present_external_slideshow_window",
    "release_external_slideshow_window",
]
