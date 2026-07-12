#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
播放会话命令投递：集中持久化队列策略与旧单槽镜像刷新。
@Project : SCP-cv
@File : playback_commands.py
@Author : Qintsg
@Date : 2026-07-12
'''
from __future__ import annotations

from scp_cv.apps.playback.models import (
    PlaybackCommand,
    PlaybackSession,
)
from scp_cv.services.command_queue import (
    CommandInput,
    cancel_pending,
    enqueue,
    enqueue_batch,
    enqueue_coalesced,
    target_for_window,
)
from scp_cv.services.playback_sessions import get_or_create_session


_COALESCED_COMMANDS = frozenset({
    PlaybackCommand.SET_VOLUME,
    PlaybackCommand.SET_MUTE,
    PlaybackCommand.SET_LOOP,
})


def enqueue_session_command(
    session: PlaybackSession,
    command: str,
    arguments: dict[str, object] | None = None,
    *,
    supersedes: bool = False,
) -> None:
    """按命令语义追加、合并或取代窗口队列，并刷新兼容镜像。"""
    target = target_for_window(session.window_id)
    if supersedes:
        enqueue_batch(
            target,
            [CommandInput(command=command, arguments=arguments or {})],
            cancel_pending=True,
        )
    elif command in _COALESCED_COMMANDS:
        enqueue_coalesced(target, command, arguments)
    else:
        enqueue(target, command, arguments)
    session.refresh_from_db(fields=["pending_command", "command_args"])


def enqueue_session_batch(
    session: PlaybackSession,
    commands: list[tuple[str, dict[str, object]]],
    *,
    supersedes: bool = False,
) -> None:
    """原子追加同一窗口的有序命令批次，并刷新兼容镜像。"""
    enqueue_batch(
        target_for_window(session.window_id),
        [CommandInput(command=command, arguments=args) for command, args in commands],
        cancel_pending=supersedes,
    )
    session.refresh_from_db(fields=["pending_command", "command_args"])


def clear_pending_command(window_id: int) -> PlaybackSession:
    """
    取消指定窗口尚未领取的命令，并返回已刷新兼容镜像的会话。
    :param window_id: 窗口编号（1-4）
    :return: 更新后的播放会话
    """
    session = get_or_create_session(window_id)
    cancel_pending(target_for_window(window_id))
    session.refresh_from_db(fields=["pending_command", "command_args"])
    return session


__all__ = [
    "clear_pending_command",
    "enqueue_session_batch",
    "enqueue_session_command",
]
