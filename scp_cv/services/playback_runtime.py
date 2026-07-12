#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
播放运行态编排：集中全局重置、窗口广播与固定音频策略。
@Project : SCP-cv
@File : playback_runtime.py
@Author : Qintsg
@Date : 2026-07-12
'''
from __future__ import annotations

import logging
import time

from scp_cv.apps.playback.models import (
    PlaybackCommand,
    PlaybackSession,
    PlaybackState,
    RuntimeState,
)
from scp_cv.services.playback_commands import enqueue_session_command
from scp_cv.services.playback_sessions import VALID_WINDOW_IDS, get_or_create_session
from scp_cv.services.playback_window_controls import runtime_muted_windows


logger = logging.getLogger(__name__)

RESET_ALL_WINDOWS_ARG = "reset_all_windows"
RESET_TOKEN_ARG = "reset_token"
_RESET_SESSION_UPDATE_FIELDS = [
    "media_source",
    "playback_state",
    "error_message",
    "current_slide",
    "total_slides",
    "position_ms",
    "duration_ms",
    "loop_enabled",
    "volume",
    "is_muted",
    "last_updated_at",
]


def reset_all_sessions_to_idle() -> list[PlaybackSession]:
    """
    将所有播放窗口重置为待机状态，并请求播放器重建窗口。
    :return: 重置后的会话列表
    """
    reset_sessions: list[PlaybackSession] = []
    for window_id in sorted(VALID_WINDOW_IDS):
        session = get_or_create_session(window_id)
        _reset_playback_fields(session)
        session.save(update_fields=_RESET_SESSION_UPDATE_FIELDS)
        reset_sessions.append(session)
    apply_runtime_audio_policy()
    _request_player_windows_rebuild()
    logger.info("已将所有窗口重置为待机状态，并请求播放器重建窗口")
    return reset_sessions


def request_all_windows_close() -> list[PlaybackSession]:
    """
    向所有窗口下发关闭指令，并同步将会话状态重置为待机。
    :return: 更新后的会话列表
    """
    reset_sessions: list[PlaybackSession] = []
    for window_id in sorted(VALID_WINDOW_IDS):
        session = get_or_create_session(window_id)
        cleanup_args = {
            "cleanup_source_id": session.media_source_id,
        } if session.media_source is not None and session.media_source.is_temporary else {}
        _reset_playback_fields(session)
        session.save(update_fields=_RESET_SESSION_UPDATE_FIELDS)
        enqueue_session_command(
            session,
            PlaybackCommand.CLOSE,
            cleanup_args,
            supersedes=True,
        )
        reset_sessions.append(session)
    apply_runtime_audio_policy()
    logger.info("已向所有窗口下发关闭指令并重置待机状态")
    return reset_sessions


def request_show_window_ids() -> list[PlaybackSession]:
    """向全部播放窗口追加显示编号指令。"""
    sessions: list[PlaybackSession] = []
    for window_id in sorted(VALID_WINDOW_IDS):
        session = get_or_create_session(window_id)
        enqueue_session_command(session, PlaybackCommand.SHOW_ID)
        sessions.append(session)
    return sessions


def get_runtime_snapshot() -> dict[str, object]:
    """
    获取全局运行状态快照。
    :return: 大屏模式、系统音量和固定静音策略
    """
    runtime = RuntimeState.get_instance()
    return {
        "big_screen_mode": runtime.big_screen_mode,
        "volume_level": runtime.volume_level,
        "muted_windows": runtime_muted_windows(runtime.big_screen_mode),
    }


def apply_runtime_audio_policy() -> None:
    """
    根据大屏模式应用固定静音策略。
    约束：窗口 3/4 始终静音；single 下窗口 2 静音；double 下窗口 1/2 不静音。
    """
    runtime = RuntimeState.get_instance()
    muted_windows = set(runtime_muted_windows(runtime.big_screen_mode))
    for window_id in sorted(VALID_WINDOW_IDS):
        session = get_or_create_session(window_id)
        muted = window_id in muted_windows
        session.is_muted = muted
        session.save(update_fields=["is_muted", "last_updated_at"])
        enqueue_session_command(
            session,
            PlaybackCommand.SET_MUTE,
            {"muted": muted},
        )


def _reset_playback_fields(session: PlaybackSession) -> None:
    """
    重置会话的播放相关字段，持久化由调用方负责。
    :param session: 播放会话实例
    """
    session.media_source = None
    session.playback_state = PlaybackState.IDLE
    session.error_message = ""
    session.current_slide = 0
    session.total_slides = 0
    session.position_ms = 0
    session.duration_ms = 0
    session.loop_enabled = False
    session.volume = 100
    session.is_muted = False


def _request_player_windows_rebuild() -> None:
    """向全部窗口广播同一重置 token，请求播放器在主线程重建窗口。"""
    reset_token = f"all-{time.time_ns()}"
    for window_id in sorted(VALID_WINDOW_IDS):
        session = get_or_create_session(window_id)
        enqueue_session_command(
            session,
            PlaybackCommand.CLOSE,
            {
                RESET_ALL_WINDOWS_ARG: True,
                RESET_TOKEN_ARG: reset_token,
            },
            supersedes=True,
        )


__all__ = [
    "RESET_ALL_WINDOWS_ARG",
    "RESET_TOKEN_ARG",
    "apply_runtime_audio_policy",
    "get_runtime_snapshot",
    "request_all_windows_close",
    "request_show_window_ids",
    "reset_all_sessions_to_idle",
]
