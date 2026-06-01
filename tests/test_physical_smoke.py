#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
物理冒烟测试编排与 REST API 合约测试。
@Project : SCP-cv
@File : test_physical_smoke.py
@Author : Qintsg
@Date : 2026-05-30
'''
from __future__ import annotations

import json
from pathlib import Path

import pytest
from django.test import Client

from scp_cv.apps.playback.models import (
    BackgroundAudioCommand,
    BackgroundAudioState,
    MediaSource,
    PlaybackCommand,
    PlaybackState,
    SourceType,
)
from scp_cv.ppt_backend import DEFAULT_PPT_BACKEND
from scp_cv.services import physical_smoke
from scp_cv.services.playback import get_or_create_session


@pytest.mark.django_db
def test_physical_smoke_runs_all_windows_and_source_types(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """物理冒烟编排应覆盖四窗口、所有媒体源类型与最终 reset-all。"""
    sources = _create_smoke_sources(tmp_path)
    opened: list[dict[str, object]] = []
    background_opened: list[int] = []
    background_stopped: list[bool] = []
    closed_windows: list[int] = []
    reset_calls: list[bool] = []

    def fake_open_source(
        window_id: int,
        media_source_id: int,
        autoplay: bool = True,
        ppt_backend: str | None = None,
        target_slide: int = 0,
    ) -> object:
        source = MediaSource.objects.get(pk=media_source_id)
        opened.append({
            "window_id": window_id,
            "source_type": source.source_type,
            "source_id": media_source_id,
            "autoplay": autoplay,
            "ppt_backend": ppt_backend,
            "target_slide": target_slide,
        })
        session = get_or_create_session(window_id)
        session.media_source = source
        session.playback_state = PlaybackState.PLAYING
        session.pending_command = PlaybackCommand.NONE
        session.current_slide = 1 if source.source_type == SourceType.PPT else 0
        session.save()
        return session

    def fake_play_background_audio_source(media_source_id: int) -> BackgroundAudioState:
        source = MediaSource.objects.get(pk=media_source_id)
        background_opened.append(media_source_id)
        state = BackgroundAudioState.get_instance()
        state.current_source = source
        state.playback_state = PlaybackState.PLAYING
        state.pending_command = BackgroundAudioCommand.NONE
        state.command_args = {}
        state.save()
        return state

    def fake_close_source(window_id: int) -> object:
        closed_windows.append(window_id)
        session = get_or_create_session(window_id)
        session.media_source = None
        session.playback_state = PlaybackState.IDLE
        session.pending_command = PlaybackCommand.NONE
        session.command_args = {}
        session.save()
        return session

    def fake_stop_background_audio(clear_source: bool = False) -> BackgroundAudioState:
        background_stopped.append(clear_source)
        state = BackgroundAudioState.get_instance()
        if clear_source:
            state.current_source = None
            state.playback_state = PlaybackState.IDLE
        else:
            state.playback_state = PlaybackState.STOPPED
        state.pending_command = BackgroundAudioCommand.NONE
        state.command_args = {}
        state.save()
        return state

    def fake_reset_all_sessions_to_idle() -> list[object]:
        reset_calls.append(True)
        for window_id in (1, 2, 3, 4):
            fake_close_source(window_id)
        return []

    monkeypatch.setattr(physical_smoke, "open_source", fake_open_source)
    monkeypatch.setattr(physical_smoke, "play_background_audio_source", fake_play_background_audio_source)
    monkeypatch.setattr(physical_smoke, "close_source", fake_close_source)
    monkeypatch.setattr(physical_smoke, "stop_background_audio", fake_stop_background_audio)
    monkeypatch.setattr(physical_smoke, "reset_all_sessions_to_idle", fake_reset_all_sessions_to_idle)
    monkeypatch.setattr(physical_smoke.time, "sleep", lambda _seconds: None)

    result = physical_smoke.run_physical_smoke_test(settle_seconds=0)

    assert result["success"] is True
    assert result["total_timeout_seconds"] == 540.0
    assert result["summary"] == {"total": 29, "passed": 29, "failed": 0}
    assert reset_calls == [True]
    assert len(opened) == 28
    assert len(closed_windows) >= 28
    assert background_opened == [sources[SourceType.AUDIO].pk]
    assert any(background_stopped)
    assert {item["window_id"] for item in opened} == {1, 2, 3, 4}
    assert {item["source_type"] for item in opened} == set(physical_smoke.WINDOW_SOURCE_TYPE_SEQUENCE)
    assert any(item["window_id"] == 0 and item["source_type"] == SourceType.AUDIO for item in result["results"])
    assert any(
        item["source_type"] == SourceType.PPT
        and item["ppt_backend"] == DEFAULT_PPT_BACKEND
        and item["target_slide"] == 1
        for item in opened
    )
    assert result["source_ids"] == {source_type: source.pk for source_type, source in sources.items()}


@pytest.mark.django_db
def test_physical_smoke_api_invokes_runner(monkeypatch: pytest.MonkeyPatch) -> None:
    """前端物理冒烟 API 应透传窗口、源 ID 和超时参数。"""
    captured: dict[str, object] = {}

    def fake_runner(**kwargs: object) -> dict[str, object]:
        captured.update(kwargs)
        return {
            "success": True,
            "summary": {"total": 1, "passed": 1, "failed": 0},
            "results": [],
            "reset": {"status": "ok", "elapsed": 0.1, "error_message": ""},
            "sessions": [],
        }

    monkeypatch.setattr("scp_cv.apps.dashboard.api_playback_views.run_physical_smoke_test", fake_runner)
    client = Client()

    response = client.post(
        "/api/playback/physical-smoke/",
        data=json.dumps({
            "windows": [1, 2],
            "source_ids": {"audio": 7},
            "settle_seconds": 0.2,
            "timeout_seconds": 5,
            "ppt_timeout_seconds": 9,
            "stream_timeout_seconds": 6,
            "total_timeout_seconds": 10,
            "reset_after": False,
        }),
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert captured == {
        "windows": [1, 2],
        "source_ids": {"audio": 7},
        "settle_seconds": 0.2,
        "timeout_seconds": 5.0,
        "ppt_timeout_seconds": 9.0,
        "stream_timeout_seconds": 6.0,
        "total_timeout_seconds": 10.0,
        "reset_after": False,
    }


@pytest.mark.django_db
def test_physical_smoke_api_reports_configuration_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """物理冒烟配置错误应返回稳定错误码。"""
    monkeypatch.setattr(
        "scp_cv.apps.dashboard.api_playback_views.run_physical_smoke_test",
        lambda **_kwargs: (_ for _ in ()).throw(physical_smoke.PhysicalSmokeError("缺少音频源")),
    )
    client = Client()

    response = client.post("/api/playback/physical-smoke/", data="{}", content_type="application/json")

    assert response.status_code == 400
    assert response.json()["code"] == "physical_smoke_error"


@pytest.mark.django_db
@pytest.mark.parametrize("payload", [
    {"windows": []},
    {"windows": "1"},
    {"windows": ["bad"]},
])
def test_physical_smoke_api_rejects_invalid_windows(payload: dict[str, object]) -> None:
    """显式传入空或非法窗口时不能退回全窗口执行。"""
    client = Client()

    response = client.post(
        "/api/playback/physical-smoke/",
        data=json.dumps(payload),
        content_type="application/json",
    )

    assert response.status_code == 400
    assert response.json()["code"] in {"invalid_physical_smoke_request", "physical_smoke_error"}


@pytest.mark.django_db
def test_physical_smoke_api_rejects_invalid_source_ids() -> None:
    """显式 source_ids 非法时不能静默改用自动选择的媒体源。"""
    client = Client()

    response = client.post(
        "/api/playback/physical-smoke/",
        data=json.dumps({"source_ids": {"audio": "bad"}}),
        content_type="application/json",
    )

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_physical_smoke_request"


@pytest.mark.django_db
def test_physical_smoke_total_timeout_skips_remaining_opens(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """达到全局总超时后应只记录失败项，不再打开后续源。"""
    _create_smoke_sources(tmp_path)
    clock = {"value": 100.0}
    opened_sources: list[str] = []

    def fake_run_single_source(
        window_id: int,
        source: MediaSource,
        settle_seconds: float,
        timeout_seconds: float,
        play_deadline: float,
    ) -> dict[str, object]:
        opened_sources.append(source.source_type)
        clock["value"] = play_deadline + 0.1
        return {
            "window_id": window_id,
            "source_type": source.source_type,
            "source_id": source.pk,
            "source_name": source.name,
            "status": "ok",
            "open_elapsed": 0.1,
            "close_elapsed": 0.1,
            "error_message": "",
            "open_error": "",
            "close_error": "",
        }

    monkeypatch.setattr(physical_smoke.time, "monotonic", lambda: clock["value"])
    monkeypatch.setattr(physical_smoke, "_run_single_source", fake_run_single_source)

    result = physical_smoke.run_physical_smoke_test(
        windows=[1],
        settle_seconds=0,
        total_timeout_seconds=1,
        reset_after=False,
    )

    assert opened_sources == [SourceType.IMAGE]
    assert result["success"] is False
    assert result["summary"] == {"total": 8, "passed": 1, "failed": 7}
    assert all(item["open_elapsed"] == 0.0 for item in result["results"][1:])


def _create_smoke_sources(tmp_path: Path) -> dict[str, MediaSource]:
    """
    创建覆盖全部媒体源类型的测试源。
    :param tmp_path: 临时文件目录
    :return: source_type 到 MediaSource 的映射
    """
    files = {
        SourceType.IMAGE: tmp_path / "poster.png",
        SourceType.VIDEO: tmp_path / "video.mp4",
        SourceType.AUDIO: tmp_path / "audio.wav",
        SourceType.PPT: tmp_path / "slides.pptx",
    }
    for file_path in files.values():
        file_path.write_bytes(b"fake")
    payloads = {
        SourceType.IMAGE: str(files[SourceType.IMAGE]),
        SourceType.VIDEO: str(files[SourceType.VIDEO]),
        SourceType.AUDIO: str(files[SourceType.AUDIO]),
        SourceType.WEB: "https://example.local/dashboard",
        SourceType.PPT: str(files[SourceType.PPT]),
        SourceType.SRT_STREAM: "srt://127.0.0.1:8890?streamid=read:test",
        SourceType.CUSTOM_STREAM: "srt://127.0.0.1:8890?streamid=read:custom",
        SourceType.RTSP_STREAM: "rtsp://127.0.0.1:8554/test",
    }
    return {
        source_type: MediaSource.objects.create(
            source_type=source_type,
            name=f"冒烟测试 {source_type}",
            uri=uri,
            is_available=True,
            keep_alive=True,
        )
        for source_type, uri in payloads.items()
    }
