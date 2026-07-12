#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
播放服务持久化命令队列与事务批次测试。
@Project : SCP-cv
@File : test_playback_command_queue.py
@Author : Qintsg
@Date : 2026-07-11
'''
from __future__ import annotations

from pathlib import Path

import pytest

from scp_cv.apps.playback.models import (
    ControlCommand,
    ControlCommandStatus,
    ControlCommandTarget,
    MediaSource,
    PlaybackCommand,
)
from scp_cv.services.command_queue import claim_next, enqueue, finish
from scp_cv.services.playback import (
    apply_runtime_audio_policy,
    clear_pending_command,
    get_or_create_session,
    navigate_content,
    open_source,
    reset_ppt_playback,
    set_window_volume,
    update_playback_progress,
)
from scp_cv.services.ppt_playback_cache import PPT_PLAYBACK_METADATA_KEY


@pytest.mark.django_db
def test_window_volume_replaces_matching_pending_setting() -> None:
    """连续调整窗口音量时只保留一条尚未领取的音量指令。"""
    set_window_volume(1, 20)

    set_window_volume(1, 80)

    queued = list(
        ControlCommand.objects.filter(
            target=ControlCommandTarget.WINDOW_1,
            command=PlaybackCommand.SET_VOLUME,
            status=ControlCommandStatus.PENDING,
        )
    )
    assert len(queued) == 1
    assert queued[0].arguments == {"volume": 80}


@pytest.mark.django_db
def test_runtime_mute_policy_replaces_matching_pending_setting() -> None:
    """重复应用运行时静音策略不应为每个窗口积压相同设置。"""
    apply_runtime_audio_policy()

    apply_runtime_audio_policy()

    assert ControlCommand.objects.filter(
        target=ControlCommandTarget.WINDOW_1,
        command=PlaybackCommand.SET_MUTE,
        status=ControlCommandStatus.PENDING,
    ).count() == 1


@pytest.mark.django_db
def test_queue_failure_keeps_executing_command_in_legacy_mirror(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """业务保存失败窗口不得用新单槽值覆盖最早的执行中命令。"""
    session = get_or_create_session(1)
    executing = enqueue(
        ControlCommandTarget.WINDOW_1,
        PlaybackCommand.SET_VOLUME,
        {"volume": 20},
    )
    claim_next(ControlCommandTarget.WINDOW_1, "player-1")

    def fail_enqueue(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("queue unavailable")

    monkeypatch.setattr(
        "scp_cv.services.command_queue.enqueue_coalesced",
        fail_enqueue,
    )

    with pytest.raises(RuntimeError, match="queue unavailable"):
        set_window_volume(1, 80)

    executing.refresh_from_db()
    session.refresh_from_db()
    assert executing.status == ControlCommandStatus.EXECUTING
    assert session.pending_command == PlaybackCommand.SET_VOLUME
    assert session.command_args == {"volume": 20}


@pytest.mark.django_db
class TestNavigateCommandQueue:
    """测试需要严格保序的导航命令。"""

    def test_repeated_navigation_is_preserved_as_two_ordered_commands(
        self,
        media_source_ppt: MediaSource,
    ) -> None:
        """连续两次 next 不得被单槽覆盖，消费者应按顺序领取两次。"""
        open_source(1, media_source_ppt.pk)
        opened = claim_next(ControlCommandTarget.WINDOW_1, "test-player")
        assert opened is not None and opened.command == PlaybackCommand.OPEN
        assert finish(
            opened.pk,
            "test-player",
            status=ControlCommandStatus.SUCCEEDED,
        )

        navigate_content(1, PlaybackCommand.NEXT)
        navigate_content(1, PlaybackCommand.NEXT)

        first = claim_next(ControlCommandTarget.WINDOW_1, "test-player")
        assert first is not None and first.command == PlaybackCommand.NEXT
        assert finish(
            first.pk,
            "test-player",
            status=ControlCommandStatus.SUCCEEDED,
        )
        second = claim_next(ControlCommandTarget.WINDOW_1, "test-player")
        assert second is not None and second.command == PlaybackCommand.NEXT


@pytest.mark.django_db
class TestPptResetOperations:
    """测试 PowerPoint-only PPT 重置。"""

    def test_reset_ppt_playback_keeps_current_slide(self, media_source_ppt: MediaSource) -> None:
        """重置 PPT 放映应收集当前 PPT 窗口并保留页码。"""
        open_source(1, media_source_ppt.pk)
        update_playback_progress(1, current_slide=5, total_slides=10)
        clear_pending_command(1)

        reset_ppt_playback()
        session = get_or_create_session(1)

        assert session.pending_command == PlaybackCommand.CLOSE
        closing = claim_next(ControlCommandTarget.WINDOW_1, "test-player")
        assert closing is not None and closing.command == PlaybackCommand.CLOSE
        assert finish(
            closing.pk,
            "test-player",
            status=ControlCommandStatus.SUCCEEDED,
        )
        reopening = claim_next(ControlCommandTarget.WINDOW_1, "test-player")
        assert reopening is not None and reopening.command == PlaybackCommand.OPEN
        assert reopening.arguments["source_id"] == media_source_ppt.pk
        assert reopening.arguments["target_slide"] == 5

    def test_reset_ppt_playback_broadcasts_to_each_active_ppt_window(
        self,
        media_source_ppt: MediaSource,
    ) -> None:
        """多播放器进程下，每个活跃 PPT 窗口都应收到 close/open 批次。"""
        open_source(1, media_source_ppt.pk)
        open_source(2, media_source_ppt.pk)
        clear_pending_command(1)
        clear_pending_command(2)

        reset_ppt_playback()
        session1 = get_or_create_session(1)
        session2 = get_or_create_session(2)

        assert session1.pending_command == PlaybackCommand.CLOSE
        assert session2.pending_command == PlaybackCommand.CLOSE
        for target in (
            ControlCommandTarget.WINDOW_1,
            ControlCommandTarget.WINDOW_2,
        ):
            closing = claim_next(target, "test-player")
            assert closing is not None and closing.command == PlaybackCommand.CLOSE
            assert finish(
                closing.pk,
                "test-player",
                status=ControlCommandStatus.SUCCEEDED,
            )
            reopening = claim_next(target, "test-player")
            assert reopening is not None and reopening.command == PlaybackCommand.OPEN
            assert reopening.arguments["source_id"] == media_source_ppt.pk

    def test_reset_ppt_playback_uses_ready_playback_cache(
        self,
        media_source_ppt: MediaSource,
        tmp_path: Path,
    ) -> None:
        """重置 PPT 放映时重启参数应继续使用放映缓存 URI。"""
        cached_file = tmp_path / "cached.ppsx"
        cached_file.write_bytes(b"cached-show")
        media_source_ppt.metadata = {
            PPT_PLAYBACK_METADATA_KEY: {
                "status": "ready",
                "path": str(cached_file),
            },
        }
        media_source_ppt.save(update_fields=["metadata"])
        open_source(1, media_source_ppt.pk)
        update_playback_progress(1, current_slide=2, total_slides=5)
        clear_pending_command(1)

        reset_ppt_playback()
        closing = claim_next(ControlCommandTarget.WINDOW_1, "test-player")
        assert closing is not None
        assert finish(
            closing.pk,
            "test-player",
            status=ControlCommandStatus.SUCCEEDED,
        )
        reopening = claim_next(ControlCommandTarget.WINDOW_1, "test-player")
        assert reopening is not None
        restart_args = reopening.arguments

        assert restart_args["uri"] == str(cached_file)
        assert restart_args["original_uri"] == media_source_ppt.uri
