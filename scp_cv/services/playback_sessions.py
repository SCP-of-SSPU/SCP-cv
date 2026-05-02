#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
播放会话基础服务，负责窗口编号校验、会话获取和状态快照序列化。
@Project : SCP-cv
@File : playback_sessions.py
@Author : Qintsg
@Date : 2026-05-02
'''
from __future__ import annotations

import logging

from scp_cv.apps.playback.models import PlaybackSession, PlaybackState

logger = logging.getLogger(__name__)

# 有效的窗口编号范围（1-4 对应四个输出显示器）
VALID_WINDOW_IDS = frozenset({1, 2, 3, 4})


class PlaybackError(Exception):
    """播放会话操作过程中的业务异常。"""


def validate_window_id(window_id: int) -> None:
    """
    校验窗口编号合法性。
    :param window_id: 窗口编号
    :raises PlaybackError: 窗口编号不在 1-4 范围时
    """
    if window_id not in VALID_WINDOW_IDS:
        raise PlaybackError(f"无效的窗口编号：{window_id}，有效范围 1-4")


def get_or_create_session(window_id: int) -> PlaybackSession:
    """
    获取指定窗口的播放会话，若不存在则创建。
    :param window_id: 窗口编号（1-4）
    :return: 对应窗口的播放会话实例
    """
    validate_window_id(window_id)
    session, created = PlaybackSession.objects.get_or_create(
        window_id=window_id,
        defaults={"playback_state": PlaybackState.IDLE},
    )
    if created:
        logger.info("创建窗口 %d 的播放会话 id=%d", window_id, session.pk)
    return session


def get_all_sessions() -> list[PlaybackSession]:
    """
    获取所有窗口的播放会话列表（按 window_id 排序）。
    :return: 播放会话列表
    """
    return list(PlaybackSession.objects.order_by("window_id"))


def get_session_snapshot(window_id: int) -> dict[str, object]:
    """
    获取指定窗口播放会话的完整状态快照，用于页面渲染和 SSE 推送。
    :param window_id: 窗口编号（1-4）
    :return: 包含会话所有状态字段的字典
    """
    session = get_or_create_session(window_id)

    # 关联源信息按“无源”场景填充占位，前端可直接渲染而不需要二次判空。
    source_name = "无"
    source_type = ""
    source_type_label = "无"
    source_uri = ""
    if session.media_source is not None:
        source_name = session.media_source.name
        source_type = session.media_source.source_type
        source_type_label = session.media_source.get_source_type_display()
        source_uri = session.media_source.uri

    return {
        "window_id": session.window_id,
        "session_id": session.pk,
        "source_id": session.media_source_id,
        "source_name": source_name,
        "source_type": source_type,
        "source_type_label": source_type_label,
        "source_uri": source_uri,
        "playback_state": session.playback_state,
        "playback_state_label": session.get_playback_state_display(),
        "display_mode": session.display_mode,
        "display_mode_label": session.get_display_mode_display(),
        "target_display_label": session.target_display_label or "未选择",
        "spliced_display_label": session.spliced_display_label or "无",
        "is_spliced": session.is_spliced,
        "current_slide": session.current_slide,
        "total_slides": session.total_slides,
        "position_ms": session.position_ms,
        "duration_ms": session.duration_ms,
        "pending_command": session.pending_command,
        "last_updated_at": session.last_updated_at.isoformat() if session.last_updated_at else "",
        "volume": session.volume,
        "is_muted": session.is_muted,
        "loop_enabled": session.loop_enabled,
    }


def get_all_sessions_snapshot() -> list[dict[str, object]]:
    """
    获取所有窗口（1-4）的状态快照列表。
    :return: 四个窗口的会话快照列表
    """
    return [get_session_snapshot(window_id) for window_id in sorted(VALID_WINDOW_IDS)]
