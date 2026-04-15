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

from unittest.mock import patch

import pytest

from scp_cv.apps.playback.models import (
    MediaSource,
    PlaybackCommand,
    PlaybackMode,
    PlaybackSession,
    PlaybackState,
)
from scp_cv.services.playback import (
    PlaybackError,
    clear_pending_command,
    close_source,
    control_playback,
    get_or_create_session,
    get_session_snapshot,
    navigate_content,
    open_source,
    select_display_target,
    stop_current_content,
    update_playback_progress,
)


# ══════════════════════════════════════════════════════════════
# get_or_create_session
# ══════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestGetOrCreateSession:
    """测试播放会话的单例获取/创建逻辑。"""

    def test_creates_session_when_none_exists(self) -> None:
        """数据库为空时应创建新会话。"""
        assert PlaybackSession.objects.count() == 0
        session = get_or_create_session()
        assert session.pk is not None
        assert session.playback_state == PlaybackState.IDLE
        assert PlaybackSession.objects.count() == 1

    def test_returns_existing_session(self, playback_session: PlaybackSession) -> None:
        """已有会话时应复用同一实例。"""
        session = get_or_create_session()
        assert session.pk == playback_session.pk

    def test_idempotent_calls(self) -> None:
        """多次调用应返回同一会话。"""
        first_session = get_or_create_session()
        second_session = get_or_create_session()
        assert first_session.pk == second_session.pk
        assert PlaybackSession.objects.count() == 1


