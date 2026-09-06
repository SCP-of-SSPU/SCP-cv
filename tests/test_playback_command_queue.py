"""播放指令队列的顺序与覆盖语义测试。"""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from scp_cv.apps.playback.models import MediaSource, PlaybackCommand, PlaybackCommandRecord
from scp_cv.services.playback import control_playback, navigate_content, open_source
from scp_cv.services.playback_commands import (
    acknowledge_playback_command,
    claim_next_playback_command,
    clear_playback_command_queue,
)


@pytest.mark.django_db(transaction=True)
def test_consecutive_navigation_commands_are_claimed_in_order(
    media_source_ppt: MediaSource,
) -> None:
    """连续 PPT 翻页必须逐条交付，不能被单槽 pending_command 合并。"""
    open_source(1, media_source_ppt.pk)
    first_open = claim_next_playback_command(1)
    assert first_open is not None
    acknowledge_playback_command(first_open.id)

    navigate_content(1, PlaybackCommand.NEXT)
    navigate_content(1, PlaybackCommand.NEXT)
    navigate_content(1, PlaybackCommand.PREV)

    claimed = []
    while command := claim_next_playback_command(1):
        claimed.append(command.command)
        acknowledge_playback_command(command.id)

    assert claimed == [PlaybackCommand.NEXT, PlaybackCommand.NEXT, PlaybackCommand.PREV]


@pytest.mark.django_db(transaction=True)
def test_new_open_discards_commands_for_previous_content(
    media_source_ppt: MediaSource,
    media_source_video: MediaSource,
) -> None:
    """切换到新源时不得继续执行旧源尚未消费的控制指令。"""
    open_source(1, media_source_ppt.pk)
    first_open = claim_next_playback_command(1)
    assert first_open is not None
    acknowledge_playback_command(first_open.id)

    navigate_content(1, PlaybackCommand.NEXT)
    control_playback(1, PlaybackCommand.PAUSE)
    open_source(1, media_source_video.pk)

    replacement = claim_next_playback_command(1)
    assert replacement is not None
    assert replacement.command == PlaybackCommand.OPEN
    assert replacement.command_args["source_id"] == media_source_video.pk
    acknowledge_playback_command(replacement.id)
    assert claim_next_playback_command(1) is None


@pytest.mark.django_db(transaction=True)
def test_active_consumer_renews_lease_without_duplicate_delivery(
    media_source_video: MediaSource,
    settings,
) -> None:
    """长时间执行期间同一消费者轮询只能续租，不能重复投递。"""
    settings.PLAYBACK_COMMAND_LEASE_SECONDS = 1
    open_source(1, media_source_video.pk)
    first = claim_next_playback_command(1, "consumer-a")
    assert first is not None
    PlaybackCommandRecord.objects.filter(pk=first.id).update(
        claimed_at=timezone.now() - timedelta(seconds=10),
    )

    assert claim_next_playback_command(1, "consumer-a") is None
    record = PlaybackCommandRecord.objects.get(pk=first.id)
    assert record.claimed_by == "consumer-a"
    assert record.claimed_at > timezone.now() - timedelta(seconds=1)


@pytest.mark.django_db(transaction=True)
def test_new_open_preserves_already_processing_command(
    media_source_ppt: MediaSource,
    media_source_video: MediaSource,
) -> None:
    """终止/替换命令只能清理 pending，不能删除已经执行中的记录。"""
    open_source(1, media_source_ppt.pk)
    processing = claim_next_playback_command(1, "consumer")
    assert processing is not None
    navigate_content(1, PlaybackCommand.NEXT)

    open_source(1, media_source_video.pk)

    records = list(
        PlaybackCommandRecord.objects.filter(session__window_id=1)
        .order_by("id")
        .values_list("id", "command", "status")
    )
    assert records == [
        (processing.id, PlaybackCommand.OPEN, "processing"),
        (records[1][0], PlaybackCommand.OPEN, "pending"),
    ]


@pytest.mark.django_db(transaction=True)
def test_one_hundred_expired_playback_leases_are_recoverable(
    media_source_video: MediaSource,
    settings,
) -> None:
    """模拟 100 次领取后崩溃，命令保留率必须为 100%。"""
    settings.PLAYBACK_COMMAND_LEASE_SECONDS = 1
    for attempt in range(100):
        session = open_source(1, media_source_video.pk)
        claimed = claim_next_playback_command(1, f"dead-{attempt}")
        assert claimed is not None
        PlaybackCommandRecord.objects.filter(pk=claimed.id).update(
            claimed_at=timezone.now() - timedelta(seconds=10),
        )
        recovered = claim_next_playback_command(1, f"recovered-{attempt}")
        assert recovered is not None and recovered.id == claimed.id
        acknowledge_playback_command(recovered.id, recovered.consumer_id)
        clear_playback_command_queue(session)
