#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
播放会话生命周期辅助方法，负责字段重置与播放器窗口重建广播。
@Project : SCP-cv
@File : playback_lifecycle.py
@Author : Qintsg
@Date : 2026-08-23
'''
from __future__ import annotations

import time

from scp_cv.apps.playback.models import (
    PlaybackCommand,
    PlaybackSession,
    PlaybackState,
)
from scp_cv.services.playback_commands import enqueue_playback_command
from scp_cv.services.playback_sessions import VALID_WINDOW_IDS, get_or_create_session

RESET_ALL_WINDOWS_ARG = "reset_all_windows"
RESET_TOKEN_ARG = "reset_token"


def request_player_windows_rebuild() -> None:
    """
    请求播放器进程在主线程关闭并重建全部窗口。

    :return: None
    """
    reset_token = f"all-{time.time_ns()}"
    for window_id in sorted(VALID_WINDOW_IDS):
        session = get_or_create_session(window_id)
        enqueue_playback_command(session, PlaybackCommand.CLOSE, {
            RESET_ALL_WINDOWS_ARG: True,
            RESET_TOKEN_ARG: reset_token,
        })


def reset_playback_fields(session: PlaybackSession) -> None:
    """
    重置会话的播放相关字段。

    :param session: 播放会话实例；调用方负责保存
    :return: None
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
    session.pending_command = PlaybackCommand.NONE
    session.command_args = {}
