#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
播放器统一预热池测试，覆盖 LibreOffice bridge 生命周期保护。
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
from scp_cv.ppt_backend import PPT_BACKEND_LIBREOFFICE, PPT_BACKEND_POWERPOINT


class _BridgeStub:
    """记录关闭调用的 LibreOffice bridge 替身。"""

    def __init__(self) -> None:
        """
        初始化关闭记录。
        :return: None
        """
        self.closed = False

    def close(self) -> None:
        """
        标记 bridge 已关闭。
        :return: None
        """
        self.closed = True


class _BridgeOpenStub(_BridgeStub):
    """记录文件级 LibreOffice bridge 预热打开参数。"""

    def __init__(self, _logger: object) -> None:
        """
        初始化打开记录。
        :param _logger: 日志器
        :return: None
        """
        super().__init__()
        self.open_calls: list[tuple[str, bool]] = []
        self.preheat_called = False

    def open(self, uri: str, autoplay: bool, display_index: int = 0) -> dict[str, object]:
        """
        记录文件级打开请求。
        :param uri: PPT 文件路径
        :param autoplay: 是否自动放映
        :param display_index: 显示器序号
        :return: 空闲状态
        """
        self.open_calls.append((uri, autoplay))
        return {"playback_state": "stopped"}

    def preheat(self) -> dict[str, object]:
        """
        记录应用级预热请求。
        :return: 空闲状态
        """
        self.preheat_called = True
        return {"playback_state": "idle"}


class _PptAppsStub:
    """记录 PowerPoint/WPS 预热池调用。"""

    def __init__(self) -> None:
        """
        初始化调用记录。
        :return: None
        """
        self.preheat_calls: list[str] = []
        self.preheat_source_calls: list[tuple[str, int, str]] = []

    def preheat(self, backend: str) -> None:
        """
        记录应用级预热。
        :param backend: PPT 后端
        :return: None
        """
        self.preheat_calls.append(backend)

    def preheat_source(self, backend: str, source_id: int, uri: str) -> None:
        """
        记录文件级预热。
        :param backend: PPT 后端
        :param source_id: 媒体源 ID
        :param uri: PPT 文件路径
        :return: None
        """
        self.preheat_source_calls.append((backend, source_id, uri))


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
        self.muted = muted

    def deleteLater(self) -> None:
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
        self.audio_output = audio_output

    def setVideoOutput(self, video_output: object | None) -> None:
        self.video_output = video_output

    def setSource(self, source: object) -> None:
        self.source = source

    def stop(self) -> None:
        self.stopped = True

    def deleteLater(self) -> None:
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
        return False

    def matches(self, source_id: int, uri: str) -> bool:
        return self.source_id == source_id and self.uri == uri

    def claim(self) -> PreheatedStreamSource:
        self.claimed = True
        return PreheatedStreamSource(self.source_id, self.uri, self.instance, self.player, self.media, 10.0)

    def close(self) -> None:
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


def test_take_libreoffice_bridge_discards_expired_bridge(monkeypatch: MonkeyPatch) -> None:
    """过期的 LibreOffice 预热 bridge 不应被前台打开复用。"""
    bridge = _BridgeStub()
    pool = object.__new__(PlayerPreheatPool)
    pool._libreoffice_bridge = bridge
    pool._libreoffice_bridge_ready_at = 20.0
    monkeypatch.setattr(preheat_pool.time, "monotonic", lambda: 100.1)

    taken = pool.take_libreoffice_bridge()

    assert taken is None
    assert bridge.closed is True
    assert pool._libreoffice_bridge is None
    assert pool._libreoffice_bridge_ready_at == 0.0


def test_take_libreoffice_bridge_returns_fresh_bridge(monkeypatch: MonkeyPatch) -> None:
    """未过期的 LibreOffice 预热 bridge 仍应被前台打开认领。"""
    bridge = _BridgeStub()
    pool = object.__new__(PlayerPreheatPool)
    pool._libreoffice_bridge = bridge
    pool._libreoffice_bridge_ready_at = 50.0
    monkeypatch.setattr(preheat_pool.time, "monotonic", lambda: 100.0)

    taken = pool.take_libreoffice_bridge()

    assert taken is bridge
    assert bridge.closed is False
    assert pool._libreoffice_bridge is None
    assert pool._libreoffice_bridge_ready_at == 0.0


