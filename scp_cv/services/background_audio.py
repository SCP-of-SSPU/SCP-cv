#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
背景音频服务的稳定公开 interface。

播放列表与临时媒体生命周期由 background_audio_playlist 管理，
播放状态与持久化指令队列由 background_audio_runtime 管理。
@Project : SCP-cv
@File : background_audio.py
@Author : Qintsg
@Date : 2026-05-31
'''
from __future__ import annotations

from scp_cv.services.background_audio_playlist import (
    BackgroundAudioError,
    add_source_to_playlist,
    advance_background_audio_on_finished,
    clear_playlist,
    handle_media_source_deleted,
    play_next_background_audio,
    play_playlist_item,
    play_previous_background_audio,
    play_source,
    remove_playlist_item,
    resume_background_audio,
    stop_background_audio,
)
from scp_cv.services.background_audio_runtime import (
    clear_background_audio_command,
    pause_background_audio,
    seek_background_audio,
    set_background_audio_loop,
    set_background_audio_mute,
    set_background_audio_volume,
    update_background_audio_progress,
)

__all__ = [
    "BackgroundAudioError",
    "add_source_to_playlist",
    "advance_background_audio_on_finished",
    "clear_background_audio_command",
    "clear_playlist",
    "handle_media_source_deleted",
    "pause_background_audio",
    "play_next_background_audio",
    "play_playlist_item",
    "play_previous_background_audio",
    "play_source",
    "remove_playlist_item",
    "resume_background_audio",
    "seek_background_audio",
    "set_background_audio_loop",
    "set_background_audio_mute",
    "set_background_audio_volume",
    "stop_background_audio",
    "update_background_audio_progress",
]
