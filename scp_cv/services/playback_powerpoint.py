#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PowerPoint 播放独占协调，负责在跨播放器进程打开前关闭旧放映会话。
@Project : SCP-cv
@File : playback_powerpoint.py
@Author : Qintsg
@Date : 2026-08-23
'''
from __future__ import annotations

import logging

from scp_cv.apps.playback.models import (
    PlaybackCommand,
    PlaybackSession,
    PlaybackState,
    SourceType,
)
from scp_cv.services.playback_commands import enqueue_playback_command
from scp_cv.services.slides_pdf import get_slides_playback_mode

logger = logging.getLogger(__name__)


def close_other_powerpoint_sessions(target_window_id: int) -> list[int]:
    """
    在目标窗口打开 PowerPoint 前向其它 PowerPoint 窗口下发关闭指令。

    此接口位于 Django 服务层，因此可以协调分属不同 ``run_player`` 进程的
    窗口；播放器适配器的系统级槽位负责保证旧放映释放前新放映不会抢跑。

    :param target_window_id: 即将打开 PowerPoint 的目标窗口编号
    :return: 已下发关闭指令的窗口编号列表
    """
    closed_window_ids: list[int] = []
    sessions = (
        PlaybackSession.objects.exclude(window_id=target_window_id)
        .filter(media_source__source_type=SourceType.PPT)
        .exclude(playback_state=PlaybackState.IDLE)
        .select_related("media_source")
    )
    for session in sessions:
        source = session.media_source
        if source is None or get_slides_playback_mode(source) != "powerpoint":
            continue
        cleanup_args = {
            "cleanup_source_id": source.pk,
        } if source.is_temporary else {}
        session.playback_state = PlaybackState.IDLE
        session.error_message = ""
        session.current_slide = 0
        session.total_slides = 0
        session.position_ms = 0
        session.duration_ms = 0
        enqueue_playback_command(session, PlaybackCommand.CLOSE, cleanup_args)
        closed_window_ids.append(session.window_id)
    if closed_window_ids:
        logger.info(
            "窗口 %d 打开 PowerPoint 前关闭其它放映窗口：%s",
            target_window_id,
            closed_window_ids,
        )
    return closed_window_ids


__all__ = ["close_other_powerpoint_sessions"]
