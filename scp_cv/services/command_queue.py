#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
持久化控制命令队列：集中处理入队、领取、确认和旧字段镜像。
@Project : SCP-cv
@File : services/command_queue.py
@Author : Qintsg
@Date : 2026-07-11
'''
from __future__ import annotations

import uuid
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from django.db import IntegrityError, transaction
from django.utils import timezone

from scp_cv.apps.playback.models import (
    BackgroundAudioState,
    ControlCommand,
    ControlCommandStatus,
    ControlCommandTarget,
    PlaybackSession,
)
from scp_cv.services.command_status import record_enqueued_commands
from scp_cv.services.command_consumer import (
    CommandConsumerIdentity,
    command_owner_process_is_alive as _command_owner_process_is_alive,
    normalize_consumer_id as _normalize_consumer_id,
    normalize_consumer_identity as _normalize_consumer_identity,
)


_OPEN_STATUSES = (ControlCommandStatus.PENDING, ControlCommandStatus.EXECUTING)
_TERMINAL_STATUSES = (
    ControlCommandStatus.SUCCEEDED,
    ControlCommandStatus.FAILED,
    ControlCommandStatus.CANCELLED,
)
_SUPERSEDED_MESSAGE = "由后续控制批次取代"
_CONSUMER_LEASE_TIMEOUT = timedelta(seconds=30)


@dataclass(frozen=True, slots=True)
class CommandInput:
    """待入队指令的值对象。"""

    command: str
    arguments: Mapping[str, Any] = field(default_factory=dict)


def enqueue(
    target: ControlCommandTarget | str,
    command: str,
    arguments: Mapping[str, Any] | None = None,
) -> ControlCommand:
    """把一条控制指令追加到目标通道，返回持久化记录。"""
    return enqueue_batch(
        target,
        [CommandInput(command=command, arguments=arguments or {})],
    )[0]


def enqueue_coalesced(
    target: ControlCommandTarget | str,
    command: str,
    arguments: Mapping[str, Any] | None = None,
) -> ControlCommand:
    """合并同一目标尚未领取的同类指令；执行中指令永不被改写。"""
    normalized_target = _normalize_target(target)
    normalized_command = _normalize_command(command)
    normalized_arguments = dict(arguments or {})
    with transaction.atomic():
        queued = (
            ControlCommand.objects.select_for_update()
            .filter(
                target=normalized_target,
                command=normalized_command,
                status=ControlCommandStatus.PENDING,
            )
            .order_by("id")
            .first()
        )
        if queued is None:
            queued = ControlCommand.objects.create(
                target=normalized_target,
                command=normalized_command,
                arguments=normalized_arguments,
            )
        else:
            queued.arguments = normalized_arguments
            queued.save(update_fields=["arguments"])
        _sync_legacy_mirror(normalized_target)
    record_enqueued_commands([queued])
    return queued


def enqueue_batch(
    target: ControlCommandTarget | str,
    commands: Iterable[CommandInput],
    *,
    cancel_pending: bool = False,
) -> list[ControlCommand]:
    """在一个事务中追加有序批次，可先取代目标的旧未完成指令。"""
    normalized_target = _normalize_target(target)
    normalized_commands = [
        CommandInput(
            command=_normalize_command(command.command),
            arguments=dict(command.arguments),
        )
        for command in commands
    ]
    if not normalized_commands:
        raise ValueError("commands 不能为空")

    with transaction.atomic():
        now = timezone.now()
        if cancel_pending:
            ControlCommand.objects.filter(
                target=normalized_target,
                status=ControlCommandStatus.PENDING,
            ).update(
                status=ControlCommandStatus.CANCELLED,
                error_message=_SUPERSEDED_MESSAGE,
                finished_at=now,
            )
            ControlCommand.objects.filter(
                target=normalized_target,
                status=ControlCommandStatus.EXECUTING,
            ).update(cancel_requested=True)

        batch_id = uuid.uuid4()
        queued = [
            ControlCommand.objects.create(
                target=normalized_target,
                command=command.command,
                arguments=dict(command.arguments),
                batch_id=batch_id,
            )
            for command in normalized_commands
        ]
        _sync_legacy_mirror(normalized_target)
    record_enqueued_commands(queued)
    return queued


def cancel_pending(
    target: ControlCommandTarget | str,
    *,
    error_message: str = "由兼容清理入口取消",
) -> int:
    """取消目标中尚未领取的指令，并刷新旧单槽镜像。"""
    normalized_target = _normalize_target(target)
    with transaction.atomic():
        cancelled = ControlCommand.objects.filter(
            target=normalized_target,
            status=ControlCommandStatus.PENDING,
        ).update(
            status=ControlCommandStatus.CANCELLED,
            error_message=error_message,
            finished_at=timezone.now(),
        )
        _sync_legacy_mirror(normalized_target)
    return cancelled


def claim_next(
    target: ControlCommandTarget | str,
    consumer_id: CommandConsumerIdentity | str,
) -> ControlCommand | None:
    """以条件更新原子领取目标通道中最早的待执行指令。"""
    normalized_target = _normalize_target(target)
    consumer = _normalize_consumer_identity(consumer_id)
    while True:
        if ControlCommand.objects.filter(
            target=normalized_target,
            status=ControlCommandStatus.EXECUTING,
        ).exists():
            return None
        candidate_id = (
            ControlCommand.objects.filter(
                target=normalized_target,
                status=ControlCommandStatus.PENDING,
            )
            .order_by("id")
            .values_list("id", flat=True)
            .first()
        )
        if candidate_id is None:
            return None
        try:
            with transaction.atomic():
                claimed = ControlCommand.objects.filter(
                    pk=candidate_id,
                    status=ControlCommandStatus.PENDING,
                ).update(
                    status=ControlCommandStatus.EXECUTING,
                    consumer_id=consumer.consumer_id,
                    consumer_pid=consumer.process_id,
                    consumer_process_started_at=consumer.process_started_at,
                    consumer_heartbeat_at=timezone.now(),
                    started_at=timezone.now(),
                )
        except IntegrityError:
            # 数据库部分唯一约束是并发领取时的最终裁决者。
            return None
        if claimed:
            return ControlCommand.objects.get(pk=candidate_id)


def finish(
    command_id: int,
    consumer_id: str,
    *,
    status: ControlCommandStatus | str,
    error_message: str = "",
) -> bool:
    """仅允许实际领取者终结仍在执行中的指令。"""
    normalized_consumer = _normalize_consumer_id(consumer_id)
    normalized_status = str(status)
    if normalized_status not in _TERMINAL_STATUSES:
        raise ValueError("完成状态必须是 succeeded、failed 或 cancelled")

    with transaction.atomic():
        queued = ControlCommand.objects.select_for_update().filter(
            pk=command_id,
            status=ControlCommandStatus.EXECUTING,
            consumer_id=normalized_consumer,
        ).first()
        if queued is None:
            return False
        if queued.cancel_requested:
            queued.status = ControlCommandStatus.CANCELLED
            queued.error_message = _SUPERSEDED_MESSAGE
        else:
            queued.status = normalized_status
            queued.error_message = error_message
        queued.finished_at = timezone.now()
        queued.save(update_fields=["status", "error_message", "finished_at"])
        _sync_legacy_mirror(queued.target)
    return True


def is_cancel_requested(command_id: int, consumer_id: str) -> bool:
    """查询实际领取者的执行中指令是否已被后续批次请求取消。"""
    normalized_consumer = _normalize_consumer_id(consumer_id)
    return ControlCommand.objects.filter(
        pk=command_id,
        status=ControlCommandStatus.EXECUTING,
        consumer_id=normalized_consumer,
        cancel_requested=True,
    ).exists()


def finish_cancelled(command_id: int, consumer_id: str) -> bool:
    """在调用方完成资源释放后，把自己领取的指令终结为已取消。"""
    return finish(
        command_id,
        consumer_id,
        status=ControlCommandStatus.CANCELLED,
        error_message=_SUPERSEDED_MESSAGE,
    )


def renew_consumer_lease(
    consumer: CommandConsumerIdentity | str,
) -> int:
    """续约当前进程实际领取的执行记录，返回续约数量。"""
    identity = _normalize_consumer_identity(consumer)
    return ControlCommand.objects.filter(
        status=ControlCommandStatus.EXECUTING,
        consumer_id=identity.consumer_id,
        consumer_pid=identity.process_id,
        consumer_process_started_at=identity.process_started_at,
    ).update(consumer_heartbeat_at=timezone.now())


def release_consumer(
    consumer: CommandConsumerIdentity | str,
    *,
    error_message: str = "播放器已停止，未完成指令不会重放",
) -> int:
    """播放器关闭时终结由该进程实例领取但尚未完成的记录。"""
    identity = _normalize_consumer_identity(consumer)
    with transaction.atomic():
        executing = ControlCommand.objects.select_for_update().filter(
            status=ControlCommandStatus.EXECUTING,
            consumer_id=identity.consumer_id,
            consumer_pid=identity.process_id,
            consumer_process_started_at=identity.process_started_at,
        )
        affected_targets = list(
            executing.order_by().values_list("target", flat=True).distinct()
        )
        released = executing.update(
            status=ControlCommandStatus.FAILED,
            error_message=error_message,
            finished_at=timezone.now(),
        )
        for target in affected_targets:
            _sync_legacy_mirror(target)
    return released


def recover_abandoned(
    target: ControlCommandTarget | str,
    current_consumer_id: CommandConsumerIdentity | str,
    *,
    error_message: str = "播放器重启，旧执行记录已终止且不会重放",
    lease_timeout: timedelta = _CONSUMER_LEASE_TIMEOUT,
) -> int:
    """终结目标中属于旧消费者的执行记录，返回恢复数量。"""
    normalized_target = _normalize_target(target)
    current_consumer = _normalize_consumer_identity(current_consumer_id)
    if lease_timeout.total_seconds() <= 0:
        raise ValueError("lease_timeout 必须大于 0 秒")
    now = timezone.now()
    with transaction.atomic():
        candidates = list(
            ControlCommand.objects.filter(
                target=normalized_target,
                status=ControlCommandStatus.EXECUTING,
            )
            .order_by("id")
        )
        recovered = 0
        for queued in candidates:
            if (
                queued.consumer_id == current_consumer.consumer_id
                and queued.consumer_pid == current_consumer.process_id
                and queued.consumer_process_started_at
                == current_consumer.process_started_at
            ):
                continue
            if _command_owner_process_is_alive(
                queued,
                now=now,
                lease_timeout=lease_timeout,
            ):
                continue
            recovered += ControlCommand.objects.filter(
                pk=queued.pk,
                status=ControlCommandStatus.EXECUTING,
                consumer_id=queued.consumer_id,
                consumer_pid=queued.consumer_pid,
                consumer_process_started_at=queued.consumer_process_started_at,
                consumer_heartbeat_at=queued.consumer_heartbeat_at,
            ).update(
                status=ControlCommandStatus.FAILED,
                error_message=error_message,
                finished_at=now,
            )
        if recovered:
            _sync_legacy_mirror(normalized_target)
    return recovered


def prune(*, finished_before: datetime | None = None) -> int:
    """删除指定截止时间之前的终态指令，默认保留七天。"""
    cutoff = finished_before or (timezone.now() - timedelta(days=7))
    deleted, _ = ControlCommand.objects.filter(
        status__in=_TERMINAL_STATUSES,
        finished_at__lt=cutoff,
    ).delete()
    return deleted


def target_for_window(window_id: int) -> ControlCommandTarget:
    """把窗口编号转换为队列目标，并拒绝 1-4 之外的值。"""
    try:
        return ControlCommandTarget(f"window:{int(window_id)}")
    except (TypeError, ValueError) as exc:
        raise ValueError(f"窗口编号必须是 1-4，收到：{window_id}") from exc


def _normalize_target(target: ControlCommandTarget | str) -> str:
    """校验并返回可持久化的控制目标。"""
    normalized = str(target)
    if normalized not in ControlCommandTarget.values:
        raise ValueError(f"不支持的控制目标：{normalized}")
    return normalized


def _normalize_command(command: str) -> str:
    """校验并返回可持久化的控制指令。"""
    normalized = str(command).strip()
    if not normalized:
        raise ValueError("command 不能为空")
    return normalized


def _sync_legacy_mirror(target: str) -> None:
    """用队列中最早的未完成指令刷新旧单槽字段。"""
    queued = (
        ControlCommand.objects.filter(target=target, status__in=_OPEN_STATUSES)
        .order_by("id")
        .first()
    )
    command = queued.command if queued else ""
    arguments = queued.arguments if queued else {}

    if target == ControlCommandTarget.BACKGROUND_AUDIO:
        BackgroundAudioState.objects.filter(pk=1).update(
            pending_command=command,
            command_args=arguments,
        )
        return

    window_id = int(target.removeprefix("window:"))
    PlaybackSession.objects.filter(window_id=window_id).update(
        pending_command=command,
        command_args=arguments,
    )


__all__ = [
    "CommandConsumerIdentity",
    "CommandInput",
    "cancel_pending",
    "claim_next",
    "enqueue",
    "enqueue_batch",
    "enqueue_coalesced",
    "finish",
    "finish_cancelled",
    "is_cancel_requested",
    "prune",
    "recover_abandoned",
    "release_consumer",
    "renew_consumer_lease",
    "target_for_window",
]
