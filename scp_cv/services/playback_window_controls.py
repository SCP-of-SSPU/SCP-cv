#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
播放窗口控制服务，承载音量、静音与循环等单窗口播放参数写入。
@Project : SCP-cv
@File : playback_window_controls.py
@Author : Qintsg
@Date : 2026-05-07
'''
from __future__ import annotations

import logging

from scp_cv.apps.playback.models import (
    BigScreenMode,
    PlaybackCommand,
    PlaybackSession,
    RuntimeState,
)
from scp_cv.services.playback_sessions import PlaybackError, get_or_create_session

logger = logging.getLogger(__name__)


def runtime_muted_windows(big_screen_mode: str) -> list[int]:
    """
    返回指定大屏模式下必须静音的窗口编号。
    :param big_screen_mode: single 或 double
    :return: 需要强制静音的窗口编号
    """
    muted_windows = [3, 4]
    if big_screen_mode == BigScreenMode.SINGLE:
        muted_windows.append(2)
    return sorted(muted_windows)


def is_muted_by_runtime(window_id: int) -> bool:
    """
    判断窗口是否受当前运行态约束必须静音。
    :param window_id: 窗口编号
    :return: True 表示该窗口由大屏模式策略强制静音
    """
    runtime = RuntimeState.get_instance()
    return window_id in runtime_muted_windows(runtime.big_screen_mode)


def set_window_volume(window_id: int, volume: int) -> PlaybackSession:
    """
    设置指定窗口音量（0-100），同时下发 SET_VOLUME 指令。
    :param window_id: 窗口编号（1-4）
    :param volume: 音量等级（0-100）
    :return: 更新后的播放会话
    """
    normalized_volume = max(0, min(100, int(volume)))
    session = get_or_create_session(window_id)
    session.volume = normalized_volume
    session.pending_command = PlaybackCommand.SET_VOLUME
    session.command_args = {"volume": normalized_volume}
    session.save()
    logger.info("窗口 %d 音量设置为 %d", window_id, normalized_volume)
    return session


def set_window_mute(window_id: int, muted: bool) -> PlaybackSession:
    """
    设置指定窗口静音状态，同时下发 SET_MUTE 指令。
    :param window_id: 窗口编号（1-4）
    :param muted: 是否静音
    :return: 更新后的播放会话
    """
    session = get_or_create_session(window_id)
    normalized_muted = True if is_muted_by_runtime(window_id) else muted
    session.is_muted = normalized_muted
    session.pending_command = PlaybackCommand.SET_MUTE
    session.command_args = {"muted": normalized_muted}
    session.save()
    logger.info("窗口 %d 静音设置为 %s", window_id, normalized_muted)
    return session


def toggle_loop_playback(window_id: int, enabled: bool) -> PlaybackSession:
    """
    切换指定窗口的循环播放状态，同时下发 SET_LOOP 指令给播放器进程。
    :param window_id: 窗口编号（1-4）
    :param enabled: 是否启用循环播放
    :return: 更新后的播放会话
    :raises PlaybackError: 无活跃源时
    """
    session = get_or_create_session(window_id)
    if session.media_source is None:
        raise PlaybackError(f"窗口 {window_id} 当前没有打开的媒体源")

    session.loop_enabled = enabled
    session.pending_command = PlaybackCommand.SET_LOOP
    session.command_args = {"enabled": enabled}
    session.save()

    logger.info("窗口 %d 循环播放已%s", window_id, "开启" if enabled else "关闭")
    return session
