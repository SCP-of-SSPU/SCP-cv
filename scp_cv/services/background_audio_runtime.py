#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
背景音频运行时：统一维护播放状态并写入持久化指令队列。
@Project : SCP-cv
@File : background_audio_runtime.py
@Author : Qintsg
@Date : 2026-07-11
'''
from __future__ import annotations

import logging
from typing import Optional

from scp_cv.apps.playback.models import (
    BackgroundAudioCommand,
    BackgroundAudioState,
    MediaSource,
    PlaybackState,
)

logger = logging.getLogger("scp_cv.services.background_audio")


def queue_background_audio_command(
    state: BackgroundAudioState,
    command: str,
    arguments: dict[str, object] | None = None,
    *,
    supersedes: bool = False,
) -> None:
    """把背景音频控制写入持久化队列并保持旧字段镜像。"""
    from scp_cv.apps.playback.models import ControlCommandTarget
    from scp_cv.services.command_queue import (
        CommandInput,
        enqueue,
        enqueue_batch,
        enqueue_coalesced,
    )

    if supersedes:
        enqueue_batch(
            ControlCommandTarget.BACKGROUND_AUDIO,
            [CommandInput(command, arguments or {})],
            cancel_pending=True,
        )
    elif command in {
        BackgroundAudioCommand.SET_VOLUME,
        BackgroundAudioCommand.SET_MUTE,
        BackgroundAudioCommand.SET_LOOP,
    }:
        enqueue_coalesced(ControlCommandTarget.BACKGROUND_AUDIO, command, arguments)
    else:
        enqueue(ControlCommandTarget.BACKGROUND_AUDIO, command, arguments)
    state.refresh_from_db(fields=["pending_command", "command_args"])


def resume_current_audio(state: BackgroundAudioState) -> BackgroundAudioState:
    """恢复已加载且仍可继续播放的音频。"""
    state.playback_state = PlaybackState.PLAYING
    state.error_message = ""
    state.save(update_fields=["playback_state", "error_message", "updated_at"])
    queue_background_audio_command(state, BackgroundAudioCommand.PLAY)
    logger.info("背景音频恢复播放")
    return state


def pause_background_audio() -> BackgroundAudioState:
    """
    暂停背景音频。

    :return: 更新后的背景音频状态
    """
    state = BackgroundAudioState.get_instance()
    state.playback_state = PlaybackState.PAUSED
    state.save(update_fields=["playback_state", "updated_at"])
    queue_background_audio_command(state, BackgroundAudioCommand.PAUSE)
    logger.info("背景音频暂停")
    return state


def stop_audio_state(
    state: BackgroundAudioState,
    clear_source: bool = False,
) -> BackgroundAudioState:
    """停止运行时并根据请求保留或清空当前源。"""
    if clear_source:
        state.current_source = None
        state.playback_state = PlaybackState.IDLE
    else:
        state.playback_state = PlaybackState.STOPPED
    state.error_message = ""
    state.position_ms = 0
    state.duration_ms = 0
    state.save(update_fields=[
        "current_source",
        "playback_state",
        "error_message",
        "position_ms",
        "duration_ms",
        "updated_at",
    ])
    queue_background_audio_command(
        state,
        BackgroundAudioCommand.STOP,
        {"clear_source": bool(clear_source)},
        supersedes=True,
    )
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
    state.save(update_fields=["position_ms", "updated_at"])
    queue_background_audio_command(
        state,
        BackgroundAudioCommand.SEEK,
        {"position_ms": normalized_position},
    )
    return state


def set_background_audio_volume(volume: int) -> BackgroundAudioState:
    """
    设置背景音频音量。

    :param volume: 音量等级（0-100）
    :return: 更新后的背景音频状态
    """
    normalized_volume = max(0, min(100, int(volume)))
    state = BackgroundAudioState.get_instance()
    state.volume = normalized_volume
    state.save(update_fields=["volume", "updated_at"])
    queue_background_audio_command(
        state,
        BackgroundAudioCommand.SET_VOLUME,
        {"volume": normalized_volume},
    )
    return state


def set_background_audio_mute(muted: bool) -> BackgroundAudioState:
    """
    设置背景音频静音状态。

    :param muted: 是否静音
    :return: 更新后的背景音频状态
    """
    state = BackgroundAudioState.get_instance()
    state.is_muted = bool(muted)
    state.save(update_fields=["is_muted", "updated_at"])
    queue_background_audio_command(
        state,
        BackgroundAudioCommand.SET_MUTE,
        {"muted": bool(muted)},
    )
    return state


def set_background_audio_loop(enabled: bool) -> BackgroundAudioState:
    """
    设置背景音频列表循环。

    :param enabled: 是否启用列表循环
    :return: 更新后的背景音频状态
    """
    state = BackgroundAudioState.get_instance()
    state.loop_enabled = bool(enabled)
    state.save(update_fields=["loop_enabled", "updated_at"])
    queue_background_audio_command(
        state,
        BackgroundAudioCommand.SET_LOOP,
        {"enabled": bool(enabled)},
    )
    return state


def clear_background_audio_command() -> BackgroundAudioState:
    """
    清除播放器已执行的背景音频指令。

    :return: 更新后的背景音频状态
    """
    from scp_cv.apps.playback.models import ControlCommandTarget
    from scp_cv.services.command_queue import cancel_pending

    state = BackgroundAudioState.get_instance()
    cancel_pending(ControlCommandTarget.BACKGROUND_AUDIO)
    state.refresh_from_db(fields=["pending_command", "command_args"])
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
    update_fields: list[str] = []
    if playback_state is not None:
        state.playback_state = playback_state
        state.error_message = error_message or "" if playback_state == PlaybackState.ERROR else ""
        update_fields.extend(["playback_state", "error_message"])
    if position_ms is not None:
        state.position_ms = max(0, int(position_ms))
        update_fields.append("position_ms")
    if duration_ms is not None:
        state.duration_ms = max(0, int(duration_ms))
        update_fields.append("duration_ms")
    if update_fields:
        update_fields.append("updated_at")
        state.save(update_fields=update_fields)
    return state


def mark_background_audio_finished(state: BackgroundAudioState) -> BackgroundAudioState:
    """在列表不再继续时记录自然播放完成。"""
    state.playback_state = PlaybackState.STOPPED
    state.position_ms = state.duration_ms
    state.save(update_fields=["playback_state", "position_ms", "updated_at"])
    return state


def open_audio_source(source: MediaSource, autoplay: bool) -> BackgroundAudioState:
    """切换当前音频源并以终端 OPEN 批次替换旧指令。"""
    state = BackgroundAudioState.get_instance()
    state.current_source = source
    state.playback_state = PlaybackState.LOADING
    state.error_message = ""
    state.position_ms = 0
    state.duration_ms = 0
    command_args: dict[str, object] = {
        "source_id": source.pk,
        "uri": source.uri,
        "autoplay": autoplay,
        "volume": state.volume,
        "muted": state.is_muted,
    }
    state.save(update_fields=[
        "current_source",
        "playback_state",
        "error_message",
        "position_ms",
        "duration_ms",
        "updated_at",
    ])
    queue_background_audio_command(
        state,
        BackgroundAudioCommand.OPEN,
        command_args,
        supersedes=True,
    )
    logger.info("背景音频打开「%s」", source.name)
    return state
