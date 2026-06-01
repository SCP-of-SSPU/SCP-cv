#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
背景音频服务：维护全局播放状态、播放列表与播放器指令。
@Project : SCP-cv
@File : background_audio.py
@Author : Qintsg
@Date : 2026-05-31
'''
from __future__ import annotations

import logging
from typing import Optional

from django.db import transaction
from django.db.models import Max

from scp_cv.apps.playback.models import (
    BackgroundAudioCommand,
    BackgroundAudioPlaylistItem,
    BackgroundAudioState,
    MediaSource,
    PlaybackState,
    SourceType,
)
from scp_cv.services.background_audio_payloads import get_background_audio_snapshot

logger = logging.getLogger(__name__)


class BackgroundAudioError(ValueError):
    """背景音频业务异常。"""


@transaction.atomic
def add_source_to_playlist(media_source_id: int) -> BackgroundAudioPlaylistItem:
    """
    将音频媒体源加入背景音频播放列表。

    :param media_source_id: MediaSource 主键
    :return: 新建或已存在的播放列表项
    :raises BackgroundAudioError: 媒体源不存在或不是 audio 时
    """
    source = _get_audio_source(media_source_id)
    existing = BackgroundAudioPlaylistItem.objects.filter(source=source).first()
    if existing is not None:
        return existing

    next_order = int(BackgroundAudioPlaylistItem.objects.aggregate(Max("sort_order"))["sort_order__max"] or 0) + 10
    item = BackgroundAudioPlaylistItem.objects.create(source=source, sort_order=next_order)
    logger.info("背景音频播放列表加入「%s」", source.name)
    return item


def play_source(media_source_id: int) -> BackgroundAudioState:
    """
    加入并立即播放指定音频源。

    :param media_source_id: MediaSource 主键
    :return: 更新后的背景音频状态
    :raises BackgroundAudioError: 媒体源不存在或不是 audio 时
    """
    item = add_source_to_playlist(media_source_id)
    return play_playlist_item(item.pk)


@transaction.atomic
def play_playlist_item(item_id: int) -> BackgroundAudioState:
    """
    播放指定播放列表项。

    :param item_id: 播放列表项主键
    :return: 更新后的背景音频状态
    :raises BackgroundAudioError: 播放列表项不存在时
    """
    item = _get_playlist_item(item_id)
    return _open_source(item.source, autoplay=True)


@transaction.atomic
def resume_background_audio() -> BackgroundAudioState:
    """
    恢复当前音频；若当前没有音频，则播放列表首项。

    :return: 更新后的背景音频状态
    :raises BackgroundAudioError: 播放列表为空时
    """
    state = BackgroundAudioState.get_instance()
    if state.current_source_id and state.playback_state not in {PlaybackState.STOPPED, PlaybackState.ERROR}:
        state.playback_state = PlaybackState.PLAYING
        state.error_message = ""
        state.pending_command = BackgroundAudioCommand.PLAY
        state.command_args = {}
        state.save()
        logger.info("背景音频恢复播放")
        return state
    if state.current_source_id:
        source = _get_audio_source(state.current_source_id)
        return _open_source(source, autoplay=True)

    first_item = BackgroundAudioPlaylistItem.objects.select_related("source").first()
    if first_item is None:
        raise BackgroundAudioError("背景音频播放列表为空")
    return _open_source(first_item.source, autoplay=True)


def pause_background_audio() -> BackgroundAudioState:
    """
    暂停背景音频。

    :return: 更新后的背景音频状态
    """
    state = BackgroundAudioState.get_instance()
    state.playback_state = PlaybackState.PAUSED
    state.pending_command = BackgroundAudioCommand.PAUSE
    state.command_args = {}
    state.save()
    logger.info("背景音频暂停")
    return state


def stop_background_audio(clear_source: bool = False) -> BackgroundAudioState:
    """
    停止背景音频。

    :param clear_source: 是否同时清空当前源；删除当前列表项时使用
    :return: 更新后的背景音频状态
    """
    state = BackgroundAudioState.get_instance()
    cleanup_source_id = _temporary_source_id(state.current_source)
    if cleanup_source_id:
        clear_source = True
    if clear_source:
        state.current_source = None
        state.playback_state = PlaybackState.IDLE
    else:
        state.playback_state = PlaybackState.STOPPED
    state.error_message = ""
    state.position_ms = 0
    state.duration_ms = 0
    state.pending_command = BackgroundAudioCommand.STOP
    state.command_args = {"clear_source": bool(clear_source)}
    state.save()
    if cleanup_source_id:
        BackgroundAudioPlaylistItem.objects.filter(source_id=cleanup_source_id).delete()
        _delete_temporary_audio_source(cleanup_source_id)
    logger.info("背景音频停止，clear_source=%s", clear_source)
    return state


def seek_background_audio(position_ms: int) -> BackgroundAudioState:
    """
    跳转背景音频播放进度。

    :param position_ms: 目标位置毫秒
    :return: 更新后的背景音频状态
    """
    state = BackgroundAudioState.get_instance()
    normalized_position = max(0, int(position_ms))
    state.position_ms = normalized_position
    state.pending_command = BackgroundAudioCommand.SEEK
    state.command_args = {"position_ms": normalized_position}
    state.save()
    return state


def play_next_background_audio() -> BackgroundAudioState:
    """
    播放下一首背景音频。

    :return: 更新后的背景音频状态
    :raises BackgroundAudioError: 播放列表为空时
    """
    return _play_relative_item(step=1)


def play_previous_background_audio() -> BackgroundAudioState:
    """
    播放上一首背景音频。

    :return: 更新后的背景音频状态
    :raises BackgroundAudioError: 播放列表为空时
    """
    return _play_relative_item(step=-1)


def set_background_audio_volume(volume: int) -> BackgroundAudioState:
    """
    设置背景音频音量。

    :param volume: 音量等级（0-100）
    :return: 更新后的背景音频状态
    """
    normalized_volume = max(0, min(100, int(volume)))
    state = BackgroundAudioState.get_instance()
    state.volume = normalized_volume
    state.pending_command = BackgroundAudioCommand.SET_VOLUME
    state.command_args = {"volume": normalized_volume}
    state.save()
    return state


def set_background_audio_mute(muted: bool) -> BackgroundAudioState:
    """
    设置背景音频静音状态。

    :param muted: 是否静音
    :return: 更新后的背景音频状态
    """
    state = BackgroundAudioState.get_instance()
    state.is_muted = bool(muted)
    state.pending_command = BackgroundAudioCommand.SET_MUTE
    state.command_args = {"muted": bool(muted)}
    state.save()
    return state


def set_background_audio_loop(enabled: bool) -> BackgroundAudioState:
    """
    设置背景音频列表循环。

    :param enabled: 是否启用列表循环
    :return: 更新后的背景音频状态
    """
    state = BackgroundAudioState.get_instance()
    state.loop_enabled = bool(enabled)
    state.pending_command = BackgroundAudioCommand.SET_LOOP
    state.command_args = {"enabled": bool(enabled)}
    state.save()
    return state


@transaction.atomic
def remove_playlist_item(item_id: int) -> BackgroundAudioState:
    """
    删除背景音频播放列表项；删除当前播放项时自动停止。

    :param item_id: 播放列表项主键
    :return: 更新后的背景音频状态
    :raises BackgroundAudioError: 播放列表项不存在时
    """
    item = _get_playlist_item(item_id)
    state = BackgroundAudioState.get_instance()
    should_stop = state.current_source_id == item.source_id
    cleanup_source_id = _temporary_source_id(item.source)
    item.delete()
    logger.info("背景音频播放列表移除 source_id=%s", item.source_id)
    if should_stop:
        state = stop_background_audio(clear_source=True)
    if cleanup_source_id:
        _delete_temporary_audio_source(cleanup_source_id)
    return state


@transaction.atomic
def clear_playlist() -> BackgroundAudioState:
    """
    清空背景音频播放列表并停止当前播放。

    :return: 更新后的背景音频状态
    """
    cleanup_source_ids = set(
        BackgroundAudioPlaylistItem.objects.filter(source__is_temporary=True).values_list("source_id", flat=True),
    )
    state = BackgroundAudioState.get_instance()
    current_cleanup_source_id = _temporary_source_id(state.current_source)
    if current_cleanup_source_id:
        cleanup_source_ids.add(current_cleanup_source_id)
    BackgroundAudioPlaylistItem.objects.all().delete()
    state = stop_background_audio(clear_source=True)
    for source_id in cleanup_source_ids:
        _delete_temporary_audio_source(int(source_id))
    return state


def clear_background_audio_command() -> BackgroundAudioState:
    """
    清除播放器已执行的背景音频指令。

    :return: 更新后的背景音频状态
    """
    state = BackgroundAudioState.get_instance()
    state.pending_command = BackgroundAudioCommand.NONE
    state.command_args = {}
    state.save(update_fields=["pending_command", "command_args", "updated_at"])
    return state


def update_background_audio_progress(
    playback_state: Optional[str] = None,
    error_message: Optional[str] = None,
    position_ms: Optional[int] = None,
    duration_ms: Optional[int] = None,
) -> BackgroundAudioState:
    """
    播放器进程回写背景音频播放状态。

    :param playback_state: 播放状态
    :param error_message: 错误说明
    :param position_ms: 当前进度毫秒
    :param duration_ms: 总时长毫秒
    :return: 更新后的背景音频状态
    """
    state = BackgroundAudioState.get_instance()
    if playback_state is not None:
        state.playback_state = playback_state
        state.error_message = error_message or "" if playback_state == PlaybackState.ERROR else ""
    if position_ms is not None:
        state.position_ms = max(0, int(position_ms))
    if duration_ms is not None:
        state.duration_ms = max(0, int(duration_ms))
    state.save()
    return state


@transaction.atomic
def advance_background_audio_on_finished() -> BackgroundAudioState:
    """
    当前音频自然结束后推进到下一首，必要时按列表循环回到首项。

    :return: 更新后的背景音频状态
    """
    state = BackgroundAudioState.get_instance()
    playlist = list(BackgroundAudioPlaylistItem.objects.select_related("source").all())
    if not playlist:
        return stop_background_audio(clear_source=True)
    current_index = _current_playlist_index(playlist, state.current_source_id)
    if current_index is None:
        return _open_source(playlist[0].source, autoplay=True)
    next_index = current_index + 1
    if next_index < len(playlist):
        return _open_source(playlist[next_index].source, autoplay=True)
    if state.loop_enabled:
        return _open_source(playlist[0].source, autoplay=True)

    state.playback_state = PlaybackState.STOPPED
    state.position_ms = state.duration_ms
    state.pending_command = BackgroundAudioCommand.NONE
    state.command_args = {}
    state.save()
    return state


@transaction.atomic
def handle_media_source_deleted(media_source_id: int) -> None:
    """
    媒体源删除前同步清理背景音频引用。

    :param media_source_id: 将被删除的 MediaSource 主键
    :return: None
    """
    state = BackgroundAudioState.get_instance()
    should_stop = state.current_source_id == media_source_id
    BackgroundAudioPlaylistItem.objects.filter(source_id=media_source_id).delete()
    if should_stop:
        stop_background_audio(clear_source=True)


def _get_audio_source(media_source_id: int) -> MediaSource:
    """
    查询并校验音频媒体源。

    :param media_source_id: MediaSource 主键
    :return: audio 类型 MediaSource
    :raises BackgroundAudioError: 不存在或类型不符时
    """
    try:
        source = MediaSource.objects.get(pk=media_source_id)
    except MediaSource.DoesNotExist as not_found:
        raise BackgroundAudioError(f"媒体源 id={media_source_id} 不存在") from not_found
    if source.source_type != SourceType.AUDIO:
        raise BackgroundAudioError("背景音乐只能使用音频源")
    return source


def _temporary_source_id(source: MediaSource | None) -> int | None:
    """
    返回临时音频源 ID。

    :param source: 媒体源或 None
    :return: 临时音频源主键；非临时或非音频返回 None
    """
    if source is None:
        return None
    if source.source_type == SourceType.AUDIO and source.is_temporary:
        return int(source.pk)
    return None


def _delete_temporary_audio_source(media_source_id: int) -> None:
    """
    删除不应持久化的临时音频源。

    :param media_source_id: 媒体源主键
    :return: None
    """
    from scp_cv.services.media import MediaError, delete_temporary_source_if_unused

    try:
        delete_temporary_source_if_unused(media_source_id)
    except MediaError as cleanup_error:
        logger.warning("清理临时背景音频源失败：source_id=%s, error=%s", media_source_id, cleanup_error)


def _get_playlist_item(item_id: int) -> BackgroundAudioPlaylistItem:
    """
    查询播放列表项。

    :param item_id: 播放列表项主键
    :return: 播放列表项
    :raises BackgroundAudioError: 不存在时
    """
    try:
        return BackgroundAudioPlaylistItem.objects.select_related("source").get(pk=item_id)
    except BackgroundAudioPlaylistItem.DoesNotExist as not_found:
        raise BackgroundAudioError(f"背景音频播放列表项 id={item_id} 不存在") from not_found


def _open_source(source: MediaSource, autoplay: bool) -> BackgroundAudioState:
    """
    下发打开背景音频源指令。

    :param source: 音频媒体源
    :param autoplay: 是否自动播放
    :return: 更新后的背景音频状态
    """
    state = BackgroundAudioState.get_instance()
    state.current_source = source
    state.playback_state = PlaybackState.LOADING
    state.error_message = ""
    state.position_ms = 0
    state.duration_ms = 0
    state.pending_command = BackgroundAudioCommand.OPEN
    state.command_args = {
        "source_id": source.pk,
        "uri": source.uri,
        "autoplay": autoplay,
        "volume": state.volume,
        "muted": state.is_muted,
    }
    state.save()
    logger.info("背景音频打开「%s」", source.name)
    return state


def _play_relative_item(step: int) -> BackgroundAudioState:
    """
    按相对位置播放上一首或下一首。

    :param step: 1 表示下一首，-1 表示上一首
    :return: 更新后的背景音频状态
    :raises BackgroundAudioError: 播放列表为空时
    """
    state = BackgroundAudioState.get_instance()
    playlist = list(BackgroundAudioPlaylistItem.objects.select_related("source").all())
    if not playlist:
        raise BackgroundAudioError("背景音频播放列表为空")
    current_index = _current_playlist_index(playlist, state.current_source_id)
    if current_index is None:
        target_index = 0
    else:
        target_index = (current_index + step) % len(playlist)
    return _open_source(playlist[target_index].source, autoplay=True)


def _current_playlist_index(
    playlist: list[BackgroundAudioPlaylistItem],
    source_id: Optional[int],
) -> int | None:
    """
    查找当前源在播放列表中的位置。

    :param playlist: 已排序播放列表
    :param source_id: 当前源 ID
    :return: 当前索引；未找到返回 None
    """
    if not source_id:
        return None
    for index, item in enumerate(playlist):
        if item.source_id == source_id:
            return index
    return None
