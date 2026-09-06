#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
背景音频持久命令队列回归测试。
@Project : SCP-cv
@File : test_background_audio_command_queue.py
@Author : Qintsg
@Date : 2026-08-30
'''
from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from scp_cv.apps.playback.models import (
    BackgroundAudioCommand,
    BackgroundAudioCommandRecord,
    BackgroundAudioState,
)
from scp_cv.services.background_audio_commands import (
    acknowledge_background_audio_command,
    claim_next_background_audio_command,
    enqueue_background_audio_command,
)


@pytest.mark.django_db(transaction=True)
def test_open_pause_are_ordered_and_old_ack_cannot_delete_new_command() -> None:
    """OPEN→PAUSE 必须保序，错误消费者确认不能误删记录。"""
    state = BackgroundAudioState.get_instance()
    opened = enqueue_background_audio_command(state, BackgroundAudioCommand.OPEN, {"uri": "a.mp3"})
    enqueue_background_audio_command(state, BackgroundAudioCommand.PAUSE)

    claimed = claim_next_background_audio_command("consumer-a")
    assert claimed is not None and claimed.id == opened.id
    assert claim_next_background_audio_command("consumer-b") is None
    assert acknowledge_background_audio_command(claimed.id, "consumer-b") is False
    assert BackgroundAudioCommandRecord.objects.filter(pk=claimed.id, status="processing").exists()

    assert acknowledge_background_audio_command(claimed.id, "consumer-a") is True
    next_claim = claim_next_background_audio_command("consumer-b")
    assert next_claim is not None
    assert next_claim.command == BackgroundAudioCommand.PAUSE


@pytest.mark.django_db(transaction=True)
def test_expired_background_audio_lease_is_recoverable(settings) -> None:
    """消费者崩溃留下的过期租约应由下一消费者恢复。"""
    settings.PLAYBACK_COMMAND_LEASE_SECONDS = 1
    state = BackgroundAudioState.get_instance()
    record = enqueue_background_audio_command(state, BackgroundAudioCommand.PLAY)
    claimed = claim_next_background_audio_command("dead-consumer")
    assert claimed is not None
    BackgroundAudioCommandRecord.objects.filter(pk=record.pk).update(
        claimed_at=timezone.now() - timedelta(seconds=10),
    )

    recovered = claim_next_background_audio_command("new-consumer")
    assert recovered is not None and recovered.id == record.pk
    assert recovered.consumer_id == "new-consumer"
    assert recovered.command == BackgroundAudioCommand.PLAY


@pytest.mark.django_db(transaction=True)
def test_active_background_consumer_renews_lease(settings) -> None:
    """背景音频 handler 未完成时，同一消费者轮询只续租不重复派发。"""
    settings.PLAYBACK_COMMAND_LEASE_SECONDS = 1
    state = BackgroundAudioState.get_instance()
    record = enqueue_background_audio_command(state, BackgroundAudioCommand.OPEN, {"uri": "a.mp3"})
    assert claim_next_background_audio_command("consumer-a") is not None
    BackgroundAudioCommandRecord.objects.filter(pk=record.pk).update(
        claimed_at=timezone.now() - timedelta(seconds=10),
    )

    assert claim_next_background_audio_command("consumer-a") is None
    record.refresh_from_db()
    assert record.claimed_by == "consumer-a"
    assert record.claimed_at > timezone.now() - timedelta(seconds=1)


@pytest.mark.django_db(transaction=True)
def test_pending_same_kind_commands_are_coalesced_but_processing_is_preserved() -> None:
    """连续音量更新只合并未领取记录，不能删除已处理中的旧记录。"""
    state = BackgroundAudioState.get_instance()
    first = enqueue_background_audio_command(state, BackgroundAudioCommand.SET_VOLUME, {"volume": 10})
    claimed = claim_next_background_audio_command("consumer")
    assert claimed is not None and claimed.id == first.id
    second = enqueue_background_audio_command(state, BackgroundAudioCommand.SET_VOLUME, {"volume": 20})
    third = enqueue_background_audio_command(state, BackgroundAudioCommand.SET_VOLUME, {"volume": 30})

    assert BackgroundAudioCommandRecord.objects.filter(pk=first.pk).exists()
    assert not BackgroundAudioCommandRecord.objects.filter(pk=second.pk).exists()
    assert BackgroundAudioCommandRecord.objects.filter(pk=third.pk, status="pending").exists()


@pytest.mark.django_db(transaction=True)
def test_one_thousand_writes_cannot_be_deleted_by_old_ack() -> None:
    """1000 次并发等价写入后，旧记录确认只能删除其自身。"""
    state = BackgroundAudioState.get_instance()
    first = enqueue_background_audio_command(state, BackgroundAudioCommand.OPEN, {"uri": "a.mp3"})
    claimed = claim_next_background_audio_command("consumer")
    assert claimed is not None and claimed.id == first.pk
    latest = None
    for volume in range(1000):
        latest = enqueue_background_audio_command(
            state,
            BackgroundAudioCommand.SET_VOLUME,
            {"volume": volume % 101},
        )
    assert latest is not None

    acknowledge_background_audio_command(first.pk, "consumer")

    remaining = list(BackgroundAudioCommandRecord.objects.all())
    assert [record.pk for record in remaining] == [latest.pk]
    assert remaining[0].command_args == {"volume": 999 % 101}
