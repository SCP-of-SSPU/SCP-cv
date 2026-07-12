#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
控制命令状态投影：为受理回执与实时状态流提供稳定的普通数据合同。
@Project : SCP-cv
@File : services/command_status.py
@Author : Qintsg
@Date : 2026-07-11
'''
from __future__ import annotations

from collections.abc import Generator, Iterable
from contextlib import contextmanager
from contextvars import ContextVar

from scp_cv.apps.playback.models import ControlCommand, ControlCommandStatus


_RECENT_COMMAND_LIMIT = 100
_captured_commands: ContextVar[list[ControlCommand] | None] = ContextVar(
    "captured_control_commands",
    default=None,
)


@contextmanager
def capture_enqueued_commands() -> Generator[list[ControlCommand], None, None]:
    """捕获当前调用上下文中实际入队的命令，隔离并发请求。"""
    commands: list[ControlCommand] = []
    token = _captured_commands.set(commands)
    try:
        yield commands
    finally:
        _captured_commands.reset(token)


def record_enqueued_commands(commands: Iterable[ControlCommand]) -> None:
    """由命令队列登记本调用上下文中已持久化的命令。"""
    capture = _captured_commands.get()
    if capture is not None:
        capture.extend(commands)


def control_command_payload(command: ControlCommand) -> dict[str, object]:
    """把 ControlCommand 投影为 REST、SSE 与 gRPC 共用的普通数据。"""
    return {
        "id": int(command.pk),
        "target": command.target,
        "command": command.command,
        "status": command.status,
        "error_message": command.error_message,
    }


def control_command_payloads(
    commands: Iterable[ControlCommand],
) -> list[dict[str, object]]:
    """按首次入队顺序刷新并序列化唯一命令，避免返回同请求内的过期状态。"""
    captured_by_id: dict[int, ControlCommand] = {}
    for command in commands:
        command_id = int(command.pk)
        captured_by_id.setdefault(command_id, command)
    persisted_by_id = ControlCommand.objects.in_bulk(captured_by_id)
    return [
        control_command_payload(persisted_by_id.get(command_id, command))
        for command_id, command in captured_by_id.items()
    ]


def get_recent_control_command_payloads(
    *,
    limit: int = _RECENT_COMMAND_LIMIT,
) -> list[dict[str, object]]:
    """返回全部未完成命令及最近完成命令，确保旧 ID 的新终态不会被新队列挤出。"""
    normalized_limit = max(1, int(limit))
    active = list(ControlCommand.objects.filter(
        status__in=(ControlCommandStatus.PENDING, ControlCommandStatus.EXECUTING),
    ))
    recent_terminal = list(
        ControlCommand.objects.filter(status__in=(
            ControlCommandStatus.SUCCEEDED,
            ControlCommandStatus.FAILED,
            ControlCommandStatus.CANCELLED,
        ))
        .order_by("-finished_at", "-id")[:normalized_limit]
    )
    commands_by_id = {
        int(command.pk): command
        for command in (*active, *recent_terminal)
    }
    return [
        control_command_payload(commands_by_id[command_id])
        for command_id in sorted(commands_by_id)
    ]


__all__ = [
    "capture_enqueued_commands",
    "control_command_payload",
    "control_command_payloads",
    "get_recent_control_command_payloads",
    "record_enqueued_commands",
]
