#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
命令消费者身份与进程存活判定。
@Project : SCP-cv
@File : services/command_consumer.py
@Author : Qintsg
@Date : 2026-07-11
'''
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta

from scp_cv.apps.playback.models import ControlCommand


_PROCESS_CREATE_TIME_TOLERANCE_SECONDS = 0.01


@dataclass(frozen=True, slots=True)
class CommandConsumerIdentity:
    """用 PID 与进程创建时间防止消费者 ID 和 Windows PID 复用误判。"""

    consumer_id: str
    process_id: int
    process_started_at: float

    @classmethod
    def current(cls, consumer_id: str) -> CommandConsumerIdentity:
        """为当前播放器进程创建可跨进程校验的消费者身份。"""
        import psutil

        process_id = os.getpid()
        return cls(
            consumer_id=normalize_consumer_id(consumer_id),
            process_id=process_id,
            process_started_at=float(psutil.Process(process_id).create_time()),
        )


def normalize_consumer_id(consumer_id: str) -> str:
    """校验消费者编号，防止生成无法确认归属的执行记录。"""
    normalized = consumer_id.strip()
    if not normalized:
        raise ValueError("consumer_id 不能为空")
    return normalized


def normalize_consumer_identity(
    consumer: CommandConsumerIdentity | str,
) -> CommandConsumerIdentity:
    """校验显式身份，字符串调用方则绑定到当前进程实例。"""
    if isinstance(consumer, str):
        return CommandConsumerIdentity.current(consumer)
    consumer_id = normalize_consumer_id(consumer.consumer_id)
    if consumer.process_id <= 0:
        raise ValueError("consumer process_id 必须是正整数")
    if consumer.process_started_at <= 0:
        raise ValueError("consumer process_started_at 必须大于 0")
    return CommandConsumerIdentity(
        consumer_id=consumer_id,
        process_id=int(consumer.process_id),
        process_started_at=float(consumer.process_started_at),
    )


def command_owner_process_is_alive(
    queued: ControlCommand,
    *,
    now: datetime,
    lease_timeout: timedelta,
) -> bool:
    """仅在进程身份匹配且消费者租约新鲜时确认原领取者仍存活。"""
    import psutil

    process_id = queued.consumer_pid
    expected_started_at = queued.consumer_process_started_at
    heartbeat_at = queued.consumer_heartbeat_at
    if (
        process_id is None
        or expected_started_at is None
        or heartbeat_at is None
        or heartbeat_at < now - lease_timeout
    ):
        return False
    try:
        process = psutil.Process(process_id)
        if not process.is_running() or process.status() == psutil.STATUS_ZOMBIE:
            return False
        actual_started_at = float(process.create_time())
    except psutil.NoSuchProcess:
        return False
    except psutil.AccessDenied:
        # 无权读取时不能证明是遗留记录；保留执行状态比误杀更安全。
        return True
    except (OSError, ValueError, psutil.Error):
        return False
    return (
        abs(actual_started_at - float(expected_started_at))
        <= _PROCESS_CREATE_TIME_TOLERANCE_SECONDS
    )


__all__ = [
    "CommandConsumerIdentity",
    "command_owner_process_is_alive",
    "normalize_consumer_id",
    "normalize_consumer_identity",
]
