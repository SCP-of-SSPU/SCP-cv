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

from scp_cv.player.adapters import srt_stream
from scp_cv.player.adapters.srt_stream import SrtStreamAdapter


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


class _FakePlayer:
    """libVLC player 替身，返回固定播放状态。"""

    def __init__(self, playback_state: str) -> None:
        """
        初始化播放器替身。
        :param playback_state: 固定返回的 libVLC 状态
        :return: None
        """
        self.playback_state = playback_state

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
