#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
SRT 直播适配器测试，覆盖首帧错误宽限状态。
@Project : SCP-cv
@File : test_srt_stream_adapter.py
@Author : Qintsg
@Date : 2026-05-07
'''
from __future__ import annotations

from pytest import MonkeyPatch

from scp_cv.player.adapters import create_adapter
from scp_cv.player.adapters import srt_stream
from scp_cv.player.adapters.srt_stream import SrtStreamAdapter, _build_srt_media_options, _build_vlc_instance_args
from scp_cv.player.preheat_stream import _stream_media_options
from scp_cv.player.preheat_types import PreheatedStreamSource
from scp_cv.services.mediamtx import get_srt_read_url


class _FakeVlcState:
    """libVLC 状态枚举替身。"""

    Error = "error"
    Playing = "playing"
    Paused = "paused"
    Opening = "opening"
    Buffering = "buffering"
    Stopped = "stopped"
    Ended = "ended"


class _FakeVlc:
    """libVLC 模块替身，仅暴露 get_state 需要的 State。"""

    State = _FakeVlcState

    class EventType:
        """libVLC 事件枚举替身。"""

        MediaPlayerPlaying = "playing"
        MediaPlayerEncounteredError = "error"
        MediaPlayerStopped = "stopped"
        MediaPlayerEndReached = "ended"


class _FakePlayer:
    """libVLC player 替身，返回固定播放状态。"""

    def __init__(self, playback_state: str) -> None:
        """
        初始化播放器替身。
        :param playback_state: 固定返回的 libVLC 状态
        :return: None
        """
        self.playback_state = playback_state
        self.hwnds: list[int] = []
        self.play_calls = 0
        self.mute_calls: list[bool] = []

    def set_hwnd(self, hwnd: int) -> None:
        self.hwnds.append(hwnd)

    def event_manager(self) -> object:
        class _EventManager:
            def event_attach(self, _event_type: object, _callback: object) -> None:
                return None

        return _EventManager()

    def play(self) -> int:
        self.play_calls += 1
        return 0

    def audio_set_mute(self, muted: bool) -> None:
        self.mute_calls.append(muted)

    def get_state(self) -> str:
        """
        返回固定 libVLC 状态。
        :return: libVLC 状态字符串
        """
        return self.playback_state

    def get_time(self) -> int:
        """
        返回直播流未知当前位置。
        :return: 当前位置毫秒
        """
        return 0

    def get_length(self) -> int:
        """
        返回直播流未知总时长。
        :return: 总时长毫秒
        """
        return 0


def _install_fake_vlc(monkeypatch: MonkeyPatch, monotonic_now: float) -> None:
    """
    安装 libVLC 与单调时钟替身。
    :param monkeypatch: pytest monkeypatch fixture
    :param monotonic_now: 当前单调时钟值
    :return: None
    """
    monkeypatch.setattr(srt_stream, "vlc", _FakeVlc)
    monkeypatch.setattr(srt_stream.time, "monotonic", lambda: monotonic_now)


def test_srt_error_in_grace_period_reports_loading(monkeypatch: MonkeyPatch) -> None:
    """首帧宽限期内的 libVLC Error 应继续表现为 loading。"""
    _install_fake_vlc(monkeypatch, monotonic_now=12.0)
    adapter = SrtStreamAdapter()
    adapter._player = _FakePlayer(_FakeVlcState.Error)
    adapter._opened_at_monotonic = 10.0

    adapter_state = adapter.get_state()

    assert adapter_state.playback_state == "loading"


def test_srt_error_after_grace_period_reports_error(monkeypatch: MonkeyPatch) -> None:
    """超过宽限期后持续错误应正式上报 error。"""
    _install_fake_vlc(monkeypatch, monotonic_now=20.0)
    adapter = SrtStreamAdapter()
    adapter._player = _FakePlayer(_FakeVlcState.Error)
    adapter._has_error = True
    adapter._error_message = "libVLC 播放 SRT 流失败"
    adapter._last_error_at_monotonic = 10.0

    adapter_state = adapter.get_state()

    assert adapter_state.playback_state == "error"
    assert adapter_state.error_message == "libVLC 播放 SRT 流失败"


def test_srt_read_url_uses_player_side_low_latency() -> None:
    """播放器 SRT 读端 URL 应使用毫秒级低延迟参数。"""
    read_url = get_srt_read_url("live-room")

    assert read_url == "srt://127.0.0.1:8890?streamid=read:live-room&latency=50"


def test_srt_adapter_uses_low_latency_vlc_options() -> None:
    """SRT 前台播放适配器应使用低缓存、追实时画面的 libVLC 参数。"""
    instance_args = _build_vlc_instance_args()
    media_options = _build_srt_media_options()

    assert "--network-caching=50" in instance_args
    assert "--live-caching=50" in instance_args
    assert "--clock-jitter=0" in instance_args
    assert "--clock-synchro=0" in instance_args
    assert "--drop-late-frames" in instance_args
    assert "--skip-frames" in instance_args
    assert ":network-caching=50" in media_options
    assert ":live-caching=50" in media_options
    assert ":drop-late-frames" in media_options
    assert ":skip-frames" in media_options
    assert ":rtsp-tcp" in media_options


def test_srt_adapter_uses_configured_vlc_options(settings: object) -> None:
    """直播 libVLC cache 参数应允许通过 settings 覆盖。"""
    settings.STREAM_VLC_NETWORK_CACHING_MS = 80
    settings.STREAM_VLC_LIVE_CACHING_MS = 90
    settings.STREAM_VLC_FILE_CACHING_MS = 10
    settings.STREAM_VLC_CLOCK_JITTER = 1
    settings.STREAM_VLC_CLOCK_SYNCHRO = 1
    settings.STREAM_VLC_DROP_LATE_FRAMES = False
    settings.STREAM_VLC_SKIP_FRAMES = False

    instance_args = _build_vlc_instance_args()
    media_options = _build_srt_media_options()

    assert "--network-caching=80" in instance_args
    assert "--live-caching=90" in instance_args
    assert "--file-caching=10" in instance_args
    assert "--clock-jitter=1" in instance_args
    assert "--clock-synchro=1" in instance_args
    assert "--drop-late-frames" not in instance_args
    assert "--skip-frames" not in instance_args
    assert ":network-caching=80" in media_options
    assert ":live-caching=90" in media_options


def test_srt_adapter_honors_configured_rtsp_transport(settings: object) -> None:
    """RTSP 传输方式应通过 settings 转换为 libVLC media option。"""
    settings.MEDIAMTX_RTSP_READ_TRANSPORT = "udp"

    media_options = _build_srt_media_options()

    assert ":rtsp-udp" in media_options
    assert ":rtsp-tcp" not in media_options


def test_stream_preheat_uses_bounded_low_cache_options() -> None:
    """直播预连接应使用有界低缓存，避免后台读端累积大量延迟。"""
    media_options = _stream_media_options()

    assert ":network-caching=100" in media_options
    assert ":live-caching=100" in media_options
    assert ":clock-jitter=0" in media_options
    assert ":clock-synchro=0" in media_options
    assert ":rtsp-tcp" in media_options


def test_srt_adapter_reuses_claimed_preheated_stream(monkeypatch: MonkeyPatch) -> None:
    """前台 SRT/RTSP adapter 应能复用预热好的 libVLC player/media。"""
    _install_fake_vlc(monkeypatch, monotonic_now=20.0)
    fake_player = _FakePlayer(_FakeVlcState.Playing)
    fake_instance = object()
    fake_media = object()
    preheated = PreheatedStreamSource(9, "rtsp://127.0.0.1/live", fake_instance, fake_player, fake_media, 10.0)

    class _PreheatPool:
        def __init__(self) -> None:
            self.calls: list[tuple[int, str]] = []

        def take_stream(self, source_id: int, uri: str) -> PreheatedStreamSource:
            self.calls.append((source_id, uri))
            return preheated

    pool = _PreheatPool()
    adapter = SrtStreamAdapter()
    adapter.set_preheat_context(9, True, pool)

    adapter.open("rtsp://127.0.0.1/live", window_handle=1234, autoplay=True)

    assert pool.calls == [(9, "rtsp://127.0.0.1/live")]
    assert adapter._player is fake_player
    assert adapter._media is fake_media
    assert adapter._instance is fake_instance
    assert fake_player.hwnds == [1234]
    assert fake_player.play_calls == 1
    assert fake_player.mute_calls == [False]


def test_stream_source_types_route_to_libvlc_srt_adapter() -> None:
    """SRT、RTSP 兼容源和自定义流目前都统一进入 libVLC 直播适配器。"""
    for source_type in ["srt_stream", "rtsp_stream", "custom_stream"]:
        adapter = create_adapter(source_type)

        assert isinstance(adapter, SrtStreamAdapter)