# ══════════════════════════════════════════════════════════════
# get_session_snapshot
# ══════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestGetSessionSnapshot:
    """测试会话状态快照的完整性和字段映射。"""

    def test_snapshot_without_source(self) -> None:
        """无媒体源时快照应包含默认占位值。"""
        snapshot = get_session_snapshot()

        assert snapshot["source_name"] == "无"
        assert snapshot["source_type_label"] == "无"
        assert snapshot["playback_state"] == PlaybackState.IDLE
        assert snapshot["current_slide"] == 0
        assert snapshot["position_ms"] == 0

    def test_snapshot_with_source(self, media_source_ppt: MediaSource) -> None:
        """关联源后快照应反映源的信息。"""
        session = get_or_create_session()
        session.media_source = media_source_ppt
        session.playback_state = PlaybackState.PLAYING
        session.current_slide = 3
        session.total_slides = 10
        session.save()

        snapshot = get_session_snapshot()

        assert snapshot["source_name"] == "测试演示文稿"
        assert snapshot["source_type"] == "ppt"
        assert snapshot["playback_state"] == PlaybackState.PLAYING
        assert snapshot["current_slide"] == 3
        assert snapshot["total_slides"] == 10

    def test_snapshot_contains_all_required_keys(self) -> None:
        """快照字典应包含所有必要的键。"""
        snapshot = get_session_snapshot()
        required_keys = {
            "session_id", "source_name", "source_type", "source_type_label", "source_uri",
            "playback_state", "playback_state_label",
            "display_mode", "display_mode_label",
            "target_display_label", "spliced_display_label", "is_spliced",
            "current_slide", "total_slides", "position_ms", "duration_ms",
            "pending_command", "last_updated_at", "loop_enabled",
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
        session = open_source(media_source_ppt.pk)

        assert session.media_source == media_source_ppt
        assert session.playback_state == PlaybackState.LOADING
        assert session.pending_command == PlaybackCommand.OPEN
        assert session.command_args["source_type"] == "ppt"
        assert session.command_args["uri"] == media_source_ppt.uri
        assert session.command_args["autoplay"] is True

    def test_open_with_autoplay_false(self, media_source_video: MediaSource) -> None:
        """autoplay=False 时指令参数应反映。"""
        session = open_source(media_source_video.pk, autoplay=False)

        assert session.command_args["autoplay"] is False

    def test_open_nonexistent_source_raises(self) -> None:
        """打开不存在的源 id 应抛出 PlaybackError。"""
        with pytest.raises(PlaybackError, match="不存在"):
            open_source(99999)

    def test_open_resets_previous_state(
        self, media_source_ppt: MediaSource, media_source_video: MediaSource,
    ) -> None:
        """打开新源应重置之前的播放状态。"""
        # 先打开 PPT 并模拟播放中
        first_session = open_source(media_source_ppt.pk)
        first_session.playback_state = PlaybackState.PLAYING
        first_session.current_slide = 5
        first_session.total_slides = 20
        first_session.save()

        # 再打开视频
        second_session = open_source(media_source_video.pk)

        assert second_session.media_source == media_source_video
        assert second_session.playback_state == PlaybackState.LOADING
        assert second_session.current_slide == 0
        assert second_session.total_slides == 0


# ══════════════════════════════════════════════════════════════
# control_playback
# ══════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestControlPlayback:
    """测试播放控制指令（play / pause / stop）。"""

    def test_play_command(self, media_source_video: MediaSource) -> None:
        """发送 play 指令应设置正确的 pending_command。"""
        open_source(media_source_video.pk)
        session = control_playback(PlaybackCommand.PLAY)

        assert session.pending_command == PlaybackCommand.PLAY

    def test_pause_command(self, media_source_video: MediaSource) -> None:
        """发送 pause 指令应设置正确的 pending_command。"""
        open_source(media_source_video.pk)
        session = control_playback(PlaybackCommand.PAUSE)

        assert session.pending_command == PlaybackCommand.PAUSE

    def test_stop_command(self, media_source_video: MediaSource) -> None:
        """发送 stop 指令应设置正确的 pending_command。"""
        open_source(media_source_video.pk)
        session = control_playback(PlaybackCommand.STOP)

        assert session.pending_command == PlaybackCommand.STOP

    def test_invalid_action_raises(self, media_source_video: MediaSource) -> None:
        """无效的控制动作应抛出 PlaybackError。"""
        open_source(media_source_video.pk)
        with pytest.raises(PlaybackError, match="无效"):
            control_playback("rewind")

    def test_no_source_raises(self) -> None:
        """没有打开源时发送控制指令应抛出 PlaybackError。"""
        get_or_create_session()
        with pytest.raises(PlaybackError, match="没有打开"):
            control_playback(PlaybackCommand.PLAY)


# ══════════════════════════════════════════════════════════════
# navigate_content
# ══════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestNavigateContent:
    """测试内容导航（翻页 / 跳转 / Seek）。"""

    def test_next_command(self, media_source_ppt: MediaSource) -> None:
        """发送 next 应设置正确指令。"""
        open_source(media_source_ppt.pk)
        session = navigate_content(PlaybackCommand.NEXT)

        assert session.pending_command == PlaybackCommand.NEXT

    def test_prev_command(self, media_source_ppt: MediaSource) -> None:
        """发送 prev 应设置正确指令。"""
        open_source(media_source_ppt.pk)
        session = navigate_content(PlaybackCommand.PREV)

        assert session.pending_command == PlaybackCommand.PREV

    def test_goto_with_target_index(self, media_source_ppt: MediaSource) -> None:
        """跳转到指定页码应在 command_args 中记录。"""
        open_source(media_source_ppt.pk)
        session = navigate_content(PlaybackCommand.GOTO, target_index=5)

        assert session.pending_command == PlaybackCommand.GOTO
        assert session.command_args["target_index"] == 5

    def test_seek_with_position(self, media_source_video: MediaSource) -> None:
        """Seek 到指定毫秒位置应在 command_args 中记录。"""
        open_source(media_source_video.pk)
        session = navigate_content(PlaybackCommand.SEEK, position_ms=30000)

        assert session.pending_command == PlaybackCommand.SEEK
        assert session.command_args["position_ms"] == 30000

    def test_invalid_action_raises(self, media_source_ppt: MediaSource) -> None:
        """无效的导航动作应抛出 PlaybackError。"""
        open_source(media_source_ppt.pk)
        with pytest.raises(PlaybackError, match="无效"):
            navigate_content("fast_forward")

    def test_no_source_raises(self) -> None:
        """没有打开源时发送导航指令应抛出 PlaybackError。"""
        get_or_create_session()
        with pytest.raises(PlaybackError, match="没有打开"):
            navigate_content(PlaybackCommand.NEXT)


# ══════════════════════════════════════════════════════════════
# close_source
# ══════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestCloseSource:
    """测试源关闭和会话重置。"""

    def test_close_with_active_source(self, media_source_video: MediaSource) -> None:
        """有活跃源时关闭应发出 CLOSE 指令。"""
        open_source(media_source_video.pk)
        session = close_source()

        assert session.pending_command == PlaybackCommand.CLOSE

    def test_close_without_source_resets(self) -> None:
        """无活跃源时关闭应直接重置为 IDLE。"""
        get_or_create_session()
        session = close_source()

        assert session.playback_state == PlaybackState.IDLE
        assert session.pending_command == PlaybackCommand.NONE

    def test_stop_current_content_delegates(self, media_source_video: MediaSource) -> None:
        """stop_current_content 应委托给 close_source。"""
        open_source(media_source_video.pk)
        session = stop_current_content()

        assert session.pending_command == PlaybackCommand.CLOSE


# ══════════════════════════════════════════════════════════════
# clear_pending_command
# ══════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestClearPendingCommand:
    """测试指令清除（播放器消费指令后调用）。"""

    def test_clears_command_and_args(self, media_source_ppt: MediaSource) -> None:
        """清除后 pending_command 应回到 NONE。"""
        open_source(media_source_ppt.pk)
        session = clear_pending_command()

        assert session.pending_command == PlaybackCommand.NONE
        assert session.command_args == {}


# ══════════════════════════════════════════════════════════════
# update_playback_progress
# ══════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestUpdatePlaybackProgress:
    """测试播放进度上报。"""

    def test_update_ppt_progress(self) -> None:
        """上报 PPT 翻页进度应正确写入数据库。"""
        get_or_create_session()
        session = update_playback_progress(
            playback_state=PlaybackState.PLAYING,
            current_slide=3,
            total_slides=20,
        )

        assert session.playback_state == PlaybackState.PLAYING
        assert session.current_slide == 3
        assert session.total_slides == 20

    def test_update_video_progress(self) -> None:
        """上报视频播放进度应正确写入数据库。"""
        get_or_create_session()
        session = update_playback_progress(
            playback_state=PlaybackState.PLAYING,
            position_ms=45000,
            duration_ms=120000,
        )

        assert session.position_ms == 45000
        assert session.duration_ms == 120000

    def test_partial_update(self) -> None:
        """只上报部分字段时不应影响其他字段。"""
        get_or_create_session()
        update_playback_progress(
            playback_state=PlaybackState.PLAYING,
            current_slide=5,
            total_slides=10,
            position_ms=1000,
        )
        session = update_playback_progress(current_slide=6)

        assert session.current_slide == 6
        assert session.total_slides == 10  # 未传入的字段保持不变
        assert session.playback_state == PlaybackState.PLAYING

    def test_none_params_are_ignored(self) -> None:
        """传入 None 的参数不应修改对应字段。"""
        get_or_create_session()
        update_playback_progress(playback_state=PlaybackState.PAUSED)
        session = update_playback_progress(playback_state=None)

        assert session.playback_state == PlaybackState.PAUSED  # 未被覆盖


# ══════════════════════════════════════════════════════════════
# select_display_target
# ══════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestSelectDisplayTarget:
    """测试显示目标选择。"""

    def _make_display_target(
        self, name: str, index: int, is_primary: bool = False,
    ) -> object:
        """
        构造一个 DisplayTarget 数据类实例。
        :param name: 显示器名称
        :param index: 显示器索引
        :param is_primary: 是否主屏
        :return: DisplayTarget 实例
        """
        from scp_cv.services.display import DisplayTarget
        return DisplayTarget(
            name=name,
            index=index,
            is_primary=is_primary,
            x=0 if index == 0 else 1920,
            y=0,
            width=1920,
            height=1080,
        )

    @patch("scp_cv.services.playback.list_display_targets")
    def test_select_single_display(self, mock_displays: object) -> None:
        """选择单屏模式应正确设置目标显示器。"""
        mock_displays.return_value = [
            self._make_display_target("HDMI-1", 0, is_primary=True),
            self._make_display_target("HDMI-2", 1),
        ]

        session = select_display_target(PlaybackMode.SINGLE, "HDMI-2")

        assert session.display_mode == PlaybackMode.SINGLE
        assert session.target_display_label == "HDMI-2"
        assert session.is_spliced is False

    @patch("scp_cv.services.playback.list_display_targets")
    def test_select_nonexistent_display_raises(self, mock_displays: object) -> None:
        """选择不存在的显示器应抛出 PlaybackError。"""
        mock_displays.return_value = [
            self._make_display_target("HDMI-1", 0, is_primary=True),
        ]

        with pytest.raises(PlaybackError, match="不存在"):
            select_display_target(PlaybackMode.SINGLE, "VGA-1")

    @patch("scp_cv.services.playback.build_left_right_splice_target")
    @patch("scp_cv.services.playback.list_display_targets")
    def test_select_splice_mode(self, mock_displays: object, mock_splice: object) -> None:
        """左右拼接模式应设置 is_spliced 和拼接标签。"""
        display_left = self._make_display_target("HDMI-1", 0, is_primary=True)
        display_right = self._make_display_target("HDMI-2", 1)
        mock_displays.return_value = [display_left, display_right]

        from scp_cv.services.display import SplicedDisplayTarget
        mock_splice.return_value = SplicedDisplayTarget(
            left=display_left,
            right=display_right,
            width=3840,
            height=1080,
        )

        session = select_display_target(PlaybackMode.LEFT_RIGHT_SPLICE)

        assert session.display_mode == PlaybackMode.LEFT_RIGHT_SPLICE
        assert session.is_spliced is True
        assert "HDMI-1" in session.spliced_display_label
        assert "HDMI-2" in session.spliced_display_label

    @patch("scp_cv.services.playback.build_left_right_splice_target")
    @patch("scp_cv.services.playback.list_display_targets")
    def test_splice_insufficient_displays_raises(
        self, mock_displays: object, mock_splice: object,
    ) -> None:
        """只有一台显示器时拼接应抛出 PlaybackError。"""
        mock_displays.return_value = [
            self._make_display_target("HDMI-1", 0, is_primary=True),
        ]
        mock_splice.return_value = None

        with pytest.raises(PlaybackError, match="不足"):
            select_display_target(PlaybackMode.LEFT_RIGHT_SPLICE)

    def test_unknown_display_mode_raises(self) -> None:
        """未知的显示模式应抛出 PlaybackError。"""
        with pytest.raises(PlaybackError, match="未知"):
            select_display_target("triple_screen")
