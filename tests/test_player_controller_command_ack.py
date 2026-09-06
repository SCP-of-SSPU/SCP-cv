#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
播放器主线程执行后确认命令的回归测试。
@Project : SCP-cv
@File : test_player_controller_command_ack.py
@Author : Qintsg
@Date : 2026-08-30
'''
from __future__ import annotations

import pytest

from scp_cv.apps.playback.models import (
    BackgroundAudioCommand,
    BackgroundAudioCommandRecord,
    BackgroundAudioState,
    PlaybackCommand,
    PlaybackCommandRecord,
)
from scp_cv.player.controller import PlayerController
from scp_cv.services.background_audio_commands import (
    claim_next_background_audio_command,
    enqueue_background_audio_command,
)
from scp_cv.services.playback import get_or_create_session
from scp_cv.services.playback_commands import claim_next_playback_command, enqueue_playback_command


@pytest.mark.django_db(transaction=True)
def test_playback_command_is_acknowledged_only_after_main_thread_handler() -> None:
    """队列记录应在主线程 handler 返回后删除。"""
    session = get_or_create_session(1)
    record = enqueue_playback_command(session, PlaybackCommand.SHOW_ID)
    claimed = claim_next_playback_command(1, "consumer")
    assert claimed is not None
    controller = PlayerController(enable_background_audio=False)
    handled: list[int] = []
    controller._handle_show_id = lambda window_id, _args: handled.append(window_id)  # type: ignore[method-assign]

    assert PlaybackCommandRecord.objects.filter(pk=record.pk, status="processing").exists()
    controller._execute_command_on_main_thread(
        1,
        PlaybackCommand.SHOW_ID,
        {},
        record.pk,
        "consumer",
    )

    assert handled == [1]
    assert not PlaybackCommandRecord.objects.filter(pk=record.pk).exists()


class _AudioAdapter:
    """记录背景音频暂停调用。"""

    def __init__(self) -> None:
        self.paused = False

    def pause(self) -> None:
        """记录暂停。"""
        self.paused = True


@pytest.mark.django_db(transaction=True)
def test_background_audio_command_ack_uses_record_id() -> None:
    """旧记录确认不能通过清空单槽误删新记录。"""
    state = BackgroundAudioState.get_instance()
    first = enqueue_background_audio_command(state, BackgroundAudioCommand.PAUSE)
    second = enqueue_background_audio_command(state, BackgroundAudioCommand.PLAY)
    claimed = claim_next_background_audio_command("consumer")
    assert claimed is not None and claimed.id == first.pk
    adapter = _AudioAdapter()
    controller = PlayerController(enable_background_audio=False)
    controller._background_audio_adapter = adapter

    controller._execute_background_audio_command_on_main_thread(
        first.pk,
        BackgroundAudioCommand.PAUSE,
        {},
        "consumer",
    )

    assert adapter.paused is True
    assert not BackgroundAudioCommandRecord.objects.filter(pk=first.pk).exists()
    assert BackgroundAudioCommandRecord.objects.filter(pk=second.pk).exists()
