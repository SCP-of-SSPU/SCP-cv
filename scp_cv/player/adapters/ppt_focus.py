#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PPT 放映相关的前台与任务栏 Win32 辅助。
- 放映窗口嵌入后把被 PowerPoint 抢走的前台还给播放器，避免任务栏浮出；
- 隐藏由本系统拉起的 PowerPoint 编辑窗口，避免任务栏出现残留按钮。
@Project : SCP-cv
@File : ppt_focus.py
@Author : Qintsg
@Date : 2026-06-10
'''
from __future__ import annotations

import logging
from typing import Optional

from scp_cv.player.adapters.ppt_process import read_ppt_app_hwnd

_GA_ROOT = 2


def conceal_ppt_editor_window(
    ppt_app: object,
    logger: Optional[logging.Logger] = None,
) -> bool:
    """
    隐藏 PowerPoint 编辑主窗口并移除任务栏按钮。
    仅应对本系统自行拉起的 PowerPoint 实例调用，避免影响用户已打开的窗口。
    :param ppt_app: PowerPoint Application COM 对象
    :param logger: 可选日志器
    :return: True 表示已执行隐藏
    """
    app_hwnd = read_ppt_app_hwnd(ppt_app)
    if app_hwnd == 0:
        return False
    try:
        import win32con
        import win32gui

        extended_style = win32gui.GetWindowLong(app_hwnd, win32con.GWL_EXSTYLE)
        extended_style &= ~win32con.WS_EX_APPWINDOW
        extended_style |= win32con.WS_EX_TOOLWINDOW
        win32gui.SetWindowLong(app_hwnd, win32con.GWL_EXSTYLE, extended_style)
        if win32gui.IsWindowVisible(app_hwnd):
            win32gui.ShowWindow(app_hwnd, win32con.SW_HIDE)
        return True
    except Exception as conceal_error:
        if logger is not None:
            logger.debug("隐藏 PowerPoint 编辑窗口失败：%s", conceal_error)
        return False


def restore_player_foreground(
    container_hwnd: int,
    ppt_process_id: int,
    logger: Optional[logging.Logger] = None,
) -> bool:
    """
    放映窗口嵌入完成后，若前台被 PowerPoint 抢走则还给播放器顶层窗口。
    只在当前前台窗口属于指定 PowerPoint 进程时动作，不打扰操作员的其它窗口。
    :param container_hwnd: 播放器嵌入容器（子窗口）句柄
    :param ppt_process_id: 当前 PowerPoint 进程 ID；为 0 时跳过恢复
    :param logger: 可选日志器
    :return: True 表示已执行前台恢复
    """
    if container_hwnd == 0 or ppt_process_id == 0:
        return False
    try:
        import win32con
        import win32gui
        import win32process
    except Exception as import_error:
        if logger is not None:
            logger.debug("Win32 模块不可用，跳过前台恢复：%s", import_error)
        return False

    try:
        player_root = int(win32gui.GetAncestor(container_hwnd, _GA_ROOT) or 0)
    except Exception:
        player_root = 0
    if player_root == 0:
        player_root = container_hwnd

    try:
        foreground_hwnd = int(win32gui.GetForegroundWindow() or 0)
    except Exception:
        return False
    if foreground_hwnd == 0 or foreground_hwnd == player_root:
        return False

    try:
        _, foreground_pid = win32process.GetWindowThreadProcessId(foreground_hwnd)
    except Exception:
        return False
    if int(foreground_pid or 0) != int(ppt_process_id):
        return False

    _set_foreground_window(win32gui, foreground_hwnd, player_root, logger)
    _reassert_topmost(win32gui, win32con, player_root, logger)
    return True


def _set_foreground_window(
    win32gui: object,
    foreground_hwnd: int,
    player_root: int,
    logger: Optional[logging.Logger],
) -> None:
    """
    通过 AttachThreadInput 提升 SetForegroundWindow 成功率。
    :param win32gui: win32gui 模块或测试替身
    :param foreground_hwnd: 当前前台窗口句柄
    :param player_root: 播放器顶层窗口句柄
    :param logger: 可选日志器
    :return: None
    """
    attached = False
    current_thread_id = 0
    foreground_thread_id = 0
    try:
        import win32api
        import win32process

        current_thread_id = win32api.GetCurrentThreadId()
        foreground_thread_id, _ = win32process.GetWindowThreadProcessId(foreground_hwnd)
        if current_thread_id and foreground_thread_id and current_thread_id != foreground_thread_id:
            win32process.AttachThreadInput(foreground_thread_id, current_thread_id, True)
            attached = True
    except Exception:
        attached = False
    try:
        bring_to_top = getattr(win32gui, "BringWindowToTop", None)
        if callable(bring_to_top):
            bring_to_top(player_root)
        win32gui.SetForegroundWindow(player_root)
    except Exception as foreground_error:
        if logger is not None:
            logger.debug("播放器前台恢复失败：%s", foreground_error)
    finally:
        if attached:
            try:
                import win32process

                win32process.AttachThreadInput(foreground_thread_id, current_thread_id, False)
            except Exception:
                pass


def _reassert_topmost(
    win32gui: object,
    win32con: object,
    player_root: int,
    logger: Optional[logging.Logger],
) -> None:
    """
    重申播放器顶层窗口的 TOPMOST，使其重新压住任务栏。
    :param win32gui: win32gui 模块或测试替身
    :param win32con: win32con 模块或测试替身
    :param player_root: 播放器顶层窗口句柄
    :param logger: 可选日志器
    :return: None
    """
    try:
        win32gui.SetWindowPos(
            player_root,
            win32con.HWND_TOPMOST,
            0,
            0,
            0,
            0,
            win32con.SWP_NOMOVE
            | win32con.SWP_NOSIZE
            | win32con.SWP_NOACTIVATE
            | win32con.SWP_SHOWWINDOW,
        )
    except Exception as topmost_error:
        if logger is not None:
            logger.debug("重申播放器置顶失败：%s", topmost_error)


__all__ = [
    "conceal_ppt_editor_window",
    "restore_player_foreground",
]