def test_preheat_source_uses_file_level_ppt_preheat() -> None:
    """PPT 源预热应携带 source_id/uri，进入文件级预热路径。"""
    ppt_apps = _PptAppsStub()
    pool = object.__new__(PlayerPreheatPool)
    pool._ppt_apps = ppt_apps
    pool._libreoffice_bridge = None
    pool._libreoffice_bridge_ready_at = 0.0
    pool._libreoffice_bridge_source_id = 0
    pool._libreoffice_bridge_uri = ""

    pool.preheat_source(12, SourceType.PPT, "C:/demo/source.pptx", PPT_BACKEND_POWERPOINT)

    assert ppt_apps.preheat_source_calls == [(PPT_BACKEND_POWERPOINT, 12, "C:/demo/source.pptx")]
    assert ppt_apps.preheat_calls == []


def test_preheat_libreoffice_bridge_opens_source_hidden(monkeypatch: MonkeyPatch) -> None:
    """LibreOffice 文件级预热应打开文档但不自动放映。"""
    created: list[_BridgeOpenStub] = []

    def fake_bridge_client(logger: object) -> _BridgeOpenStub:
        """
        创建 bridge 替身并记录。
        :param logger: 日志器
        :return: bridge 替身
        """
        bridge = _BridgeOpenStub(logger)
        created.append(bridge)
        return bridge

    monkeypatch.setattr(
        "scp_cv.player.adapters.ppt_libreoffice_bridge.LibreOfficeBridgeClient",
        fake_bridge_client,
    )
    pool = object.__new__(PlayerPreheatPool)
    pool._libreoffice_bridge = None
    pool._libreoffice_bridge_ready_at = 0.0
    pool._libreoffice_bridge_source_id = 0
    pool._libreoffice_bridge_uri = ""

    pool.preheat_ppt_backend(PPT_BACKEND_LIBREOFFICE, 33, "C:/demo/source.pptx")

    assert len(created) == 1
    assert created[0].open_calls == [("C:/demo/source.pptx", False)]
    assert created[0].preheat_called is False
    assert pool._libreoffice_bridge is created[0]
    assert pool._libreoffice_bridge_source_id == 33
    assert pool._libreoffice_bridge_uri == "C:/demo/source.pptx"


def test_take_libreoffice_bridge_requires_matching_file(monkeypatch: MonkeyPatch) -> None:
    """文件级 LibreOffice bridge 不应被不同源误认领。"""
    bridge = _BridgeStub()
    pool = object.__new__(PlayerPreheatPool)
    pool._libreoffice_bridge = bridge
    pool._libreoffice_bridge_ready_at = 50.0
    pool._libreoffice_bridge_source_id = 7
    pool._libreoffice_bridge_uri = "C:/demo/one.pptx"
    monkeypatch.setattr(preheat_pool.time, "monotonic", lambda: 100.0)

    taken = pool.take_libreoffice_bridge(8, "C:/demo/two.pptx")

    assert taken is None
    assert bridge.closed is True
    assert pool._libreoffice_bridge is None
    assert pool._libreoffice_bridge_source_id == 0
    assert pool._libreoffice_bridge_uri == ""


def test_take_libreoffice_bridge_returns_matching_file(monkeypatch: MonkeyPatch) -> None:
    """同源同路径的 LibreOffice 文件级 bridge 应被前台认领。"""
    bridge = _BridgeStub()
    pool = object.__new__(PlayerPreheatPool)
    pool._libreoffice_bridge = bridge
    pool._libreoffice_bridge_ready_at = 50.0
    pool._libreoffice_bridge_source_id = 7
    pool._libreoffice_bridge_uri = "C:/demo/one.pptx"
    monkeypatch.setattr(preheat_pool.time, "monotonic", lambda: 100.0)

    taken = pool.take_libreoffice_bridge(7, "C:/demo/one.pptx")

    assert taken is bridge
    assert bridge.closed is False
    assert pool._libreoffice_bridge is None
    assert pool._libreoffice_bridge_source_id == 0
    assert pool._libreoffice_bridge_uri == ""


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
