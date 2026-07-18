"""可靠播放指令队列：调用方只负责入队，播放器按顺序领取并确认。"""

from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction

from scp_cv.apps.playback.models import (
    PlaybackCommand,
    PlaybackCommandRecord,
    PlaybackSession,
)


_COALESCED_COMMANDS = {
    PlaybackCommand.SEEK,
    PlaybackCommand.SET_LOOP,
    PlaybackCommand.SET_VOLUME,
    PlaybackCommand.SET_MUTE,
}

_SUPERSEDING_COMMANDS = {
    PlaybackCommand.OPEN,
    PlaybackCommand.CLOSE,
    PlaybackCommand.RESET_PPT,
}


@dataclass(frozen=True)
class ClaimedPlaybackCommand:
    """播放器可执行的不可变指令快照。"""

    id: int
    window_id: int
    command: str
    command_args: dict[str, object]


def enqueue_playback_command(
    session: PlaybackSession,
    command: str,
    command_args: dict[str, object] | None = None,
    *,
    update_fields: list[str] | None = None,
) -> PlaybackCommandRecord:
    """原子更新会话可视状态并把一条指令加入持久队列。"""
    args = dict(command_args or {})
    with transaction.atomic():
        if command in _SUPERSEDING_COMMANDS:
            # 新内容或终止命令定义了窗口的新边界；此前尚未执行的控制命令
            # 都属于旧画面，继续交付会造成切源后翻页/播放错位。
            PlaybackCommandRecord.objects.filter(session_id=session.pk).delete()
        elif command in _COALESCED_COMMANDS:
            PlaybackCommandRecord.objects.filter(
                session_id=session.pk,
                command=command,
            ).delete()
        record = PlaybackCommandRecord.objects.create(
            session=session,
            command=command,
            command_args=args,
        )
        session.pending_command = command
        session.command_args = args
        if update_fields is None:
            session.save()
        else:
            fields = list(dict.fromkeys([*update_fields, "pending_command", "command_args", "last_updated_at"]))
            session.save(update_fields=fields)
    return record


def claim_next_playback_command(window_id: int) -> ClaimedPlaybackCommand | None:
    """读取窗口最早的待执行指令；确认前不会从队列移除。"""
    record = (
        PlaybackCommandRecord.objects.filter(session__window_id=window_id)
        .select_related("session")
        .order_by("id")
        .first()
    )
    if record is None:
        return None
    return ClaimedPlaybackCommand(
        id=record.pk,
        window_id=record.session.window_id,
        command=record.command,
        command_args=dict(record.command_args or {}),
    )


def acknowledge_playback_command(command_id: int) -> None:
    """确认并移除已发往 Qt 主线程的指令，同时投影下一条到兼容字段。"""
    with transaction.atomic():
        record = PlaybackCommandRecord.objects.select_for_update().filter(pk=command_id).first()
        if record is None:
            return
        session_id = record.session_id
        record.delete()
        next_record = PlaybackCommandRecord.objects.filter(session_id=session_id).order_by("id").first()
        if next_record is None:
            PlaybackSession.objects.filter(pk=session_id).update(
                pending_command=PlaybackCommand.NONE,
                command_args={},
            )
        else:
            PlaybackSession.objects.filter(pk=session_id).update(
                pending_command=next_record.command,
                command_args=dict(next_record.command_args or {}),
            )


def clear_playback_command_queue(session: PlaybackSession) -> PlaybackSession:
    """清空窗口全部未消费指令并重置兼容字段。"""
    with transaction.atomic():
        PlaybackCommandRecord.objects.filter(session_id=session.pk).delete()
        session.pending_command = PlaybackCommand.NONE
        session.command_args = {}
        session.save(update_fields=["pending_command", "command_args", "last_updated_at"])
    return session
