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

from django.core.files.uploadedfile import SimpleUploadedFile

import pytest
from django.test import Client

from scp_cv.apps.playback.models import MediaSource, PlaybackCommand, PlaybackSession, Scenario, SourceType
from scp_cv.services.playback import RESET_ALL_WINDOWS_ARG, get_or_create_session


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
    source_payload = next(source for source in payload["sources"] if source["id"] == media_source_ppt.pk)
    assert "ppt_backend" not in source_payload
    assert "preview_url" in source_payload
    assert "thumbnail_url" in source_payload


@pytest.mark.django_db
def test_upload_source_api_stores_preheat_flag() -> None:
    """POST /api/sources/upload/ 应保存上传文件源预热开关。"""
    client = Client()
    uploaded_file = SimpleUploadedFile("video.mp4", b"fake-mp4", content_type="video/mp4")

    response = client.post(
        "/api/sources/upload/",
        data={"file": uploaded_file, "preheat_enabled": "false"},
    )

    assert response.status_code == 201
    source = MediaSource.objects.get(pk=response.json()["source"]["id"])
    assert source.keep_alive is False
    assert response.json()["source"]["preheat_enabled"] is False


@pytest.mark.django_db
def test_add_local_source_api_stores_preheat_flag(tmp_path: Path) -> None:
    """POST /api/sources/local/ 应保存本地文件源预热开关。"""
    client = Client()
    video_file = tmp_path / "local.mp4"
    video_file.write_bytes(b"fake-mp4")

    response = client.post(
        "/api/sources/local/",
        data={"path": str(video_file), "preheat_enabled": False},
        content_type="application/json",
    )

    assert response.status_code == 201
    source = MediaSource.objects.get(pk=response.json()["source"]["id"])
    assert source.keep_alive is False
    assert response.json()["source"]["preheat_enabled"] is False


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


@pytest.mark.django_db
def test_playback_open_api_ignores_unknown_ppt_backend(media_source_ppt: MediaSource) -> None:
    """POST /api/playback/{window}/open/ 应忽略旧 ppt_backend 字段。"""
    client = Client()

    response = client.post(
        "/api/playback/1/open/",
        data={"source_id": media_source_ppt.pk, "autoplay": True, "ppt_backend": "wps"},
        content_type="application/json",
    )

    assert response.status_code == 200
    session = PlaybackSession.objects.get(window_id=1)
    assert session.media_source_id == media_source_ppt.pk
    assert "ppt_backend" not in session.command_args


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
    session = get_or_create_session(1)
    session.error_message = "播放器无法连接直播源"
    session.save(update_fields=["error_message"])

    response = client.get("/api/sessions/")

    assert response.status_code == 200
    assert [item["window_id"] for item in response.json()["sessions"]] == [1, 2, 3, 4]
    assert response.json()["sessions"][0]["error_message"] == "播放器无法连接直播源"


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


@pytest.mark.django_db
def test_shutdown_system_api_requests_close_and_marks_signal(
    media_source_ppt: MediaSource,
    settings,
    tmp_path: Path,
) -> None:
    """POST /api/system/shutdown/ 应写入关闭信号并返回待机态会话。"""
    settings.LOG_DIR = tmp_path / "logs"
    settings.LOG_DIR.mkdir(parents=True, exist_ok=True)
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


@pytest.mark.django_db
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
def test_scenarios_pin_api_toggles_sort_order() -> None:
    """POST /api/scenarios/{id}/pin/ 应支持置顶和取消置顶。"""
    client = Client()
    scenario = Scenario.objects.create(name="置顶切换预案")

    pin_response = client.post(f"/api/scenarios/{scenario.pk}/pin/")
    unpin_response = client.post(f"/api/scenarios/{scenario.pk}/pin/")

    assert pin_response.status_code == 200
    assert pin_response.json()["scenario"]["sort_order"] > 0
    assert unpin_response.status_code == 200
    assert unpin_response.json()["scenario"]["sort_order"] == 0


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
def test_source_preview_api_returns_inline_file(tmp_path: Path) -> None:
    """GET /api/sources/{id}/preview/ 应返回图片/视频的 inline 预览文件。"""
    image_file = tmp_path / "poster.png"
    image_file.write_bytes(b"fake-image")
    source = MediaSource.objects.create(
        source_type=SourceType.IMAGE,
        name="海报",
        uri=str(image_file),
        mime_type="image/png",
    )
    client = Client()

    response = client.get(f"/api/sources/{source.pk}/preview/")

    assert response.status_code == 200
    assert response["Content-Type"] == "image/png"


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


@pytest.mark.django_db
def test_switch_ppt_backend_api_is_removed(media_source_ppt: MediaSource) -> None:
    """PPT 后端切换 API 已移除。"""
    client = Client()
    client.post(
        "/api/playback/1/open/",
        data={"source_id": media_source_ppt.pk, "autoplay": True},
        content_type="application/json",
    )

    response = client.post(
        "/api/playback/1/ppt-backend/",
        data={"ppt_backend": "wps"},
        content_type="application/json",
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_reset_ppt_playback_api_requests_ppt_reset(media_source_ppt: MediaSource) -> None:
    """POST /api/playback/reset-ppt/ 应下发 PPT 重置指令并保留页码。"""
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
    assert session.pending_command == PlaybackCommand.RESET_PPT
    assert session.command_args["restart_sessions"][0]["target_slide"] == 6
    assert "reset_token" in session.command_args
    assert "ppt_backend" not in session.command_args["restart_sessions"][0]


@pytest.mark.django_db
def test_device_power_api_uses_tcp_service() -> None:
    """电源 API 应调用 TCP 电源服务且不返回状态字段。"""
    client = Client()
    with patch("scp_cv.apps.dashboard.api_views.power_on_device", return_value={"device_type": "splice_screen", "action": "on"}):
        response = client.post("/api/devices/splice_screen/power/on/")

    assert response.status_code == 200
    assert response.json()["device"] == {"device_type": "splice_screen", "action": "on"}
