"""背景音频持久命令队列及租约操作。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from scp_cv.apps.playback.models import BackgroundAudioCommand, BackgroundAudioCommandRecord, BackgroundAudioState

_COALESCED = {
    BackgroundAudioCommand.SEEK,
    BackgroundAudioCommand.SET_LOOP,
    BackgroundAudioCommand.SET_VOLUME,
    BackgroundAudioCommand.SET_MUTE,
}


def _lease_seconds() -> float:
    """读取背景音频租约时长。"""
    return max(1.0, float(getattr(settings, "PLAYBACK_COMMAND_LEASE_SECONDS", 30.0)))


@dataclass(frozen=True)
class ClaimedBackgroundAudioCommand:
    """背景音频可执行命令快照。"""

    id: int
    command: str
    command_args: dict[str, object]
    consumer_id: str


def _project(state: BackgroundAudioState) -> None:
    """将最早未完成记录投影到兼容字段。"""
    record = BackgroundAudioCommandRecord.objects.filter(state_id=state.pk).order_by("id").first()
    if record is None:
        state.pending_command = BackgroundAudioCommand.NONE
        state.command_args = {}
    else:
        state.pending_command = record.command
        state.command_args = dict(record.command_args or {})
    state.save(update_fields=["pending_command", "command_args", "updated_at"])


def enqueue_background_audio_command(
    state: BackgroundAudioState,
    command: str,
    command_args: dict[str, object] | None = None,
) -> BackgroundAudioCommandRecord:
    """按规则入队并更新兼容投影。"""
    args = dict(command_args or {})
    with transaction.atomic():
        if command in _COALESCED:
            BackgroundAudioCommandRecord.objects.filter(
                state_id=state.pk,
                status="pending",
                command=command,
            ).delete()
        record = BackgroundAudioCommandRecord.objects.create(state=state, command=command, command_args=args)
        _project(state)
    return record


def claim_next_background_audio_command(
    consumer_id: str,
) -> ClaimedBackgroundAudioCommand | None:
    """领取最早命令；过期 processing 会被恢复。"""
    now = timezone.now()
    deadline = now - timedelta(seconds=_lease_seconds())
    with transaction.atomic():
        state = BackgroundAudioState.objects.select_for_update().filter(pk=1).first()
        if state is None:
            return None
        active = (
            BackgroundAudioCommandRecord.objects.select_for_update()
            .filter(state_id=state.pk, status="processing")
            .order_by("id")
            .first()
        )
        if active is not None:
            if active.claimed_by == consumer_id:
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
            BackgroundAudioCommandRecord.objects.select_for_update()
            .filter(state_id=state.pk, status="pending")
            .order_by("id")
            .first()
        )
        if record is None:
            _project(state)
            return None
        record.status = "processing"
        record.claimed_by = consumer_id
        record.claimed_at = now
        record.attempt_count += 1
        record.save(update_fields=["status", "claimed_by", "claimed_at", "attempt_count"])
        _project(state)
        return ClaimedBackgroundAudioCommand(record.pk, record.command, dict(record.command_args or {}), consumer_id)


def acknowledge_background_audio_command(command_id: int, consumer_id: str | None = None) -> bool:
    """确认已执行命令；身份不匹配时不删除。"""
    with transaction.atomic():
        record = BackgroundAudioCommandRecord.objects.select_for_update().filter(pk=command_id).first()
        if record is None:
            return False
        if consumer_id is not None and record.claimed_by != consumer_id:
            return False
        state = BackgroundAudioState.objects.select_for_update().get(pk=record.state_id)
        record.delete()
        _project(state)
    return True


def release_background_audio_command_lease(consumer_id: str) -> int:
    """释放消费者持有的背景音频租约。"""
    return BackgroundAudioCommandRecord.objects.filter(
        status="processing", claimed_by=consumer_id,
    ).update(status="pending", claimed_by="", claimed_at=None)


def clear_background_audio_command_queue(state: BackgroundAudioState | None = None) -> BackgroundAudioState:
    """清空队列并重置兼容字段。"""
    state = state or BackgroundAudioState.get_instance()
    with transaction.atomic():
        BackgroundAudioCommandRecord.objects.filter(state_id=state.pk).delete()
        state.pending_command = BackgroundAudioCommand.NONE
        state.command_args = {}
        state.save(update_fields=["pending_command", "command_args", "updated_at"])
    return state


__all__ = [
    "ClaimedBackgroundAudioCommand",
    "acknowledge_background_audio_command",
    "claim_next_background_audio_command",
    "clear_background_audio_command_queue",
    "enqueue_background_audio_command",
    "release_background_audio_command_lease",
]
