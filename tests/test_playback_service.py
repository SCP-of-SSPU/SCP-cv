#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
播放会话管理服务 (playback.py) 单元测试。
覆盖会话获取、快照生成、源打开/关闭、播放控制、导航、进度上报等功能。
@Project : SCP-cv
@File : test_playback_service.py
@Author : Qintsg
@Date : 2026-04-14
'''
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from scp_cv.apps.playback.models import (
    BigScreenMode,
    MediaSource,
    PlaybackCommand,
    PlaybackCommandRecord,
    PlaybackSession,
    PlaybackState,
    RuntimeState,
)
from scp_cv.services.playback import (
    PlaybackError,
    clear_pending_command,
    control_playback,
    get_or_create_session,
    get_session_snapshot,
    navigate_content,
    open_source,
    reset_all_sessions_to_idle,
    set_big_screen_mode,
    update_playback_progress,
)
from scp_cv.services.playback_sessions import touch_player_heartbeats
from scp_cv.services.ppt_playback_cache import PPT_PLAYBACK_METADATA_KEY
from scp_cv.services.video_wall import VideoWallError


# ══════════════════════════════════════════════════════════════
# get_or_create_session
# ══════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestGetOrCreateSession:
    """测试播放会话的单例获取/创建逻辑。"""

    def test_creates_session_when_none_exists(self) -> None:
        """数据库为空时应创建新会话。"""
        assert PlaybackSession.objects.count() == 0
        session = get_or_create_session(1)
        assert session.pk is not None
        assert session.playback_state == PlaybackState.IDLE
        assert session.window_id == 1
        assert PlaybackSession.objects.count() == 1

    def test_returns_existing_session(self, playback_session: PlaybackSession) -> None:
        """已有会话时应复用同一实例。"""
        session = get_or_create_session(1)
        assert session.pk == playback_session.pk

    def test_idempotent_calls(self) -> None:
        """多次调用应返回同一会话。"""
        first_session = get_or_create_session(1)
        second_session = get_or_create_session(1)
        assert first_session.pk == second_session.pk
        assert PlaybackSession.objects.count() == 1


@pytest.mark.django_db
def test_startup_reset_does_not_queue_runtime_rebuild() -> None:
    """runall 启动前没有播放器可重建，不应遗留会在预热后立即执行的 reset 指令。"""
    session = get_or_create_session(1)
    session.pending_command = PlaybackCommand.PLAY
    session.command_args = {"stale": True}
    session.save()

    reset_all_sessions_to_idle(rebuild_players=False)

    assert PlaybackCommandRecord.objects.count() == 0
    assert set(PlaybackSession.objects.values_list("pending_command", flat=True)) == {
        PlaybackCommand.NONE,
    }

# ══════════════════════════════════════════════════════════════
# get_session_snapshot
# ══════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestGetSessionSnapshot:
    """测试会话状态快照的完整性和字段映射。"""

    def test_snapshot_without_source(self) -> None:
        """无媒体源时快照应包含默认占位值。"""
        snapshot = get_session_snapshot(1)

        assert snapshot["source_name"] == "无"
        assert snapshot["source_type_label"] == "无"
        assert snapshot["playback_state"] == PlaybackState.IDLE
        assert snapshot["current_slide"] == 0
        assert snapshot["position_ms"] == 0

    def test_player_online_requires_recent_player_heartbeat(self) -> None:
        """SSE 在线不能冒充播放器在线；只有播放器心跳后窗口才应在线。"""
        assert get_session_snapshot(1)["player_online"] is False

        touch_player_heartbeats([1])

        snapshot = get_session_snapshot(1)
        assert snapshot["player_online"] is True
        assert snapshot["player_last_seen_at"]

    def test_snapshot_with_source(self, media_source_ppt: MediaSource) -> None:
        """关联源后快照应反映源的信息。"""
        session = get_or_create_session(1)
        session.media_source = media_source_ppt
        session.playback_state = PlaybackState.PLAYING
        session.current_slide = 3
        session.total_slides = 10
        session.save()

        snapshot = get_session_snapshot(1)

        assert snapshot["source_name"] == "测试演示文稿"
        assert snapshot["source_id"] == media_source_ppt.pk
        assert snapshot["source_type"] == "ppt"
        assert snapshot["playback_state"] == PlaybackState.PLAYING
        assert snapshot["current_slide"] == 3
        assert snapshot["total_slides"] == 10

    def test_snapshot_contains_all_required_keys(self) -> None:
        """快照字典应包含所有必要的键。"""
        snapshot = get_session_snapshot(1)
        required_keys = {
            "window_id", "session_id", "source_id", "source_name", "source_type", "source_type_label", "source_uri",
            "playback_state", "playback_state_label",
            "display_mode", "display_mode_label",
            "target_display_label", "spliced_display_label", "is_spliced",
            "error_message",
            "current_slide", "total_slides", "position_ms", "duration_ms",
            "pending_command", "player_online", "player_last_seen_at",
            "last_updated_at", "volume", "is_muted", "loop_enabled",
            "playback_mode",
        }
        assert set(snapshot.keys()) == required_keys


# ══════════════════════════════════════════════════════════════
# open_source
# ══════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestOpenSource:
    """测试媒体源打开逻辑。"""

    def test_open_existing_source(self, media_source_ppt: MediaSource) -> None:
        """打开已有源应设置 LOADING 状态和 OPEN 指令。"""
        session = open_source(1, media_source_ppt.pk)

        assert session.media_source == media_source_ppt
        assert session.playback_state == PlaybackState.LOADING
        assert session.pending_command == PlaybackCommand.OPEN
        assert session.command_args["source_id"] == media_source_ppt.pk
        assert session.command_args["source_type"] == "ppt"
        assert session.command_args["uri"] == media_source_ppt.uri
        assert session.command_args["original_uri"] == media_source_ppt.uri
        assert session.command_args["autoplay"] is True

    def test_open_ppt_uses_ready_playback_cache(
        self,
        media_source_ppt: MediaSource,
        tmp_path: Path,
    ) -> None:
        """已有放映缓存时打开 PPT 应优先下发缓存 URI，并保留 original_uri。"""
        cached_file = tmp_path / "cached.ppsx"
        cached_file.write_bytes(b"cached-show")
        media_source_ppt.metadata = {
            PPT_PLAYBACK_METADATA_KEY: {
                "status": "ready",
                "path": str(cached_file),
            },
        }
        media_source_ppt.save(update_fields=["metadata"])

        session = open_source(1, media_source_ppt.pk)

        assert session.command_args["uri"] == str(cached_file)
        assert session.command_args["original_uri"] == media_source_ppt.uri

    def test_open_ppt_with_target_slide(self, media_source_ppt: MediaSource) -> None:
        """打开 PPT 时应保留目标页码。"""
        session = open_source(1, media_source_ppt.pk, target_slide=4)

        assert session.command_args["target_slide"] == 4

    def test_open_with_autoplay_false(self, media_source_video: MediaSource) -> None:
        """autoplay=False 时指令参数应反映。"""
        session = open_source(1, media_source_video.pk, autoplay=False)

        assert session.command_args["autoplay"] is False

    def test_open_nonexistent_source_raises(self) -> None:
        """打开不存在的源 id 应抛出 PlaybackError。"""
        with pytest.raises(PlaybackError, match="不存在"):
            open_source(1, 99999)

    def test_open_audio_source_raises(self, media_source_audio: MediaSource) -> None:
        """音频源不允许打开到 1-4 号窗口。"""
        with pytest.raises(PlaybackError, match="背景音乐"):
            open_source(1, media_source_audio.pk)

    def test_open_resets_previous_state(
        self, media_source_ppt: MediaSource, media_source_video: MediaSource,
    ) -> None:
        """打开新源应重置之前的播放状态。"""
        # 先打开 PPT 并模拟播放中
        first_session = open_source(1, media_source_ppt.pk)
        first_session.playback_state = PlaybackState.PLAYING
        first_session.current_slide = 5
        first_session.total_slides = 20
        first_session.save()

        # 再打开视频
        second_session = open_source(1, media_source_video.pk)

        assert second_session.media_source == media_source_video
        assert second_session.playback_state == PlaybackState.LOADING
        assert second_session.current_slide == 0
        assert second_session.total_slides == 0

    def test_open_marks_previous_temporary_source_for_cleanup(
        self, media_source_ppt: MediaSource, media_source_video: MediaSource,
    ) -> None:
        """切换离开临时源时应把清理 ID 下发给播放器。"""
        media_source_ppt.is_temporary = True
        media_source_ppt.save(update_fields=["is_temporary"])
        open_source(1, media_source_ppt.pk)

        session = open_source(1, media_source_video.pk)

        assert session.command_args["cleanup_source_id"] == media_source_ppt.pk


# ══════════════════════════════════════════════════════════════
# control_playback
# ══════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestControlPlayback:
    """测试播放控制指令（play / pause / stop）。"""

    def test_play_command(self, media_source_video: MediaSource) -> None:
        """发送 play 指令应设置正确的 pending_command。"""
        open_source(1, media_source_video.pk)
        session = control_playback(1, PlaybackCommand.PLAY)

        assert session.pending_command == PlaybackCommand.PLAY

    def test_pause_command(self, media_source_video: MediaSource) -> None:
        """发送 pause 指令应设置正确的 pending_command。"""
        open_source(1, media_source_video.pk)
        session = control_playback(1, PlaybackCommand.PAUSE)

        assert session.pending_command == PlaybackCommand.PAUSE

    def test_stop_command(self, media_source_video: MediaSource) -> None:
        """发送 stop 指令应设置正确的 pending_command。"""
        open_source(1, media_source_video.pk)
        session = control_playback(1, PlaybackCommand.STOP)

        assert session.pending_command == PlaybackCommand.STOP

    def test_invalid_action_raises(self, media_source_video: MediaSource) -> None:
        """无效的控制动作应抛出 PlaybackError。"""
        open_source(1, media_source_video.pk)
        with pytest.raises(PlaybackError, match="无效"):
            control_playback(1, "rewind")

    def test_no_source_raises(self) -> None:
        """没有打开源时发送控制指令应抛出 PlaybackError。"""
        get_or_create_session(1)
        with pytest.raises(PlaybackError, match="没有打开"):
            control_playback(1, PlaybackCommand.PLAY)


# ══════════════════════════════════════════════════════════════
# navigate_content
# ══════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestNavigateContent:
    """测试内容导航（翻页 / 跳转 / Seek）。"""

    def test_next_command(self, media_source_ppt: MediaSource) -> None:
        """发送 next 应设置正确指令。"""
        open_source(1, media_source_ppt.pk)
        session = navigate_content(1, PlaybackCommand.NEXT)

        assert session.pending_command == PlaybackCommand.NEXT

    def test_prev_command(self, media_source_ppt: MediaSource) -> None:
        """发送 prev 应设置正确指令。"""
        open_source(1, media_source_ppt.pk)
        session = navigate_content(1, PlaybackCommand.PREV)

        assert session.pending_command == PlaybackCommand.PREV

    def test_goto_with_target_index(self, media_source_ppt: MediaSource) -> None:
        """跳转到指定页码应在 command_args 中记录。"""
        open_source(1, media_source_ppt.pk)
        session = navigate_content(1, PlaybackCommand.GOTO, target_index=5)

        assert session.pending_command == PlaybackCommand.GOTO
        assert session.command_args["target_index"] == 5

    def test_goto_out_of_range_raises(self, media_source_ppt: MediaSource) -> None:
        """PPT 跳页超过已知页数时应返回明确错误。"""
        open_source(1, media_source_ppt.pk)
        update_playback_progress(1, current_slide=1, total_slides=3)

        with pytest.raises(PlaybackError, match="超出范围"):
            navigate_content(1, PlaybackCommand.GOTO, target_index=4)

    def test_boundary_prev_still_dispatches_for_ppt_animations(
        self,
        media_source_ppt: MediaSource,
    ) -> None:
        """第一页仍应下发 prev，让播放器后端自行处理动画级回退。"""
        open_source(1, media_source_ppt.pk)
        update_playback_progress(1, current_slide=1, total_slides=3)
        clear_pending_command(1)
        session = navigate_content(1, PlaybackCommand.PREV)

        assert session.pending_command == PlaybackCommand.PREV

    def test_boundary_next_still_dispatches_for_ppt_animations(
        self,
        media_source_ppt: MediaSource,
    ) -> None:
        """最后一页仍应下发 next，让 PowerPoint 可推进末页动画。"""
        open_source(1, media_source_ppt.pk)
        update_playback_progress(1, current_slide=3, total_slides=3)
        clear_pending_command(1)
        session = navigate_content(1, PlaybackCommand.NEXT)

        assert session.pending_command == PlaybackCommand.NEXT

    def test_seek_with_position(self, media_source_video: MediaSource) -> None:
        """Seek 到指定毫秒位置应在 command_args 中记录。"""
        open_source(1, media_source_video.pk)
        session = navigate_content(1, PlaybackCommand.SEEK, position_ms=30000)

        assert session.pending_command == PlaybackCommand.SEEK
        assert session.command_args["position_ms"] == 30000

    def test_ppt_rejects_seek(self, media_source_ppt: MediaSource) -> None:
        """PPT 源不应接受 seek 指令。"""
        open_source(1, media_source_ppt.pk)

        with pytest.raises(PlaybackError, match="不支持 seek"):
            navigate_content(1, PlaybackCommand.SEEK, position_ms=1000)

    def test_invalid_action_raises(self, media_source_ppt: MediaSource) -> None:
        """无效的导航动作应抛出 PlaybackError。"""
        open_source(1, media_source_ppt.pk)
        with pytest.raises(PlaybackError, match="无效"):
            navigate_content(1, "fast_forward")

    def test_repeated_same_navigation_is_not_suppressed(
        self,
        media_source_ppt: MediaSource,
    ) -> None:
        """相同翻页指令连续写入时仍应保持为待消费指令。"""
        open_source(1, media_source_ppt.pk)
        first_session = navigate_content(1, PlaybackCommand.NEXT)
        clear_pending_command(1)

        second_session = navigate_content(1, PlaybackCommand.NEXT)

        assert first_session.pending_command == PlaybackCommand.NEXT
        assert second_session.pending_command == PlaybackCommand.NEXT

    def test_no_source_raises(self) -> None:
        """没有打开源时发送导航指令应抛出 PlaybackError。"""
        get_or_create_session(1)
        with pytest.raises(PlaybackError, match="没有打开"):
            navigate_content(1, PlaybackCommand.NEXT)


# ══════════════════════════════════════════════════════════════
# update_playback_progress
# ══════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestSetBigScreenMode:
    """测试大屏模式切换与视频墙联动。"""

    def test_switches_runtime_and_applies_video_wall(self, monkeypatch: Any) -> None:
        """切换大屏模式时应同步更新运行态并下发视频墙模式。"""
        called_modes: list[str] = []

        monkeypatch.setattr(
            "scp_cv.services.playback.apply_video_wall_mode",
            lambda mode: called_modes.append(mode),
        )

        payload = set_big_screen_mode(BigScreenMode.DOUBLE)

        assert called_modes == [BigScreenMode.DOUBLE]
        assert payload["big_screen_mode"] == BigScreenMode.DOUBLE
        assert RuntimeState.get_instance().big_screen_mode == BigScreenMode.DOUBLE
        session_1 = get_or_create_session(1)
        session_2 = get_or_create_session(2)
        session_3 = get_or_create_session(3)
        session_4 = get_or_create_session(4)
        assert session_1.is_muted is False
        assert session_2.is_muted is False
        assert session_3.is_muted is True
        assert session_4.is_muted is True

    def test_keeps_previous_runtime_mode_when_video_wall_apply_fails(self, monkeypatch: Any) -> None:
        """视频墙下发失败时应回滚运行态并返回播放层错误。"""
        runtime = RuntimeState.get_instance()
        runtime.big_screen_mode = BigScreenMode.SINGLE
        runtime.save(update_fields=["big_screen_mode", "updated_at"])

        def raise_video_wall_error(_mode: str) -> None:
            raise VideoWallError("发送视频墙控制包失败")

        monkeypatch.setattr("scp_cv.services.playback.apply_video_wall_mode", raise_video_wall_error)

        with pytest.raises(PlaybackError, match="发送视频墙控制包失败"):
            set_big_screen_mode(BigScreenMode.DOUBLE)

        assert RuntimeState.get_instance().big_screen_mode == BigScreenMode.SINGLE


@pytest.mark.django_db
class TestUpdatePlaybackProgress:
    """测试播放进度上报。"""

    def test_update_ppt_progress(self) -> None:
        """上报 PPT 翻页进度应正确写入数据库。"""
        get_or_create_session(1)
        session = update_playback_progress(
            1,
            playback_state=PlaybackState.PLAYING,
            current_slide=3,
            total_slides=20,
        )

        assert session.playback_state == PlaybackState.PLAYING
        assert session.current_slide == 3
        assert session.total_slides == 20

    def test_update_video_progress(self) -> None:
        """上报视频播放进度应正确写入数据库。"""
        get_or_create_session(1)
        session = update_playback_progress(
            1,
            playback_state=PlaybackState.PLAYING,
            position_ms=45000,
            duration_ms=120000,
        )

        assert session.position_ms == 45000
        assert session.duration_ms == 120000

    def test_partial_update(self) -> None:
        """只上报部分字段时不应影响其他字段。"""
        get_or_create_session(1)
        update_playback_progress(
            1,
            playback_state=PlaybackState.PLAYING,
            current_slide=5,
            total_slides=10,
            position_ms=1000,
        )
        session = update_playback_progress(1, current_slide=6)

        assert session.current_slide == 6
        assert session.total_slides == 10  # 未传入的字段保持不变
        assert session.playback_state == PlaybackState.PLAYING

    def test_none_params_are_ignored(self) -> None:
        """传入 None 的参数不应修改对应字段。"""
        get_or_create_session(1)
        update_playback_progress(1, playback_state=PlaybackState.PAUSED)
        session = update_playback_progress(1, playback_state=None)

        assert session.playback_state == PlaybackState.PAUSED  # 未被覆盖
