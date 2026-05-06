#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
控制台 REST API 测试。
覆盖 Vue 前端依赖的源管理、播放控制、会话、显示器和预案接口。
@Project : SCP-cv
@File : test_rest_api.py
@Author : Qintsg
@Date : 2026-04-26
'''
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from unittest.mock import patch

from django.conf import settings

import pytest
from django.test import Client

from scp_cv.apps.playback.models import MediaSource, PlaybackCommand, PlaybackSession
from scp_cv.services.playback import get_or_create_session


@dataclass(frozen=True)
class _DisplayStub:
    """显示器测试替身，字段与 DisplayTarget 保持一致。"""

    index: int
    name: str
    width: int
    height: int
    x: int
    y: int
    is_primary: bool


@pytest.mark.django_db
def test_sources_api_lists_media_sources(media_source_ppt: MediaSource) -> None:
    """GET /api/sources/ 应返回媒体源列表。"""
    client = Client()

    response = client.get("/api/sources/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["sources"][0]["id"] == media_source_ppt.pk


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


@pytest.mark.django_db
def test_playback_control_api_reports_missing_source() -> None:
    """无媒体源时发送播放控制应返回稳定错误响应。"""
    client = Client()

    response = client.post(
        "/api/playback/1/control/",
        data={"action": "play"},
        content_type="application/json",
    )

    assert response.status_code == 400
    assert response.json()["code"] == "playback_error"


@pytest.mark.django_db
def test_sessions_api_returns_four_windows() -> None:
    """GET /api/sessions/ 应返回 1-4 号窗口快照。"""
    client = Client()
    get_or_create_session(1)

    response = client.get("/api/sessions/")

    assert response.status_code == 200
    assert [item["window_id"] for item in response.json()["sessions"]] == [1, 2, 3, 4]


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
    assert session.pending_command == PlaybackCommand.SET_MUTE


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


def test_displays_api_uses_display_service() -> None:
    """GET /api/displays/ 应序列化显示器信息。"""
    client = Client()
    displays = [
        _DisplayStub(1, "Display 1", 1920, 1080, 0, 0, True),
        _DisplayStub(2, "Display 2", 1920, 1080, 1920, 0, False),
    ]

    with patch("scp_cv.apps.dashboard.api_playback_views.list_display_targets", return_value=displays):
        response = client.get("/api/displays/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["targets"][0]["name"] == "Display 1"
    assert payload["splice_label"] == "Display 1 + Display 2"


@pytest.mark.django_db
def test_scenarios_api_create_and_delete(media_source_ppt: MediaSource) -> None:
    """预案 REST API 应支持创建和删除。"""
    client = Client()

    create_response = client.post(
        "/api/scenarios/",
        data={"name": "测试预案", "window1_source_id": media_source_ppt.pk},
        content_type="application/json",
    )

    assert create_response.status_code == 201
    scenario_id = create_response.json()["scenario"]["id"]

    delete_response = client.delete(f"/api/scenarios/{scenario_id}/")
    assert delete_response.status_code == 200


@pytest.mark.django_db
def test_ppt_resources_api_replace_and_list(media_source_ppt: MediaSource) -> None:
    """PPT 资源 REST API 应支持覆盖保存和读取。"""
    client = Client()

    save_response = client.put(
        f"/api/sources/{media_source_ppt.pk}/ppt-resources/",
        data={"resources": [{"page_index": 1, "speaker_notes": "提词器"}]},
        content_type="application/json",
    )
    list_response = client.get(f"/api/sources/{media_source_ppt.pk}/ppt-resources/")

    assert save_response.status_code == 200
    assert list_response.status_code == 200
    assert list_response.json()["resources"][0]["speaker_notes"] == "提词器"


@pytest.mark.django_db
def test_ppt_media_control_api_sets_command(media_source_ppt: MediaSource) -> None:
    """PPT 当前页媒体控制 API 应写入专用播放指令。"""
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
    assert session.pending_command == PlaybackCommand.PPT_MEDIA
    assert session.command_args["media_id"] == "m1"


def test_device_power_api_uses_tcp_service() -> None:
    """电源 API 应调用 TCP 电源服务且不返回状态字段。"""
    client = Client()
    with patch("scp_cv.apps.dashboard.api_views.power_on_device", return_value={"device_type": "splice_screen", "action": "on"}):
        response = client.post("/api/devices/splice_screen/power/on/")

    assert response.status_code == 200
    assert response.json()["device"] == {"device_type": "splice_screen", "action": "on"}
