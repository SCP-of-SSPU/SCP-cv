#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
背景音频响应序列化工具。
@Project : SCP-cv
@File : background_audio_payloads.py
@Author : Qintsg
@Date : 2026-05-31
'''
from __future__ import annotations

from typing import Optional

from scp_cv.apps.playback.models import BackgroundAudioPlaylistItem, BackgroundAudioState
from scp_cv.services.media_queries import media_source_payload


def get_background_audio_snapshot() -> dict[str, object]:
    """
    获取背景音频完整快照。

    :return: 包含全局状态和播放列表的字典
    """
    return {
        "state": background_audio_state_payload(BackgroundAudioState.get_instance()),
        "playlist": list_background_audio_playlist(),
    }


def background_audio_state_payload(state: BackgroundAudioState) -> dict[str, object]:
    """
    序列化背景音频全局状态。

    :param state: 背景音频状态实例
    :return: 前端和 SSE 共用的状态字典
    """
    source = state.current_source
    current_item = _playlist_item_for_source(source.pk if source else None)
    return {
        "id": state.pk,
        "source_id": source.pk if source else None,
        "source_name": source.name if source else "",
        "source_uri": source.uri if source else "",
        "source": media_source_payload(source) if source else None,
        "current_item_id": current_item.pk if current_item else None,
        "playback_state": state.playback_state,
        "playback_state_label": state.get_playback_state_display(),
        "error_message": state.error_message,
        "position_ms": state.position_ms,
        "duration_ms": state.duration_ms,
        "volume": state.volume,
        "is_muted": state.is_muted,
        "loop_enabled": state.loop_enabled,
        "pending_command": state.pending_command,
        "updated_at": state.updated_at.isoformat() if state.updated_at else "",
    }


def list_background_audio_playlist() -> list[dict[str, object]]:
    """
    查询背景音频播放列表。

    :return: 播放列表项字典列表
    """
    return [
        background_audio_playlist_item_payload(item)
        for item in BackgroundAudioPlaylistItem.objects.select_related("source").all()
    ]


def background_audio_playlist_item_payload(item: BackgroundAudioPlaylistItem) -> dict[str, object]:
    """
    序列化背景音频播放列表项。

    :param item: 播放列表项实例
    :return: 播放列表项字典
    """
    return {
        "id": item.pk,
        "source_id": item.source_id,
        "source_name": item.source.name,
        "sort_order": item.sort_order,
        "created_at": item.created_at.isoformat() if item.created_at else "",
        "source": media_source_payload(item.source),
    }


def _playlist_item_for_source(source_id: Optional[int]) -> BackgroundAudioPlaylistItem | None:
    """
    按当前源查询播放列表项。

    :param source_id: 媒体源 ID
    :return: 播放列表项或 None
    """
    if not source_id:
        return None
    return BackgroundAudioPlaylistItem.objects.filter(source_id=source_id).first()
