#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
REST 控制命令回执与持久队列可观测性测试。
@Project : SCP-cv
@File : test_control_command_api.py
@Author : Qintsg
@Date : 2026-07-11
'''
from __future__ import annotations

from pathlib import Path

import pytest
from django.conf import settings
from django.test import Client

from scp_cv.apps.playback.models import (
    BackgroundAudioCommand,
    ControlCommand,
    ControlCommandStatus,
    MediaSource,
    PlaybackCommand,
    PlaybackSession,
    Scenario,
)
from scp_cv.services.playback import RESET_ALL_WINDOWS_ARG


@pytest.mark.django_db
def test_deleting_current_audio_source_returns_stop_command(
    media_source_audio: MediaSource,
) -> None:
    """删除当前背景音频源时应返回条件入队的 STOP 命令。"""
    client = Client()
    client.post(
        "/api/background-audio/play-source/",
        data={"source_id": media_source_audio.pk},
        content_type="application/json",
    )

    response = client.delete(f"/api/sources/{media_source_audio.pk}/")

    assert response.status_code == 200
    assert [(command["target"], command["command"]) for command in response.json()["commands"]] == [
        ("background_audio", BackgroundAudioCommand.STOP),
    ]


@pytest.mark.django_db
def test_playback_open_api_updates_session(media_source_ppt: MediaSource) -> None:
    """POST /api/playback/{window}/open/ 应打开媒体源并返回全量窗口快照。"""
    client = Client()

    response = client.post(
        "/api/playback/1/open/",
        data={"source_id": media_source_ppt.pk, "autoplay": True},
        content_type="application/json",
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["sessions"][0]["source_name"] == media_source_ppt.name
    assert "ppt_backend" not in payload["sessions"][0]
    queued = ControlCommand.objects.get(target="window:1")
    assert payload["commands"] == [{
        "id": queued.pk,
        "target": "window:1",
        "command": PlaybackCommand.OPEN,
        "status": ControlCommandStatus.PENDING,
        "error_message": "",
    }]


@pytest.mark.django_db
def test_legacy_playback_open_returns_accepted_command(
    media_source_ppt: MediaSource,
) -> None:
    """保留的表单控制入口也应返回可追踪的持久化命令 ID。"""
    client = Client()

    response = client.post(
        "/playback/1/open/",
        data={"source_id": media_source_ppt.pk, "autoplay": "true"},
    )

    assert response.status_code == 200
    assert [(command["target"], command["command"]) for command in response.json()["commands"]] == [
        ("window:1", PlaybackCommand.OPEN),
    ]


@pytest.mark.django_db
def test_runtime_update_returns_audio_policy_commands() -> None:
    """大屏模式变更应返回其实际下发的四窗静音策略命令。"""
    client = Client()

    response = client.patch(
        "/api/runtime/",
        data={"big_screen_mode": "double"},
        content_type="application/json",
    )

    assert response.status_code == 200
    commands = response.json()["commands"]
    assert [command["target"] for command in commands] == [
        "window:1",
        "window:2",
        "window:3",
        "window:4",
    ]
    assert all(command["command"] == PlaybackCommand.SET_MUTE for command in commands)


@pytest.mark.django_db
def test_reset_all_sessions_api_sets_windows_idle(media_source_ppt: MediaSource) -> None:
    """POST /api/playback/reset-all/ 应将全部窗口重置为待机。"""
    client = Client()
    client.post(
        "/api/playback/1/open/",
        data={"source_id": media_source_ppt.pk, "autoplay": True},
        content_type="application/json",
    )

    response = client.post("/api/playback/reset-all/")
    session = PlaybackSession.objects.get(window_id=1)

    assert response.status_code == 200
    assert response.json()["sessions"][0]["playback_state"] == "idle"
    assert session.media_source is None
    assert session.pending_command == PlaybackCommand.CLOSE
    assert session.command_args[RESET_ALL_WINDOWS_ARG] is True
    assert "reset_token" in session.command_args
    commands = response.json()["commands"]
    assert [command["status"] for command in commands[:4]] == [
        ControlCommandStatus.CANCELLED,
    ] * 4
    assert [command["status"] for command in commands[4:]] == [
        ControlCommandStatus.PENDING,
    ] * 4


@pytest.mark.django_db
def test_shutdown_system_api_requests_close_and_marks_signal(media_source_ppt: MediaSource) -> None:
    """POST /api/system/shutdown/ 应写入关闭信号并返回待机态会话。"""
    client = Client()
    signal_path = Path(settings.LOG_DIR) / "runall.shutdown"
    signal_path.write_text("", encoding="utf-8")
    client.post(
        "/api/playback/1/open/",
        data={"source_id": media_source_ppt.pk, "autoplay": True},
        content_type="application/json",
    )

    response = client.post("/api/system/shutdown/")
    session = PlaybackSession.objects.get(window_id=1)

    assert response.status_code == 200
    assert response.json()["detail"] == "系统关闭请求已发送"
    assert response.json()["sessions"][0]["playback_state"] == "idle"
    assert session.media_source is None
    assert signal_path.read_text(encoding="utf-8").strip() == "shutdown"
    accepted_commands = response.json()["commands"]
    assert len(accepted_commands) == 8
    assert [command["target"] for command in accepted_commands[:4]] == [
        "window:1",
        "window:2",
        "window:3",
        "window:4",
    ]
    assert all(
        command["command"] == PlaybackCommand.CLOSE
        for command in accepted_commands[:4]
    )
    assert all(
        command["command"] == PlaybackCommand.SET_MUTE
        for command in accepted_commands[4:]
    )


@pytest.mark.django_db
def test_scenario_activation_returns_accepted_commands(
    media_source_ppt: MediaSource,
) -> None:
    """预案激活响应应列出其实际下发的窗口命令。"""
    client = Client()
    scenario = Scenario.objects.create(
        name="命令回执预案",
        targets=[{
            "window_id": 1,
            "source_state": "set",
            "source_id": media_source_ppt.pk,
            "autoplay": True,
            "resume": False,
        }],
    )

    response = client.post(f"/api/scenarios/{scenario.pk}/activate/")

    assert response.status_code == 200
    assert [(command["target"], command["command"]) for command in response.json()["commands"]] == [
        ("window:1", PlaybackCommand.OPEN),
    ]


@pytest.mark.django_db
@pytest.mark.parametrize(
    "endpoint",
    [
        "/api/scenarios/{scenario_id}/activate/",
        "/scenarios/{scenario_id}/activate/",
    ],
)
def test_partial_scenario_failure_returns_already_accepted_commands(
    media_source_ppt: MediaSource,
    endpoint: str,
) -> None:
    """预案后续目标失败时，响应不得隐藏此前已经持久化的命令。"""
    scenario = Scenario.objects.create(
        name="部分失败预案",
        targets=[
            {
                "window_id": 1,
                "source_state": "set",
                "source_id": media_source_ppt.pk,
                "autoplay": True,
                "resume": False,
            },
            {
                "window_id": 2,
                "source_state": "set",
                "source_id": 999999,
                "autoplay": True,
                "resume": False,
            },
        ],
    )

    response = Client().post(endpoint.format(scenario_id=scenario.pk))

    assert response.status_code == 400
    assert [(command["target"], command["command"]) for command in response.json()["commands"]] == [
        ("window:1", PlaybackCommand.OPEN),
    ]


@pytest.mark.django_db
def test_ppt_media_control_api_sets_command(media_source_ppt: MediaSource) -> None:
    """PPT 媒体控制应追加到持久队列且不覆盖尚未执行的 OPEN。"""
    client = Client()
    client.post(
        "/api/playback/1/open/",
        data={"source_id": media_source_ppt.pk, "autoplay": True},
        content_type="application/json",
    )

    response = client.post(
        "/api/playback/1/ppt-media/",
        data={"action": "play", "media_id": "m1", "media_index": 1},
        content_type="application/json",
    )
    session = PlaybackSession.objects.get(window_id=1)

    assert response.status_code == 200
    assert session.pending_command == PlaybackCommand.OPEN
    queued = list(
        ControlCommand.objects.filter(target="window:1").order_by("id")
    )
    assert [item.command for item in queued] == [
        PlaybackCommand.OPEN,
        PlaybackCommand.PPT_MEDIA,
    ]
    assert queued[1].arguments["media_id"] == "m1"


@pytest.mark.django_db
def test_reset_ppt_playback_api_requests_ppt_reset(media_source_ppt: MediaSource) -> None:
    """PPT 重置 API 应以 CLOSE→OPEN 批次替换旧指令并保留页码。"""
    client = Client()
    client.post(
        "/api/playback/1/open/",
        data={"source_id": media_source_ppt.pk, "autoplay": True, "ppt_backend": "wps"},
        content_type="application/json",
    )
    session = PlaybackSession.objects.get(window_id=1)
    session.current_slide = 6
    session.total_slides = 9
    session.save(update_fields=["current_slide", "total_slides"])

    response = client.post("/api/playback/reset-ppt/")
    session.refresh_from_db()

    assert response.status_code == 200
    assert session.pending_command == PlaybackCommand.CLOSE
    queued = list(
        ControlCommand.objects.filter(target="window:1").order_by("id")
    )
    assert queued[0].status == ControlCommandStatus.CANCELLED
    assert [item.command for item in queued[1:]] == [
        PlaybackCommand.CLOSE,
        PlaybackCommand.OPEN,
    ]
    assert queued[1].batch_id == queued[2].batch_id
    assert queued[2].arguments["target_slide"] == 6
    assert "ppt_backend" not in queued[2].arguments
    assert [command["id"] for command in response.json()["commands"]] == [
        queued[1].pk,
        queued[2].pk,
    ]
