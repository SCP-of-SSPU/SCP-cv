#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PowerPoint 放映重置与运行时参数构造。
@Project : SCP-cv
@File : playback_powerpoint.py
@Author : Qintsg
@Date : 2026-08-23
'''
from __future__ import annotations

import logging
import time

from scp_cv.apps.playback.models import (
    PlaybackCommand,
    PlaybackSession,
    PlaybackState,
    SourceType,
)
from scp_cv.services.playback_commands import enqueue_playback_command
from scp_cv.services.playback_sessions import VALID_WINDOW_IDS, get_or_create_session
from scp_cv.services.slides_pdf import (
    get_slides_playback_mode,
    resolve_slide_playback_uri,
)

logger = logging.getLogger(__name__)
RESET_TOKEN_ARG = "reset_token"


def close_other_powerpoint_sessions(target_window_id: int) -> list[int]:
    """
    兼容旧调用入口，不再抢占其它 PowerPoint 窗口。

    唯一 COM 所有权由跨进程 ``PowerPointSlot`` 决定，槽位冲突由目标窗口
    自行回退 PDF，服务层不能预判或关闭当前持有者。

    :param target_window_id: 即将打开 PowerPoint 的目标窗口编号
    :return: 已下发关闭指令的窗口编号列表
    """
    logger.debug("窗口 %d 使用运行时 PowerPoint 槽位协调，不抢占其它窗口", target_window_id)
    return []


def reset_ppt_playback() -> list[PlaybackSession]:
    """
    重置所有活跃 PowerPoint 放映窗口，并保留当前页码。

    :return: 更新后的会话列表
    """
    restart_sessions: list[dict[str, object]] = []
    updated_sessions: list[PlaybackSession] = []
    for window_id in sorted(VALID_WINDOW_IDS):
        session = get_or_create_session(window_id)
        if (
            session.media_source is None
            or session.media_source.source_type != SourceType.PPT
            or get_slides_playback_mode(session.media_source) != "powerpoint"
            or session.playback_state == PlaybackState.IDLE
        ):
            continue
        restart_sessions.append(_ppt_restart_args(session))
        session.playback_state = PlaybackState.LOADING
        session.error_message = ""
        session.save(update_fields=[
            "playback_state",
            "error_message",
            "last_updated_at",
        ])
        updated_sessions.append(session)

    if not restart_sessions:
        logger.info("当前没有需要重置的 PowerPoint 放映")
        return updated_sessions

    reset_token = f"ppt-{time.time_ns()}"
    target_window_ids = {
        int(restart_args.get("window_id") or 0)
        for restart_args in restart_sessions
        if int(restart_args.get("window_id") or 0) > 0
    }
    for target_window_id in sorted(target_window_ids):
        session = get_or_create_session(target_window_id)
        enqueue_playback_command(session, PlaybackCommand.RESET_PPT, {
            "restart_sessions": restart_sessions,
            RESET_TOKEN_ARG: reset_token,
        })
        if session not in updated_sessions:
            updated_sessions.append(session)
    logger.info("已请求重置 PPT 放映，待重启窗口数=%d", len(restart_sessions))
    return updated_sessions


def _ppt_restart_args(session: PlaybackSession) -> dict[str, object]:
    """
    为 PowerPoint 重启构造播放器 OPEN 指令参数。

    :param session: 当前 PowerPoint 播放会话
    :return: 可直接交给播放器的参数字典
    """
    source = session.media_source
    if source is None:
        return {}
    playback_uri = (
        resolve_slide_playback_uri(source)
        if source.source_type == SourceType.PPT
        else source.uri
    )
    return {
        "window_id": session.window_id,
        "source_id": source.pk,
        "source_type": source.source_type,
        "uri": playback_uri,
        "original_uri": source.uri,
        "adapter_kind": get_slides_playback_mode(source),
        "autoplay": True,
        "volume": session.volume,
        "muted": session.is_muted,
        "preheat_enabled": bool(getattr(source, "keep_alive", True)),
        "target_slide": max(1, int(session.current_slide or 1)),
    }


__all__ = ["close_other_powerpoint_sessions", "reset_ppt_playback"]
