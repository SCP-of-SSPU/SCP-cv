#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
播放会话创建与状态快照服务测试。
@Project : SCP-cv
@File : test_playback_session_service.py
@Author : Qintsg
@Date : 2026-07-12
'''
from __future__ import annotations

import pytest

from scp_cv.apps.playback.models import MediaSource, PlaybackSession, PlaybackState
from scp_cv.services.playback import get_or_create_session, get_session_snapshot


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
            "pending_command", "last_updated_at", "volume", "is_muted", "loop_enabled",
        }
        assert set(snapshot.keys()) == required_keys
