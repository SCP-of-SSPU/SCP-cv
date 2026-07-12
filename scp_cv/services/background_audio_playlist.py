#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
背景音频列表：统一管理源校验、相对导航与临时媒体生命周期。
@Project : SCP-cv
@File : background_audio_playlist.py
@Author : Qintsg
@Date : 2026-07-11
'''
from __future__ import annotations

import logging
from typing import Optional

from django.db import transaction
from django.db.models import Max

from scp_cv.apps.playback.models import (
    BackgroundAudioPlaylistItem,
    BackgroundAudioState,
    MediaSource,
    PlaybackState,
    SourceType,
)
from scp_cv.services.background_audio_runtime import (
    mark_background_audio_finished,
    open_audio_source,
    resume_current_audio,
    stop_audio_state,
)

logger = logging.getLogger("scp_cv.services.background_audio")


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
    return open_audio_source(item.source, autoplay=True)


@transaction.atomic
def resume_background_audio() -> BackgroundAudioState:
    """
    恢复当前音频；若当前没有音频，则播放列表首项。

    :return: 更新后的背景音频状态
    :raises BackgroundAudioError: 播放列表为空时
    """
    state = BackgroundAudioState.get_instance()
    if state.current_source_id and state.playback_state not in {PlaybackState.STOPPED, PlaybackState.ERROR}:
        return resume_current_audio(state)
    if state.current_source_id:
        source = _get_audio_source(state.current_source_id)
        return open_audio_source(source, autoplay=True)

    first_item = BackgroundAudioPlaylistItem.objects.select_related("source").first()
    if first_item is None:
        raise BackgroundAudioError("背景音频播放列表为空")
    return open_audio_source(first_item.source, autoplay=True)


def stop_background_audio(clear_source: bool = False) -> BackgroundAudioState:
    """
    停止背景音频。

    :param clear_source: 是否同时清空当前源；删除当前列表项时使用
    :return: 更新后的背景音频状态
    """
    state = BackgroundAudioState.get_instance()
    cleanup_source_id = _temporary_source_id(state.current_source)
    effective_clear_source = bool(clear_source or cleanup_source_id)
    state = stop_audio_state(state, clear_source=effective_clear_source)
    if cleanup_source_id:
        BackgroundAudioPlaylistItem.objects.filter(source_id=cleanup_source_id).delete()
        _delete_temporary_audio_source(cleanup_source_id)
    logger.info("背景音频停止，clear_source=%s", effective_clear_source)
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
        return open_audio_source(playlist[0].source, autoplay=True)
    next_index = current_index + 1
    if next_index < len(playlist):
        return open_audio_source(playlist[next_index].source, autoplay=True)
    if state.loop_enabled:
        return open_audio_source(playlist[0].source, autoplay=True)
    return mark_background_audio_finished(state)


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
    """查询并校验音频媒体源。"""
    try:
        source = MediaSource.objects.get(pk=media_source_id)
    except MediaSource.DoesNotExist as not_found:
        raise BackgroundAudioError(f"媒体源 id={media_source_id} 不存在") from not_found
    if source.source_type != SourceType.AUDIO:
        raise BackgroundAudioError("背景音乐只能使用音频源")
    return source


def _temporary_source_id(source: MediaSource | None) -> int | None:
    """返回需随播放列表生命周期回收的临时音频源 ID。"""
    if source is None:
        return None
    if source.source_type == SourceType.AUDIO and source.is_temporary:
        return int(source.pk)
    return None


def _delete_temporary_audio_source(media_source_id: int) -> None:
    """删除不应持久化的临时音频源。"""
    from scp_cv.services.media import MediaError, delete_temporary_source_if_unused

    try:
        delete_temporary_source_if_unused(media_source_id)
    except MediaError as cleanup_error:
        logger.warning("清理临时背景音频源失败：source_id=%s, error=%s", media_source_id, cleanup_error)


def _get_playlist_item(item_id: int) -> BackgroundAudioPlaylistItem:
    """查询播放列表项。"""
    try:
        return BackgroundAudioPlaylistItem.objects.select_related("source").get(pk=item_id)
    except BackgroundAudioPlaylistItem.DoesNotExist as not_found:
        raise BackgroundAudioError(f"背景音频播放列表项 id={item_id} 不存在") from not_found


def _play_relative_item(step: int) -> BackgroundAudioState:
    """按当前源在已排序列表中的相对位置播放。"""
    state = BackgroundAudioState.get_instance()
    playlist = list(BackgroundAudioPlaylistItem.objects.select_related("source").all())
    if not playlist:
        raise BackgroundAudioError("背景音频播放列表为空")
    current_index = _current_playlist_index(playlist, state.current_source_id)
    target_index = 0 if current_index is None else (current_index + step) % len(playlist)
    return open_audio_source(playlist[target_index].source, autoplay=True)


def _current_playlist_index(
    playlist: list[BackgroundAudioPlaylistItem],
    source_id: Optional[int],
) -> int | None:
    """查找当前源在播放列表中的位置。"""
    if not source_id:
        return None
    for index, item in enumerate(playlist):
        if item.source_id == source_id:
            return index
    return None
