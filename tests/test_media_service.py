#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
媒体源管理服务 (media.py) 单元测试。
覆盖源类型检测、上传添加、本地路径注册、列表查询、删除等功能。
@Project : SCP-cv
@File : test_media_service.py
@Author : Qintsg
@Date : 2026-04-14
'''
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from scp_cv.apps.playback.models import MediaSource, SourceType
from scp_cv.services.media import (
    MediaError,
    add_local_path,
    add_uploaded_file,
    delete_media_source,
    detect_source_type,
    list_media_sources,
    normalize_web_url,
    sync_streams_to_media_sources,
)

import os


# ══════════════════════════════════════════════════════════════
# detect_source_type — 纯函数，无需数据库
# ══════════════════════════════════════════════════════════════

class TestDetectSourceType:
    """测试文件扩展名到源类型的检测逻辑。"""

    @pytest.mark.parametrize("file_path,expected_type", [
        ("demo.pptx", SourceType.PPT),
        ("SLIDE.PPT", SourceType.PPT),
        ("show.ppsx", SourceType.PPT),
        ("movie.mp4", SourceType.VIDEO),
        ("clip.mkv", SourceType.VIDEO),
        ("song.mp3", SourceType.AUDIO),
        ("track.flac", SourceType.AUDIO),
        ("photo.png", SourceType.IMAGE),
        ("pic.jpeg", SourceType.IMAGE),
        ("icon.svg", SourceType.IMAGE),
    ])
    def test_known_extensions(self, file_path: str, expected_type: str) -> None:
        """已知扩展名应返回正确的 SourceType。"""
        assert detect_source_type(file_path) == expected_type

    def test_case_insensitive(self) -> None:
        """扩展名检测应大小写无关。"""
        assert detect_source_type("FILE.MP4") == SourceType.VIDEO
        assert detect_source_type("FILE.Mp4") == SourceType.VIDEO

    def test_unknown_extension_raises(self) -> None:
        """未知扩展名应抛出 MediaError。"""
        with pytest.raises(MediaError, match="无法识别"):
            detect_source_type("readme.txt")

    def test_no_extension_raises(self) -> None:
        """无扩展名文件应抛出 MediaError。"""
        with pytest.raises(MediaError, match="无法识别"):
            detect_source_type("noext")

    def test_path_with_directories(self) -> None:
        """包含目录的路径应只依据文件名扩展名判断。"""
        assert detect_source_type("C:/videos/deep/dir/movie.avi") == SourceType.VIDEO


# ══════════════════════════════════════════════════════════════
# add_uploaded_file
# ══════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestAddUploadedFile:
    """测试通过文件上传添加媒体源。"""

    def test_upload_auto_detect_type(self) -> None:
        """上传 pptx 文件应自动检测为 PPT 类型。"""
        fake_file = SimpleUploadedFile("演示.pptx", b"fake-pptx-content")
        source = add_uploaded_file(fake_file)

        assert source.pk is not None
        assert source.source_type == SourceType.PPT
        assert source.name == "演示"
        assert source.uri != ""
        assert MediaSource.objects.count() == 1

    def test_upload_with_custom_name(self) -> None:
        """上传时传入自定义名称应覆盖默认文件名。"""
        fake_file = SimpleUploadedFile("video.mp4", b"fake-mp4")
        source = add_uploaded_file(fake_file, display_name="自定义视频")

        assert source.name == "自定义视频"
        assert source.source_type == SourceType.VIDEO

    def test_upload_with_explicit_type(self) -> None:
        """显式指定源类型应跳过自动检测。"""
        fake_file = SimpleUploadedFile("data.bin", b"binary-data")
        source = add_uploaded_file(fake_file, source_type=SourceType.VIDEO)

        assert source.source_type == SourceType.VIDEO

    def test_upload_unknown_type_raises(self) -> None:
        """上传无法识别类型的文件应抛出 MediaError。"""
        fake_file = SimpleUploadedFile("readme.txt", b"text-content")
        with pytest.raises(MediaError, match="无法识别"):
            add_uploaded_file(fake_file)


# ══════════════════════════════════════════════════════════════
# add_local_path
# ══════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestAddLocalPath:
    """测试通过本地路径注册媒体源。"""

    def test_add_existing_file(self, tmp_path: Path) -> None:
        """注册已存在的本地文件应成功创建源。"""
        video_file = tmp_path / "测试视频.mp4"
        video_file.write_bytes(b"fake-video-data")

        source = add_local_path(str(video_file))

        assert source.pk is not None
        assert source.source_type == SourceType.VIDEO
        assert source.name == "测试视频"
        assert source.is_available is True
        assert str(video_file.resolve()) in source.uri

    def test_add_with_custom_name_and_type(self, tmp_path: Path) -> None:
        """传入自定义名称和类型应覆盖自动检测。"""
        ppt_file = tmp_path / "file.pptx"
        ppt_file.write_bytes(b"fake-pptx")

        source = add_local_path(str(ppt_file), display_name="年度汇报", source_type=SourceType.PPT)

        assert source.name == "年度汇报"
        assert source.source_type == SourceType.PPT

    def test_nonexistent_file_raises(self) -> None:
        """注册不存在的文件路径应抛出 MediaError。"""
        with pytest.raises(MediaError, match="文件不存在"):
            add_local_path("Z:/不存在的路径/missing.mp4")

    def test_unknown_extension_raises(self, tmp_path: Path) -> None:
        """注册无法识别扩展名的文件应抛出 MediaError。"""
        unknown_file = tmp_path / "config.yml"
        unknown_file.write_text("key: value", encoding="utf-8")

        with pytest.raises(MediaError, match="无法识别"):
            add_local_path(str(unknown_file))


# ══════════════════════════════════════════════════════════════
# normalize_web_url / add_web_url
# ══════════════════════════════════════════════════════════════

class TestWebUrlNormalization:
    """测试网页源 URL 规范化规则。"""

    def test_default_protocol_is_http(self) -> None:
        """未填写协议的局域网地址应默认使用 http。"""
        assert normalize_web_url("192.168.1.20:3000") == "http://192.168.1.20:3000"

    def test_keeps_existing_protocol(self) -> None:
        """显式协议应保持不变。"""
        assert normalize_web_url("https://example.com") == "https://example.com"

    def test_windows_path_uses_file_protocol(self) -> None:
        """Windows 本地路径应转成 file URL。"""
        assert normalize_web_url("D:/demo/index.html") == "file:///D:/demo/index.html"


@pytest.mark.django_db
def test_add_web_url_stores_normalized_http_url() -> None:
    """添加网页源时应保存规范化后的局域网 URL。"""
    from scp_cv.services.media import add_web_url

    source = add_web_url("192.168.1.20:3000", display_name="内网页面")

    assert source.source_type == SourceType.WEB
    assert source.uri == "http://192.168.1.20:3000"


# ══════════════════════════════════════════════════════════════
# list_media_sources
# ══════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestListMediaSources:
    """测试媒体源列表查询。"""

    def test_empty_list(self) -> None:
        """无媒体源时应返回空列表。"""
        assert list_media_sources() == []

    def test_list_all(self, media_source_ppt: MediaSource, media_source_video: MediaSource) -> None:
        """应返回所有媒体源。"""
        sources = list_media_sources()
        assert len(sources) == 2

    def test_filter_by_type(self, media_source_ppt: MediaSource, media_source_video: MediaSource) -> None:
        """按类型过滤应只返回匹配的源。"""
        ppt_sources = list_media_sources(source_type=SourceType.PPT)
        assert len(ppt_sources) == 1
        assert ppt_sources[0]["source_type"] == SourceType.PPT

    def test_returned_dict_keys(self, media_source_ppt: MediaSource) -> None:
        """返回字典应包含所有必要字段。"""
        sources = list_media_sources()
        assert len(sources) == 1
        expected_keys = {
            "id", "source_type", "name", "uri", "is_available", "stream_identifier", "created_at",
            "folder_id", "original_filename", "file_size", "mime_type", "is_temporary",
            "expires_at", "metadata",
        }
        assert set(sources[0].keys()) == expected_keys


# ══════════════════════════════════════════════════════════════
# delete_media_source
# ══════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestDeleteMediaSource:
    """测试媒体源删除。"""

    def test_delete_existing(self, media_source_ppt: MediaSource) -> None:
        """删除已有源应成功移除数据库记录。"""
        source_id = media_source_ppt.pk
        delete_media_source(source_id)
        assert MediaSource.objects.filter(pk=source_id).count() == 0

    def test_delete_nonexistent_raises(self) -> None:
        """删除不存在的 id 应抛出 MediaError。"""
        with pytest.raises(MediaError, match="不存在"):
            delete_media_source(99999)

    def test_delete_removes_uploaded_file(self, tmp_path: Path) -> None:
        """删除包含上传文件的源应同时删除物理文件。"""
        fake_file = tmp_path / "uploaded.mp4"
        fake_file.write_bytes(b"video-content")

        # 通过 SimpleUploadedFile 正常走上传流程，生成带 FileField 的源
        uploaded = SimpleUploadedFile("uploaded.mp4", b"video-content")
        source = add_uploaded_file(uploaded, display_name="带文件视频")
        real_path = source.uploaded_file.path

        # 确认文件存在
        assert os.path.isfile(real_path)

        delete_media_source(source.pk)

        assert not os.path.isfile(real_path), "物理文件应被删除"


# ══════════════════════════════════════════════════════════════
# sync_streams_to_media_sources
# ══════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestSyncStreamsToMediaSources:
    """测试流状态同步到媒体源。"""

    @patch("scp_cv.services.mediamtx.get_srt_read_url", return_value="srt://127.0.0.1:8890?streamid=read:test-stream&latency=30000")
    def test_creates_new_source_for_online_stream(self, mock_srt_url: MagicMock) -> None:
        """在线的新流应创建对应的 MediaSource。"""
        from scp_cv.apps.streams.models import StreamSource

        StreamSource.objects.create(
            stream_identifier="test-stream",
            name="测试流",
            is_online=True,
        )

        counts = sync_streams_to_media_sources()

        assert counts["created"] == 1
        created_source = MediaSource.objects.get(stream_identifier="test-stream")
        assert created_source.source_type == SourceType.SRT_STREAM
        assert created_source.is_available is True
        assert created_source.uri == "srt://127.0.0.1:8890?streamid=read:test-stream&latency=30000"

    @patch("scp_cv.services.mediamtx.get_srt_read_url", return_value="srt://127.0.0.1:8890?streamid=read:test-stream&latency=30000")
    def test_marks_offline_streams_unavailable(self, mock_srt_url: MagicMock) -> None:
        """流离线后，对应的 MediaSource 应标记为不可用。"""
        # 预先创建一个 RTSP 源（模拟之前在线）
        MediaSource.objects.create(
            source_type=SourceType.RTSP_STREAM,
            name="旧流",
            uri="rtsp://127.0.0.1:8554/gone-stream",
            stream_identifier="gone-stream",
            is_available=True,
        )

        counts = sync_streams_to_media_sources()

        assert counts["removed"] == 1
        offline_source = MediaSource.objects.get(stream_identifier="gone-stream")
        assert offline_source.is_available is False
