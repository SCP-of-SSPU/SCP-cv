#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
播放器统一预热池测试，覆盖 PowerPoint、媒体文件和直播预热复用。
@Project : SCP-cv
@File : test_preheat_pool.py
@Author : Qintsg
@Date : 2026-05-30
'''
from __future__ import annotations

from pathlib import Path

from pytest import MonkeyPatch

from scp_cv.apps.playback.models import SourceType
from scp_cv.player import preheat_pool
from scp_cv.player.preheat_pool import PlayerPreheatPool
from scp_cv.player.preheat_types import PreheatedStreamSource


class _PptAppsStub:
    """记录 PowerPoint 预热池调用。"""

    def __init__(self) -> None:
        """
        初始化调用记录。
        :return: None
        """
        self.preheat_calls = 0
        self.preheat_source_calls: list[tuple[int, str]] = []

    def preheat(self) -> None:
        """
        记录应用级预热。
        :return: None
        """
        self.preheat_calls += 1

    def preheat_source(self, source_id: int, uri: str) -> None:
        """
        记录文件级预热。
        :param source_id: 媒体源 ID
        :param uri: PPT 文件路径
        :return: None
        """
        self.preheat_source_calls.append((source_id, uri))


class _FakePixmap:
    """QPixmap 替身，用于验证图片文件级预热键。"""

    def __init__(self, uri: str) -> None:
        """
        记录图片路径。
        :param uri: 图片路径
        :return: None
        """
        self.uri = uri

    def isNull(self) -> bool:
        """
        模拟图片加载成功。
        :return: False
        """
        return False


class _FakeAudioOutput:
    """QAudioOutput 替身。"""

    def __init__(self) -> None:
        self.deleted = False
        self.muted = False

    def setMuted(self, muted: bool) -> None:
        """
        记录静音状态。
        :param muted: 是否静音
        :return: None
        """
        self.muted = muted

    def deleteLater(self) -> None:
        """
        记录延迟删除。
        :return: None
        """
        self.deleted = True


class _FakeMediaPlayer:
    """QMediaPlayer 替身，记录文件源和释放调用。"""

    def __init__(self) -> None:
        self.audio_output: object | None = None
        self.video_output: object | None = object()
        self.source: object | None = None
        self.stopped = False
        self.deleted = False

    def setAudioOutput(self, audio_output: object | None) -> None:
        """
        记录音频输出。
        :param audio_output: 音频输出对象
        :return: None
        """
        self.audio_output = audio_output

    def setVideoOutput(self, video_output: object | None) -> None:
        """
        记录视频输出。
        :param video_output: 视频输出对象
        :return: None
        """
        self.video_output = video_output

    def setSource(self, source: object) -> None:
        """
        记录媒体源。
        :param source: QUrl 或测试替身
        :return: None
        """
        self.source = source

    def stop(self) -> None:
        """
        记录停止调用。
        :return: None
        """
        self.stopped = True

    def deleteLater(self) -> None:
        """
        记录延迟删除。
        :return: None
        """
        self.deleted = True


class _ClaimableStreamHandle:
    """可认领直播预热句柄替身。"""

    def __init__(self, source_id: int, uri: str) -> None:
        self.source_id = source_id
        self.uri = uri
        self.closed = False
        self.claimed = False
        self.instance = object()
        self.player = object()
        self.media = object()

    def is_stale(self) -> bool:
        """
        返回是否过期。
        :return: False
        """
        return False

    def matches(self, source_id: int, uri: str) -> bool:
        """
        判断源 ID 和 URI 是否匹配。
        :param source_id: 媒体源 ID
        :param uri: 媒体 URI
        :return: True 表示匹配
        """
        return self.source_id == source_id and self.uri == uri

    def claim(self) -> PreheatedStreamSource:
        """
        认领预热直播资源。
        :return: 已预热直播资源
        """
        self.claimed = True
        return PreheatedStreamSource(self.source_id, self.uri, self.instance, self.player, self.media, 10.0)

    def close(self) -> None:
        """
        记录关闭调用。
        :return: None
        """
        self.closed = True


class _FakeQUrl:
    """QUrl 替身。"""

    @staticmethod
    def fromLocalFile(uri: str) -> str:
        """
        返回可断言的本地文件 URL 标记。
        :param uri: 本地文件路径
        :return: 标记字符串
        """
        return f"local:{uri}"


def test_ppt_sources_share_application_level_preheat() -> None:
    """PowerPoint 是进程级单例；多个 PPT 源只能共享应用级预热，不能长期持有文件 COM 代理。"""
    ppt_apps = _PptAppsStub()
    pool = object.__new__(PlayerPreheatPool)
    pool._ppt_apps = ppt_apps
    pool._ppt_com_worker = None

    pool.preheat_source(12, SourceType.PPT, "C:/demo/source.pptx")
    pool.preheat_source(13, SourceType.PPT, "C:/demo/other.pptx")

    assert ppt_apps.preheat_source_calls == []
    assert ppt_apps.preheat_calls == 2


def test_image_preheat_is_file_level_and_requires_exact_uri(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    """图片预热应按 source_id + uri 精确复用，避免同 ID 换文件误用旧缓存。"""
    monkeypatch.setattr(preheat_pool, "QPixmap", _FakePixmap)
    image_path = tmp_path / "screen.png"
    image_path.write_bytes(b"fake-image")
    pool = object.__new__(PlayerPreheatPool)
    pool._images = {}

    pool.preheat_source(101, SourceType.IMAGE, str(image_path))
    missed = pool.take_image(101, str(tmp_path / "changed.png"))
    pool.preheat_source(101, SourceType.IMAGE, str(image_path), force=True)
    pixmap = pool.take_image(101, str(image_path))

    assert missed is None
    assert isinstance(pixmap, _FakePixmap)
    assert pixmap.uri == str(image_path)


def test_video_preheat_is_file_level_and_requires_exact_uri(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    """视频预热应保存已设置文件源的播放器，并拒绝不同 uri 的认领。"""
    monkeypatch.setattr(preheat_pool, "QAudioOutput", _FakeAudioOutput)
    monkeypatch.setattr(preheat_pool, "QMediaPlayer", _FakeMediaPlayer)
    monkeypatch.setattr(preheat_pool, "QUrl", _FakeQUrl)
    video_path = tmp_path / "clip.mp4"
    video_path.write_bytes(b"fake-video")
    pool = object.__new__(PlayerPreheatPool)
    pool._videos = {}

    pool.preheat_source(202, SourceType.VIDEO, str(video_path))
    wrong_take = pool.take_video(202, str(tmp_path / "changed.mp4"))
    pool.preheat_source(202, SourceType.VIDEO, str(video_path), force=True)
    preheated = pool.take_video(202, str(video_path))

    assert wrong_take is None
    assert preheated is not None
    assert isinstance(preheated.player, _FakeMediaPlayer)
    assert preheated.player.source == f"local:{video_path}"
    assert isinstance(preheated.audio_output, _FakeAudioOutput)


def test_audio_preheat_is_file_level_and_requires_exact_uri(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    """背景音频预热应保存已设置文件源的播放器，并拒绝不同 uri 的认领。"""
    monkeypatch.setattr(preheat_pool, "QAudioOutput", _FakeAudioOutput)
    monkeypatch.setattr(preheat_pool, "QMediaPlayer", _FakeMediaPlayer)
    monkeypatch.setattr(preheat_pool, "QUrl", _FakeQUrl)
    audio_path = tmp_path / "music.mp3"
    audio_path.write_bytes(b"fake-audio")
    pool = object.__new__(PlayerPreheatPool)
    pool._audios = {}

    pool.preheat_source(404, SourceType.AUDIO, str(audio_path))
    wrong_take = pool.take_audio(404, str(tmp_path / "changed.mp3"))
    pool.preheat_source(404, SourceType.AUDIO, str(audio_path), force=True)
    preheated = pool.take_audio(404, str(audio_path))

    assert wrong_take is None
    assert preheated is not None
    assert isinstance(preheated.player, _FakeMediaPlayer)
    assert preheated.player.source == f"local:{audio_path}"
    assert isinstance(preheated.audio_output, _FakeAudioOutput)


def test_take_stream_claims_matching_uri() -> None:
    """同源同 URI 的直播预热句柄应被前台认领，而不是关闭后重建。"""
    handle = _ClaimableStreamHandle(303, "rtsp://127.0.0.1/live")
    pool = object.__new__(PlayerPreheatPool)
    pool._streams = {303: handle}

    claimed = pool.take_stream(303, "rtsp://127.0.0.1/live")

    assert claimed is not None
    assert claimed.player is handle.player
    assert claimed.media is handle.media
    assert handle.claimed is True
    assert handle.closed is False
    assert pool._streams == {}


def test_before_open_keeps_stream_preheat_for_claim() -> None:
    """打开直播源前不应提前停止后台预热，前台 adapter 需要先尝试认领。"""
    closed: list[int] = []

    class _StreamHandle:
        """记录关闭调用的直播预热句柄。"""

        def close(self) -> None:
            """
            记录关闭。
            :return: None
            """
            closed.append(303)

    pool = object.__new__(PlayerPreheatPool)
    pool._streams = {303: _StreamHandle()}

    pool.before_open(303, SourceType.SRT_STREAM)

    assert closed == []
    assert 303 in pool._streams
