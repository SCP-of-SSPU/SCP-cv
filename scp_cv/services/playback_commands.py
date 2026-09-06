"""可靠播放指令队列：带消费者租约，执行完成后才确认。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from scp_cv.apps.playback.models import PlaybackCommand, PlaybackCommandRecord, PlaybackSession


_COALESCED_COMMANDS = {
    PlaybackCommand.SEEK,
    PlaybackCommand.SET_LOOP,
    PlaybackCommand.SET_VOLUME,
    PlaybackCommand.SET_MUTE,
}
_SUPERSEDING_COMMANDS = {PlaybackCommand.OPEN, PlaybackCommand.CLOSE, PlaybackCommand.RESET_PPT}
_DEFAULT_CONSUMER = "legacy"


def _lease_seconds() -> float:
    """读取命令租约时长。"""
    return max(1.0, float(getattr(settings, "PLAYBACK_COMMAND_LEASE_SECONDS", 30.0)))


@dataclass(frozen=True)
class ClaimedPlaybackCommand:
    """播放器可执行的不可变指令快照。"""

    id: int
    window_id: int
    command: str
    command_args: dict[str, object]
    consumer_id: str = ""


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
            # 不能删除已领取的指令，否则会造成执行中的资源操作失去记录。
            PlaybackCommandRecord.objects.filter(session_id=session.pk, status="pending").delete()
        elif command in _COALESCED_COMMANDS:
            PlaybackCommandRecord.objects.filter(
                session_id=session.pk,
                status="pending",
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


def claim_next_playback_command(
    window_id: int,
    consumer_id: str | None = None,
) -> ClaimedPlaybackCommand | None:
    """按顺序领取一条指令；租约过期后可被其它消费者恢复。"""
    consumer = consumer_id or _DEFAULT_CONSUMER
    now = timezone.now()
    deadline = now - timedelta(seconds=_lease_seconds())
    with transaction.atomic():
        session = PlaybackSession.objects.select_for_update().filter(window_id=window_id).first()
        if session is None:
            return None
        # 仅恢复本窗口最早的过期 processing，避免越过它领取后续命令。
        active = (
            PlaybackCommandRecord.objects.select_for_update()
            .filter(session_id=session.pk, status="processing")
            .order_by("id")
            .first()
        )
        if active is not None:
            if active.claimed_by == consumer:
                active.claimed_at = now
                active.save(update_fields=["claimed_at"])
                return None
            if active.claimed_at is not None and active.claimed_at > deadline:
                return None
            active.status = "pending"
            active.claimed_by = ""
            active.claimed_at = None
            active.last_error = active.last_error or "消费者租约过期，已恢复"
            active.save(update_fields=["status", "claimed_by", "claimed_at", "last_error"])
        record = (
            PlaybackCommandRecord.objects.select_for_update()
            .filter(session_id=session.pk, status="pending")
            .order_by("id")
            .first()
        )
        if record is None:
            return None
        record.status = "processing"
        record.claimed_by = consumer
        record.claimed_at = now
        record.attempt_count += 1
        record.save(update_fields=["status", "claimed_by", "claimed_at", "attempt_count"])
        return ClaimedPlaybackCommand(
            id=record.pk,
            window_id=window_id,
            command=record.command,
            command_args=dict(record.command_args or {}),
            consumer_id=consumer,
        )


def acknowledge_playback_command(command_id: int, consumer_id: str | None = None) -> bool:
    """确认执行完成的指令；消费者不匹配时保留记录并返回 False。"""
    with transaction.atomic():
        record = PlaybackCommandRecord.objects.select_for_update().filter(pk=command_id).first()
        if record is None:
            return False
        if consumer_id is not None and record.claimed_by != consumer_id:
            return False
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
    return True


def release_playback_command_lease(
    consumer_id: str,
    window_ids: tuple[int, ...] | list[int] | None = None,
) -> int:
    """释放指定消费者持有的 processing 租约，使指令可恢复。"""
    query = PlaybackCommandRecord.objects.filter(status="processing", claimed_by=consumer_id)
    if window_ids:
        query = query.filter(session__window_id__in=window_ids)
    return query.update(status="pending", claimed_by="", claimed_at=None)


def clear_playback_command_queue(
    session: PlaybackSession,
    *,
    preserve_processing: bool = False,
) -> PlaybackSession:
    """清空窗口命令；运行时可保留已领取记录，避免伪装为从未执行。"""
    with transaction.atomic():
        records = PlaybackCommandRecord.objects.filter(session_id=session.pk)
        if preserve_processing:
            records.filter(status="pending").delete()
        else:
            records.delete()
        next_record = PlaybackCommandRecord.objects.filter(session_id=session.pk).order_by("id").first()
        session.pending_command = next_record.command if next_record is not None else PlaybackCommand.NONE
        session.command_args = dict(next_record.command_args or {}) if next_record is not None else {}
        session.save(update_fields=["pending_command", "command_args", "last_updated_at"])
    return session


__all__ = [
    "ClaimedPlaybackCommand",
    "acknowledge_playback_command",
    "claim_next_playback_command",
    "clear_playback_command_queue",
    "enqueue_playback_command",
    "release_playback_command_lease",
]
