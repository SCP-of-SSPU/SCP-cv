#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PPT 播放重启编排：按窗口生成恢复参数并原子追加 CLOSE/OPEN 批次。
@Project : SCP-cv
@File : playback_ppt.py
@Author : Qintsg
@Date : 2026-07-12
'''
from __future__ import annotations

import logging

from scp_cv.apps.playback.models import (
    PlaybackCommand,
    PlaybackSession,
    PlaybackState,
    SourceType,
)
from scp_cv.services.playback_commands import enqueue_session_batch
from scp_cv.services.playback_sessions import VALID_WINDOW_IDS, get_or_create_session
from scp_cv.services.ppt_playback_cache import resolve_ppt_playback_uri


logger = logging.getLogger(__name__)


def reset_ppt_playback() -> list[PlaybackSession]:
    """
    重置所有 PPT 放映窗口，并让当前 PPT 窗口回到重置前页码。
    :return: 更新后的会话列表
    """
    updated_sessions: list[PlaybackSession] = []
    for window_id in sorted(VALID_WINDOW_IDS):
        session = get_or_create_session(window_id)
        if session.media_source is None or session.media_source.source_type != SourceType.PPT:
            continue
        restart_args = _ppt_restart_args(session)
        session.playback_state = PlaybackState.LOADING
        session.error_message = ""
        session.save(update_fields=[
            "playback_state",
            "error_message",
            "last_updated_at",
        ])
        enqueue_session_batch(
            session,
            [
                (PlaybackCommand.CLOSE, {}),
                (PlaybackCommand.OPEN, restart_args),
            ],
            supersedes=True,
        )
        updated_sessions.append(session)

    logger.info("已请求重置 PPT 放映，待重启窗口数=%d", len(updated_sessions))
    return updated_sessions


def _ppt_restart_args(session: PlaybackSession) -> dict[str, object]:
    """为 PPT 重启构造播放器 OPEN 指令参数。"""
    source = session.media_source
    if source is None:
        return {}
    playback_uri = resolve_ppt_playback_uri(source)
    return {
        "window_id": session.window_id,
        "source_id": source.pk,
        "source_type": source.source_type,
        "uri": playback_uri,
        "original_uri": source.uri,
        "autoplay": True,
        "volume": session.volume,
        "muted": session.is_muted,
        "preheat_enabled": bool(getattr(source, "keep_alive", True)),
        "target_slide": max(1, int(session.current_slide or 1)),
    }


__all__ = ["reset_ppt_playback"]
