#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PPT 放映格式缓存服务测试。
@Project : SCP-cv
@File : test_ppt_playback_cache.py
@Author : Qintsg
@Date : 2026-05-31
'''
from __future__ import annotations

from pathlib import Path
import zipfile

import pytest

from scp_cv.apps.playback.models import MediaSource, SourceType
from scp_cv.services import ppt_playback_cache
from scp_cv.services.ppt_playback_cache import (
    PPT_PLAYBACK_METADATA_KEY,
    cleanup_ppt_playback_cache,
    prepare_ppt_playback_cache,
    resolve_ppt_playback_uri,
)


@pytest.mark.django_db
def test_prepare_pptx_playback_cache_writes_ready_metadata(
    tmp_path: Path,
    settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """合法 OOXML PPT 应导出为 .ppsx 并写入 ready metadata。"""
    settings.MEDIA_ROOT = tmp_path / "media"
    source_path = tmp_path / "demo.pptx"
    _write_minimal_ooxml(source_path)
    source = MediaSource.objects.create(
        source_type=SourceType.PPT,
        name="演示文稿",
        uri=str(source_path),
        is_available=True,
    )

    def fake_export(
        exported_source_path: Path,
        target_path: Path,
        target_extension: str,
    ) -> str:
        """模拟 Office 导出。"""
        assert exported_source_path == source_path
        assert target_extension == ".ppsx"
        target_path.write_bytes(b"show-cache")
        return "powerpoint"

    monkeypatch.setattr(ppt_playback_cache, "export_show_file", fake_export)

    payload = prepare_ppt_playback_cache(source)
    source.refresh_from_db()

    assert payload["status"] == "ready"
    assert payload["backend"] == "powerpoint"
    assert payload["format"] == "ppsx"
    assert payload["original_extension"] == ".pptx"
    assert Path(str(payload["path"])).is_file()
    assert resolve_ppt_playback_uri(source) == str(payload["path"])
    assert source.metadata[PPT_PLAYBACK_METADATA_KEY]["status"] == "ready"


@pytest.mark.django_db
def test_prepare_legacy_ppt_playback_cache_targets_pps(
    tmp_path: Path,
    settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """旧版 .ppt 应导出为 .pps。"""
    settings.MEDIA_ROOT = tmp_path / "media"
    source_path = tmp_path / "legacy.ppt"
    source_path.write_bytes(b"legacy-ppt")
    source = MediaSource.objects.create(source_type=SourceType.PPT, name="旧版", uri=str(source_path))

    def fake_export(
        _source_path: Path,
        target_path: Path,
        target_extension: str,
    ) -> str:
        """模拟旧版 PPT 导出。"""
        assert target_extension == ".pps"
        target_path.write_bytes(b"legacy-show")
        return "powerpoint"

    monkeypatch.setattr(ppt_playback_cache, "export_show_file", fake_export)

    payload = prepare_ppt_playback_cache(source)

    assert payload["status"] == "ready"
    assert payload["format"] == "pps"
    assert str(payload["path"]).endswith(".pps")


@pytest.mark.django_db
def test_invalid_pptx_marks_failed_without_export(
    tmp_path: Path,
    settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """伪 PPTX 不应启动 Office 导出，并应保留原始 URI 回退。"""
    settings.MEDIA_ROOT = tmp_path / "media"
    source_path = tmp_path / "broken.pptx"
    source_path.write_bytes(b"not-a-zip")
    source = MediaSource.objects.create(source_type=SourceType.PPT, name="损坏文件", uri=str(source_path))
    export_calls: list[bool] = []

    def fake_export(*_args: object, **_kwargs: object) -> str:
        """不应被调用。"""
        export_calls.append(True)
        return "powerpoint"

    monkeypatch.setattr(ppt_playback_cache, "export_show_file", fake_export)

    payload = prepare_ppt_playback_cache(source)
    source.refresh_from_db()

    assert payload["status"] == "failed"
    assert export_calls == []
    assert "不适合自动导出" in str(payload["error"])
    assert resolve_ppt_playback_uri(source) == str(source_path)


@pytest.mark.django_db
def test_resolve_ppt_playback_uri_falls_back_when_cache_missing(tmp_path: Path) -> None:
    """metadata 指向的缓存不存在时应回退到原始 URI。"""
    source_path = tmp_path / "demo.pptx"
    _write_minimal_ooxml(source_path)
    missing_cache = tmp_path / "missing.ppsx"
    source = MediaSource.objects.create(
        source_type=SourceType.PPT,
        name="演示文稿",
        uri=str(source_path),
        metadata={
            PPT_PLAYBACK_METADATA_KEY: {
                "status": "ready",
                "path": str(missing_cache),
            },
        },
    )

    assert resolve_ppt_playback_uri(source) == str(source_path)


def test_cleanup_ppt_playback_cache_removes_source_directory(tmp_path: Path, settings) -> None:
    """删除媒体源时应清理对应 PPT 放映缓存目录。"""
    settings.MEDIA_ROOT = tmp_path / "media"
    cache_dir = settings.MEDIA_ROOT / "ppt_playback" / "42"
    cache_dir.mkdir(parents=True)
    (cache_dir / "demo.ppsx").write_bytes(b"cache")

    cleanup_ppt_playback_cache(42)

    assert not cache_dir.exists()


def _write_minimal_ooxml(file_path: Path) -> None:
    """
    写入足够通过 OOXML 候选校验的最小 zip 文件。

    :param file_path: 目标文件路径
    :return: None
    """
    with zipfile.ZipFile(file_path, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types />")
