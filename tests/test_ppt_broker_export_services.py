#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PPT 预览与放映缓存导出服务的 Broker 接线测试。
@Project : SCP-cv
@File : test_ppt_broker_export_services.py
@Author : Qintsg
@Date : 2026-07-11
'''
from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from scp_cv.player.ppt_broker import (
    PptExportResult,
    PptShowExportRequest,
    PptShowFormat,
    PptSlideExportRequest,
)
from scp_cv.services import ppt_playback_export, ppt_preview
from scp_cv.services.ppt_playback_export import PptPlaybackExportError


def test_show_cache_export_uses_broker_without_local_com(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """放映缓存导出应只向 Broker 发送文件合同并验证输出。"""
    source_path = tmp_path / "source.pptx"
    source_path.write_bytes(b"source")
    target_path = tmp_path / "source.ppsx"
    requests: list[PptShowExportRequest] = []
    timeouts: list[float] = []

    class _ClientStub:
        """记录 Broker 放映格式导出调用。"""

        def __init__(self, *, timeout_seconds: float) -> None:
            timeouts.append(timeout_seconds)

        def export_show(self, request: PptShowExportRequest) -> PptExportResult:
            requests.append(request)
            Path(request.target_uri).write_bytes(b"show")
            return PptExportResult((request.target_uri,), powerpoint_pid=4321)

    monkeypatch.setattr(
        ppt_playback_export,
        "PptBrokerClient",
        _ClientStub,
        raising=False,
    )

    backend = ppt_playback_export.export_show_file(
        source_path,
        target_path,
        ".ppsx",
    )

    assert backend == "powerpoint"
    assert target_path.read_bytes() == b"show"
    assert timeouts == [ppt_playback_export._export_timeout_seconds()]
    assert len(requests) == 1
    assert requests[0].source_uri == str(source_path)
    assert requests[0].target_uri == str(target_path)
    assert requests[0].target_format is PptShowFormat.PPSX
    assert requests[0].request_id


def test_show_cache_export_reports_unavailable_broker(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Broker 不可用时应明确失败，不能回退到本地 DispatchEx。"""

    class _ClientStub:
        def __init__(self, *, timeout_seconds: float) -> None:
            del timeout_seconds

        def export_show(self, request: PptShowExportRequest) -> PptExportResult:
            del request
            raise OSError("pipe unavailable")

    monkeypatch.setattr(
        ppt_playback_export,
        "PptBrokerClient",
        _ClientStub,
        raising=False,
    )

    with pytest.raises(PptPlaybackExportError, match="run_ppt_broker"):
        ppt_playback_export.export_show_file(
            tmp_path / "source.pptx",
            tmp_path / "source.ppsx",
            ".ppsx",
        )


def test_slide_preview_export_uses_broker_and_maps_media_urls(
    monkeypatch: pytest.MonkeyPatch,
    settings: object,
    tmp_path: Path,
) -> None:
    """逐页预览由 Broker 写文件，服务层只负责目录与媒体 URL。"""
    settings.MEDIA_ROOT = tmp_path / "media"  # type: ignore[attr-defined]
    settings.MEDIA_URL = "/media/"  # type: ignore[attr-defined]
    source_path = tmp_path / "source.pptx"
    _write_minimal_ooxml(source_path)
    requests: list[PptSlideExportRequest] = []

    class _ClientStub:
        """写出两页 PNG 的 Broker 客户端替身。"""

        def __init__(self, *, timeout_seconds: float) -> None:
            assert timeout_seconds == ppt_preview._preview_worker_timeout_seconds()

        def export_slides(self, request: PptSlideExportRequest) -> PptExportResult:
            requests.append(request)
            output_dir = Path(request.output_dir)
            paths = []
            for page_index in (1, 2):
                output_path = output_dir / f"slide-{page_index}.png"
                output_path.write_bytes(b"png")
                paths.append(str(output_path))
            return PptExportResult(tuple(paths), powerpoint_pid=4321)

    monkeypatch.setattr(ppt_preview, "PptBrokerClient", _ClientStub, raising=False)

    previews = ppt_preview.export_ppt_slide_previews(source_path, 9)

    assert previews == [
        "/media/ppt_previews/9/slide-1.png",
        "/media/ppt_previews/9/slide-2.png",
    ]
    assert len(requests) == 1
    assert requests[0].source_uri == str(source_path)
    assert requests[0].output_dir == str(
        Path(settings.MEDIA_ROOT) / "ppt_previews" / "9"  # type: ignore[attr-defined]
    )
    assert requests[0].image_format == "PNG"
    assert requests[0].request_id


def test_slide_preview_export_logs_action_when_broker_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
    settings: object,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """预览导出失败保持非阻断语义，同时给出 Broker 修复动作。"""
    settings.MEDIA_ROOT = tmp_path / "media"  # type: ignore[attr-defined]
    source_path = tmp_path / "source.pptx"
    _write_minimal_ooxml(source_path)

    class _ClientStub:
        def __init__(self, *, timeout_seconds: float) -> None:
            del timeout_seconds

        def export_slides(self, request: PptSlideExportRequest) -> PptExportResult:
            del request
            raise OSError("pipe unavailable")

    monkeypatch.setattr(ppt_preview, "PptBrokerClient", _ClientStub, raising=False)

    previews = ppt_preview.export_ppt_slide_previews(source_path, 7)

    assert previews == []
    assert "run_ppt_broker" in caplog.text


def _write_minimal_ooxml(file_path: Path) -> None:
    """写入足以通过 PPTX 候选检查的最小 ZIP。"""
    with zipfile.ZipFile(file_path, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types />")
