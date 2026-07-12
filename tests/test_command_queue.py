#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
持久化控制命令队列公共接口测试。
@Project : SCP-cv
@File : test_command_queue.py
@Author : Qintsg
@Date : 2026-07-11
'''
from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from scp_cv.apps.playback.models import (
    ControlCommand,
    ControlCommandStatus,
    ControlCommandTarget,
    PlaybackCommand,
    PlaybackSession,
)
from scp_cv.services.command_queue import (
    CommandConsumerIdentity,
    CommandInput,
    cancel_pending,
    claim_next,
    enqueue,
    enqueue_batch,
    enqueue_coalesced,
    finish,
    prune,
    recover_abandoned,
    release_consumer,
    renew_consumer_lease,
    target_for_window,
)


@pytest.mark.django_db
def test_consecutive_next_commands_are_claimed_in_order_without_loss() -> None:
    """连续翻页指令必须逐条消费，不能被同值命令覆盖。"""
    first = enqueue(ControlCommandTarget.WINDOW_1, PlaybackCommand.NEXT)
    second = enqueue(ControlCommandTarget.WINDOW_1, PlaybackCommand.NEXT)

    first_claim = claim_next(ControlCommandTarget.WINDOW_1, "player-1")

    assert first_claim is not None
    assert first_claim.pk == first.pk
    assert finish(
        first_claim.pk,
        "player-1",
        status=ControlCommandStatus.SUCCEEDED,
    )

    second_claim = claim_next(ControlCommandTarget.WINDOW_1, "player-1")

    assert second_claim is not None
    assert second_claim.pk == second.pk


@pytest.mark.django_db
def test_coalesced_command_updates_matching_pending_record() -> None:
    """同一目标尚未领取的同类设置应保留一条记录并采用最新参数。"""
    session = PlaybackSession.objects.create(window_id=1)

    first = enqueue_coalesced(
        ControlCommandTarget.WINDOW_1,
        PlaybackCommand.SET_VOLUME,
        {"volume": 20},
    )
    replacement = enqueue_coalesced(
        ControlCommandTarget.WINDOW_1,
        PlaybackCommand.SET_VOLUME,
        {"volume": 80},
    )

    session.refresh_from_db()
    queued = list(
        ControlCommand.objects.filter(
            target=ControlCommandTarget.WINDOW_1,
            status=ControlCommandStatus.PENDING,
        )
    )
    assert replacement.pk == first.pk
    assert [item.pk for item in queued] == [first.pk]
    assert queued[0].arguments == {"volume": 80}
    assert session.pending_command == PlaybackCommand.SET_VOLUME
    assert session.command_args == {"volume": 80}


@pytest.mark.django_db
def test_coalesced_command_never_rewrites_executing_record() -> None:
    """同类设置已被领取后，最新设置必须新建待领取记录。"""
    first = enqueue_coalesced(
        ControlCommandTarget.WINDOW_1,
        PlaybackCommand.SET_VOLUME,
        {"volume": 20},
    )
    claim_next(ControlCommandTarget.WINDOW_1, "player-1")

    replacement = enqueue_coalesced(
        ControlCommandTarget.WINDOW_1,
        PlaybackCommand.SET_VOLUME,
        {"volume": 80},
    )

    first.refresh_from_db()
    assert replacement.pk != first.pk
    assert first.status == ControlCommandStatus.EXECUTING
    assert first.arguments == {"volume": 20}
    assert replacement.status == ControlCommandStatus.PENDING
    assert replacement.arguments == {"volume": 80}


@pytest.mark.django_db
def test_target_allows_only_one_executing_command() -> None:
    """同一目标的前一条指令未确认时，不得并行领取下一条。"""
    first = enqueue(ControlCommandTarget.WINDOW_1, PlaybackCommand.OPEN)
    enqueue(ControlCommandTarget.WINDOW_1, PlaybackCommand.NEXT)

    first_claim = claim_next(ControlCommandTarget.WINDOW_1, "player-1")
    overlapping_claim = claim_next(ControlCommandTarget.WINDOW_1, "player-2")

    assert first_claim is not None
    assert first_claim.pk == first.pk
    assert overlapping_claim is None


@pytest.mark.django_db
def test_replacing_batch_cancels_pending_commands() -> None:
    """终止性批次应取消尚未领取的旧指令，再按批次顺序入队。"""
    superseded_next = enqueue(ControlCommandTarget.WINDOW_1, PlaybackCommand.NEXT)
    superseded_prev = enqueue(ControlCommandTarget.WINDOW_1, PlaybackCommand.PREV)

    replacement = enqueue_batch(
        ControlCommandTarget.WINDOW_1,
        [
            CommandInput(PlaybackCommand.CLOSE),
            CommandInput(PlaybackCommand.OPEN, {"source_id": 42}),
        ],
        cancel_pending=True,
    )

    superseded_next.refresh_from_db()
    superseded_prev.refresh_from_db()
    first_claim = claim_next(ControlCommandTarget.WINDOW_1, "player-1")

    assert superseded_next.status == ControlCommandStatus.CANCELLED
    assert superseded_prev.status == ControlCommandStatus.CANCELLED
    assert replacement[0].batch_id == replacement[1].batch_id
    assert first_claim is not None
    assert first_claim.pk == replacement[0].pk


@pytest.mark.django_db
def test_cancel_pending_clears_queue_and_legacy_mirror_without_replacement() -> None:
    """兼容清理入口应取消未执行指令，并把单槽镜像恢复为空。"""
    session = PlaybackSession.objects.create(window_id=1)
    queued = enqueue(ControlCommandTarget.WINDOW_1, PlaybackCommand.NEXT)

    cancelled = cancel_pending(ControlCommandTarget.WINDOW_1)

    queued.refresh_from_db()
    session.refresh_from_db()
    assert cancelled == 1
    assert queued.status == ControlCommandStatus.CANCELLED
    assert session.pending_command == PlaybackCommand.NONE
    assert session.command_args == {}


@pytest.mark.django_db
def test_cancel_requested_forces_executing_command_to_cancelled() -> None:
    """在途指令被取代后，无论执行结果如何都应落为已取消。"""
    opening = enqueue(ControlCommandTarget.WINDOW_1, PlaybackCommand.OPEN)
    claim_next(ControlCommandTarget.WINDOW_1, "player-old")
    closing = enqueue_batch(
        ControlCommandTarget.WINDOW_1,
        [CommandInput(PlaybackCommand.CLOSE)],
        cancel_pending=True,
    )[0]

    assert finish(
        opening.pk,
        "player-old",
        status=ControlCommandStatus.SUCCEEDED,
    )

    opening.refresh_from_db()
    next_claim = claim_next(ControlCommandTarget.WINDOW_1, "player-new")
    assert opening.status == ControlCommandStatus.CANCELLED
    assert next_claim is not None
    assert next_claim.pk == closing.pk


@pytest.mark.django_db
def test_finishing_old_command_keeps_new_command_in_legacy_mirror() -> None:
    """旧指令完成时不得清空随后入队的新指令镜像。"""
    session = PlaybackSession.objects.create(window_id=1)
    first = enqueue(ControlCommandTarget.WINDOW_1, PlaybackCommand.NEXT)
    claim_next(ControlCommandTarget.WINDOW_1, "player-1")
    enqueue(
        ControlCommandTarget.WINDOW_1,
        PlaybackCommand.NEXT,
        {"target_index": 9},
    )

    assert finish(
        first.pk,
        "player-1",
        status=ControlCommandStatus.SUCCEEDED,
    )

    session.refresh_from_db()
    assert session.pending_command == PlaybackCommand.NEXT
    assert session.command_args == {"target_index": 9}


@pytest.mark.django_db
def test_finish_rejects_a_different_consumer_without_changing_mirror() -> None:
    """非领取者不能终结指令，也不能推进旧字段镜像。"""
    session = PlaybackSession.objects.create(window_id=1)
    executing = enqueue(ControlCommandTarget.WINDOW_1, PlaybackCommand.OPEN)
    claim_next(ControlCommandTarget.WINDOW_1, "player-owner")
    enqueue(ControlCommandTarget.WINDOW_1, PlaybackCommand.NEXT)

    finished = finish(
        executing.pk,
        "player-other",
        status=ControlCommandStatus.SUCCEEDED,
    )

    executing.refresh_from_db()
    session.refresh_from_db()
    assert finished is False
    assert executing.status == ControlCommandStatus.EXECUTING
    assert session.pending_command == PlaybackCommand.OPEN


@pytest.mark.django_db
def test_recover_abandoned_fails_old_execution_without_replay() -> None:
    """播放器重启后应终结旧执行记录，不能重放可能已生效的指令。"""
    queued = enqueue(ControlCommandTarget.WINDOW_1, PlaybackCommand.NEXT)
    current_process = CommandConsumerIdentity.current("player-old")
    crashed_process = CommandConsumerIdentity(
        consumer_id=current_process.consumer_id,
        process_id=current_process.process_id,
        process_started_at=current_process.process_started_at - 60,
    )
    claim_next(ControlCommandTarget.WINDOW_1, crashed_process)

    recovered = recover_abandoned(
        ControlCommandTarget.WINDOW_1,
        current_consumer_id="player-new",
    )

    queued.refresh_from_db()
    assert recovered == 1
    assert queued.status == ControlCommandStatus.FAILED
    assert queued.finished_at is not None
    assert claim_next(ControlCommandTarget.WINDOW_1, "player-new") is None


@pytest.mark.django_db
def test_recover_abandoned_preserves_execution_owned_by_live_process() -> None:
    """另一仍存活播放器领取的指令不得被新消费者误判为遗留记录。"""
    queued = enqueue(ControlCommandTarget.WINDOW_1, PlaybackCommand.OPEN)
    claim_next(ControlCommandTarget.WINDOW_1, "player-live")

    recovered = recover_abandoned(
        ControlCommandTarget.WINDOW_1,
        current_consumer_id="player-new",
    )

    queued.refresh_from_db()
    assert recovered == 0
    assert queued.status == ControlCommandStatus.EXECUTING
    assert queued.consumer_id == "player-live"


@pytest.mark.django_db
def test_recover_abandoned_expires_stale_consumer_lease() -> None:
    """播放器进程仍在但长期未续约时，卡死的执行记录也必须可恢复。"""
    queued = enqueue(ControlCommandTarget.WINDOW_1, PlaybackCommand.OPEN)
    claim_next(ControlCommandTarget.WINDOW_1, "player-stalled")
    ControlCommand.objects.filter(pk=queued.pk).update(
        consumer_heartbeat_at=timezone.now() - timedelta(minutes=1),
    )

    recovered = recover_abandoned(
        ControlCommandTarget.WINDOW_1,
        current_consumer_id="player-new",
        lease_timeout=timedelta(seconds=10),
    )

    queued.refresh_from_db()
    assert recovered == 1
    assert queued.status == ControlCommandStatus.FAILED


@pytest.mark.django_db
def test_recover_abandoned_never_reaps_current_process_identity() -> None:
    """当前消费者主动恢复队列时，不得把自己同一进程实例的记录置为失败。"""
    owner = CommandConsumerIdentity.current("player-current")
    queued = enqueue(ControlCommandTarget.WINDOW_1, PlaybackCommand.OPEN)
    claim_next(ControlCommandTarget.WINDOW_1, owner)
    ControlCommand.objects.filter(pk=queued.pk).update(
        consumer_heartbeat_at=timezone.now() - timedelta(minutes=1),
    )

    recovered = recover_abandoned(
        ControlCommandTarget.WINDOW_1,
        current_consumer_id=owner,
        lease_timeout=timedelta(seconds=10),
    )

    queued.refresh_from_db()
    assert recovered == 0
    assert queued.status == ControlCommandStatus.EXECUTING


@pytest.mark.django_db
def test_renew_consumer_lease_preserves_live_execution() -> None:
    """活动播放器续约后，即使旧心跳已过期也应继续持有执行记录。"""
    owner = CommandConsumerIdentity.current("player-live")
    queued = enqueue(ControlCommandTarget.WINDOW_1, PlaybackCommand.OPEN)
    claim_next(ControlCommandTarget.WINDOW_1, owner)
    expired_at = timezone.now() - timedelta(minutes=1)
    ControlCommand.objects.filter(pk=queued.pk).update(
        consumer_heartbeat_at=expired_at,
    )

    renewed = renew_consumer_lease(owner)
    recovered = recover_abandoned(
        ControlCommandTarget.WINDOW_1,
        current_consumer_id="player-new",
        lease_timeout=timedelta(seconds=10),
    )

    queued.refresh_from_db()
    assert renewed == 1
    assert recovered == 0
    assert queued.status == ControlCommandStatus.EXECUTING
    assert queued.consumer_heartbeat_at is not None
    assert queued.consumer_heartbeat_at > expired_at


@pytest.mark.django_db
def test_release_consumer_fails_own_unfinished_execution() -> None:
    """播放器正常关闭时应立即终结自己的在途记录，无需等待进程退出。"""
    owner = CommandConsumerIdentity.current("player-stopping")
    queued = enqueue(ControlCommandTarget.WINDOW_1, PlaybackCommand.OPEN)
    claim_next(ControlCommandTarget.WINDOW_1, owner)

    released = release_consumer(owner)

    queued.refresh_from_db()
    assert released == 1
    assert queued.status == ControlCommandStatus.FAILED
    assert queued.finished_at is not None
    assert "播放器已停止" in queued.error_message


@pytest.mark.django_db
def test_prune_removes_only_old_terminal_commands() -> None:
    """清理只能删除截止时间之前的终态记录。"""
    finished = enqueue(ControlCommandTarget.WINDOW_1, PlaybackCommand.NEXT)
    claim_next(ControlCommandTarget.WINDOW_1, "player-1")
    finish(
        finished.pk,
        "player-1",
        status=ControlCommandStatus.SUCCEEDED,
    )
    waiting = enqueue(ControlCommandTarget.WINDOW_1, PlaybackCommand.PREV)
    cutoff = timezone.now() + timedelta(seconds=1)

    pruned = prune(finished_before=cutoff)

    assert pruned == 1
    next_claim = claim_next(ControlCommandTarget.WINDOW_1, "player-1")
    assert next_claim is not None
    assert next_claim.pk == waiting.pk


def test_target_for_window_accepts_only_supported_window_ids() -> None:
    """窗口编号转换必须只生成四个受支持的消费通道。"""
    assert target_for_window(4) == ControlCommandTarget.WINDOW_4
    with pytest.raises(ValueError, match="窗口编号"):
        target_for_window(5)
