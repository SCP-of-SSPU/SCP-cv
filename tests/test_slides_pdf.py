#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
演示文稿 PDF 播放缓存与静态检测服务测试。
@Project : SCP-cv
@File : test_slides_pdf.py
@Author : Qintsg
@Date : 2026-08-05
'''
from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from scp_cv.apps.playback.models import MediaSource, SourceType
from scp_cv.services import slides_pdf


def _write_ooxml(file_path: Path, slide_xml: str) -> None:
    """
    写入可通过 OOXML 检测的最小演示文稿。
    :param file_path: 目标文件路径
    :param slide_xml: 第一页 slide XML
    :return: None
    """
    with zipfile.ZipFile(file_path, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types />")
        archive.writestr("ppt/slides/slide1.xml", slide_xml)
        archive.writestr("ppt/slides/_rels/slide1.xml.rels", "<Relationships />")


@pytest.mark.django_db
def test_prepare_pdf_source_sets_pdf_mode(tmp_path: Path, settings) -> None:
    """直接上传 PDF 应标记为 pdf 播放模式并保持原始 URI。"""
    settings.MEDIA_ROOT = tmp_path / "media"
    source_path = tmp_path / "slides.pdf"
    source_path.write_bytes(b"%PDF-1.4")
    source = MediaSource.objects.create(
        source_type=SourceType.PPT,
        name="直接 PDF",
        uri=str(source_path),
    )

    metadata = slides_pdf.prepare_slides_pdf(source)
    source.refresh_from_db()

    assert slides_pdf.get_slides_playback_mode(source) == "pdf"
    assert metadata[slides_pdf.SLIDES_PLAYBACK_MODE_KEY] == "pdf"
    assert slides_pdf.resolve_slide_playback_uri(source) == str(source_path)


@pytest.mark.django_db
def test_static_ooxml_prepares_pdf_cache(tmp_path: Path, settings) -> None:
    """静态 OOXML 演示文稿应自动导出 PDF 并进入 pdf 播放模式。"""
    settings.MEDIA_ROOT = tmp_path / "media"
    source_path = tmp_path / "static.pptx"
    _write_ooxml(source_path, "<p:sld xmlns:p='p'><p:cSld /></p:sld>")
    source = MediaSource.objects.create(
        source_type=SourceType.PPT,
        name="静态演示文稿",
        uri=str(source_path),
    )

    def fake_exporter(_source_path: Path, target_path: Path) -> str:
        """模拟 PowerPoint PDF 导出。"""
        target_path.write_bytes(b"pdf-cache")
        return "powerpoint"

    slides_pdf.prepare_slides_pdf(
        source,
        pdf_exporter=fake_exporter,
        static_detector=lambda _path: True,
    )
    source.refresh_from_db()

    payload = source.metadata[slides_pdf.SLIDES_PDF_METADATA_KEY]
    assert payload["status"] == "ready"
    assert slides_pdf.get_slides_playback_mode(source) == "pdf"
    assert slides_pdf.resolve_slide_playback_uri(source) == str(payload["path"])


@pytest.mark.django_db
def test_dynamic_ooxml_keeps_powerpoint_mode(tmp_path: Path, settings) -> None:
    """含动画的 OOXML 演示文稿应保持 PowerPoint 播放模式。"""
    settings.MEDIA_ROOT = tmp_path / "media"
    source_path = tmp_path / "dynamic.pptx"
    _write_ooxml(
        source_path,
        "<p:sld xmlns:p='p'><p:timing><p:tnLst /></p:timing></p:sld>",
    )
    source = MediaSource.objects.create(
        source_type=SourceType.PPT,
        name="动态演示文稿",
        uri=str(source_path),
    )

    def fake_exporter(_source_path: Path, target_path: Path) -> str:
        """模拟动态 PPT 的 PDF fallback 生成。"""
        target_path.write_bytes(b"pdf-fallback")
        return "powerpoint"

    slides_pdf.prepare_slides_pdf(source, pdf_exporter=fake_exporter)
    source.refresh_from_db()

    assert slides_pdf.get_slides_playback_mode(source) == "powerpoint"
    assert slides_pdf.get_slides_pdf_uri(source).endswith(".pdf")


def test_detect_ooxml_static_detects_timing_and_media(tmp_path: Path) -> None:
    """静态检测应识别 timing 与音视频关系。"""
    static_path = tmp_path / "static.pptx"
    _write_ooxml(static_path, "<p:sld xmlns:p='p' />")
    assert slides_pdf.detect_slides_static(static_path) is True

    dynamic_path = tmp_path / "dynamic.pptx"
    _write_ooxml(dynamic_path, "<p:sld xmlns:p='p'><p:timing /></p:sld>")
    assert slides_pdf.detect_slides_static(dynamic_path) is False

    media_path = tmp_path / "media.pptx"
    with zipfile.ZipFile(media_path, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types />")
        archive.writestr("ppt/slides/slide1.xml", "<p:sld xmlns:p='p' />")
        archive.writestr(
            "ppt/slides/_rels/slide1.xml.rels",
            """
            <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
              <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/video" Target="../media/video1.mp4" />
            </Relationships>
            """,
        )
    assert slides_pdf.detect_slides_static(media_path) is False


def test_cleanup_slides_pdf_removes_source_directory(tmp_path: Path, settings) -> None:
    """删除媒体源时应清理演示文稿 PDF 播放缓存目录。"""
    settings.MEDIA_ROOT = tmp_path / "media"
    cache_dir = settings.MEDIA_ROOT / slides_pdf.PDF_CACHE_ROOT / "42"
    cache_dir.mkdir(parents=True)
    (cache_dir / "demo.pdf").write_bytes(b"pdf")

    slides_pdf.cleanup_slides_pdf(42)

    assert not cache_dir.exists()
