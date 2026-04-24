#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
预案管理服务单元测试。
覆盖预案从当前播放会话捕获、覆盖和序列化展示字段。
@Project : SCP-cv
@File : test_scenario_service.py
@Author : Qintsg
@Date : 2026-04-24
'''
from __future__ import annotations

import pytest

from scp_cv.apps.playback.models import (
    MediaSource,
    PlaybackState,
    Scenario,
)
from scp_cv.services.playback import get_or_create_session, set_splice_mode
from scp_cv.services.scenario import (
    ScenarioError,
    capture_scenario_from_current_state,
    list_scenarios,
)


@pytest.mark.django_db
class TestCaptureScenarioFromCurrentState:
    """测试从当前窗口状态捕获预案的服务层逻辑。"""

    def test_capture_independent_windows(
        self,
        media_source_ppt: MediaSource,
        media_source_video: MediaSource,
    ) -> None:
        """独立模式应捕获窗口 1/2 的源与自动播放策略。"""
        session_1 = get_or_create_session(1)
        session_1.media_source = media_source_ppt
        session_1.playback_state = PlaybackState.PLAYING
        session_1.save(update_fields=["media_source", "playback_state"])

        session_2 = get_or_create_session(2)
        session_2.media_source = media_source_video
        session_2.playback_state = PlaybackState.PAUSED
        session_2.save(update_fields=["media_source", "playback_state"])

        scenario = capture_scenario_from_current_state(
            name="当前双窗口",
            description="从播放状态捕获",
        )

        assert scenario.name == "当前双窗口"
        assert scenario.description == "从播放状态捕获"
        assert scenario.is_splice_mode is False
        assert scenario.window1_source == media_source_ppt
        assert scenario.window1_autoplay is True
        assert scenario.window1_resume is True
        assert scenario.window2_source == media_source_video
        assert scenario.window2_autoplay is False
        assert scenario.window2_resume is True

    def test_capture_splice_mode_ignores_window2(
        self,
        media_source_ppt: MediaSource,
        media_source_video: MediaSource,
    ) -> None:
        """拼接模式只保存窗口 1 源，窗口 2 由拼接逻辑同步。"""
        set_splice_mode(True)

        session_1 = get_or_create_session(1)
        session_1.media_source = media_source_ppt
        session_1.playback_state = PlaybackState.LOADING
        session_1.save(update_fields=["media_source", "playback_state"])

        session_2 = get_or_create_session(2)
        session_2.media_source = media_source_video
        session_2.playback_state = PlaybackState.PLAYING
        session_2.save(update_fields=["media_source", "playback_state"])

        scenario = capture_scenario_from_current_state(name="拼接当前状态")

        assert scenario.is_splice_mode is True
        assert scenario.window1_source == media_source_ppt
        assert scenario.window1_autoplay is True
        assert scenario.window2_source is None
        assert scenario.window2_autoplay is False

    def test_capture_overwrites_existing_scenario(
        self,
        media_source_ppt: MediaSource,
        media_source_video: MediaSource,
    ) -> None:
        """传入已有预案 ID 时应覆盖同一条记录而不是创建新记录。"""
        scenario = Scenario.objects.create(
            name="旧预案",
            window1_source=media_source_video,
        )
        session_1 = get_or_create_session(1)
        session_1.media_source = media_source_ppt
        session_1.playback_state = PlaybackState.PLAYING
        session_1.save(update_fields=["media_source", "playback_state"])

        updated = capture_scenario_from_current_state(
            name="覆盖后的预案",
            description="覆盖描述",
            scenario_id=scenario.pk,
        )

        assert updated.pk == scenario.pk
        assert Scenario.objects.count() == 1
        assert updated.name == "覆盖后的预案"
        assert updated.description == "覆盖描述"
        assert updated.window1_source == media_source_ppt

    def test_capture_rejects_empty_name(self) -> None:
        """预案名称为空时应返回业务异常。"""
        with pytest.raises(ScenarioError, match="预案名称不能为空"):
            capture_scenario_from_current_state(name="  ")


@pytest.mark.django_db
class TestScenarioList:
    """测试预案列表序列化字段。"""

    def test_list_includes_source_names(
        self,
        media_source_ppt: MediaSource,
        media_source_video: MediaSource,
    ) -> None:
        """列表项应包含窗口源名称，供前端直接展示。"""
        Scenario.objects.create(
            name="列表预案",
            window1_source=media_source_ppt,
            window2_source=media_source_video,
        )

        scenario_dict = list_scenarios()[0]

        assert scenario_dict["window1_source_name"] == "测试演示文稿"
        assert scenario_dict["window2_source_name"] == "测试视频"
