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
    SourceState,
)
from scp_cv.services.playback import get_or_create_session
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
        targets = {target["window_id"]: target for target in scenario.targets}
        assert targets[1]["source_id"] == media_source_ppt.pk
        assert targets[1]["autoplay"] is True
        assert targets[1]["resume"] is True
        assert targets[2]["source_id"] == media_source_video.pk
        assert targets[2]["autoplay"] is False
        assert targets[2]["resume"] is True

    def test_capture_overwrites_existing_scenario(
        self,
        media_source_ppt: MediaSource,
        media_source_video: MediaSource,
    ) -> None:
        """传入已有预案 ID 时应覆盖同一条记录而不是创建新记录。"""
        scenario = Scenario.objects.create(
            name="旧预案",
        )
        scenario.targets = [{
            "window_id": 1,
            "source_state": SourceState.SET,
            "source_id": media_source_video.pk,
            "autoplay": True,
            "resume": True,
        }]
        scenario.save(update_fields=["targets"])
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
        targets = {target["window_id"]: target for target in updated.targets}
        assert targets[1]["source_id"] == media_source_ppt.pk

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
            targets=[
                {
                    "window_id": 1,
                    "source_state": SourceState.SET,
                    "source_id": media_source_ppt.pk,
                    "autoplay": True,
                    "resume": True,
                },
                {
                    "window_id": 2,
                    "source_state": SourceState.SET,
                    "source_id": media_source_video.pk,
                    "autoplay": True,
                    "resume": True,
                },
            ],
        )

        scenario_dict = list_scenarios()[0]

        targets = {target["window_id"]: target for target in scenario_dict["targets"]}
        assert targets[1]["source_name"] == "测试演示文稿"
        assert targets[2]["source_name"] == "测试视频"
