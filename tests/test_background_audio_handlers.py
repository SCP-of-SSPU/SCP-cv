#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
播放器背景音频指令处理测试。
@Project : SCP-cv
@File : test_background_audio_handlers.py
@Author : Qintsg
@Date : 2026-06-08
'''
from __future__ import annotations

import pytest

from scp_cv.player.background_audio_handlers import BackgroundAudioHandlersMixin


class _ControllerStub(BackgroundAudioHandlersMixin):
    """只包含背景音乐状态的控制器替身。"""

    def __init__(self, adapter: object | None = None) -> None:
        """
        初始化测试用控制器。
        :param adapter: 当前背景音频适配器
        :return: None
        """
        self._background_audio_adapter = adapter
        self._background_audio_source_id = 0
        self._last_reported_background_audio_state = ("old", "", 0, 0)


class _AudioAdapterStub:
    """记录同源重启调用的背景音频适配器替身。"""

    current_uri = "C:/media/song.mp3"

    def __init__(self) -> None:
        """
        初始化调用记录。
        :return: None
        """
        self.calls: list[tuple[str, object]] = []

    def set_volume(self, volume: int) -> None:
        """
        记录音量设置。
        :param volume: 音量
        :return: None
        """
        self.calls.append(("volume", volume))

    def set_mute(self, muted: bool) -> None:
        """
        记录静音设置。
        :param muted: 是否静音
        :return: None
        """
        self.calls.append(("mute", muted))

    def restart_current_source(self, autoplay: bool = True) -> None:
        """
        记录原地重启。
        :param autoplay: 是否自动播放
        :return: None
        """
        self.calls.append(("restart", autoplay))


def test_restart_background_audio_if_same_source_restarts_in_place(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    同一音频源重复 OPEN 时应恢复音量/静音并原地重启播放器。
    :param monkeypatch: pytest monkeypatch 工具
    :return: None
    """
    progress_updates: list[dict[str, object]] = []
    adapter = _AudioAdapterStub()
    controller = _ControllerStub(adapter)
    controller._background_audio_source_id = 7
    monkeypatch.setattr(
        "scp_cv.services.background_audio.update_background_audio_progress",
        lambda **kwargs: progress_updates.append(kwargs),
    )

    handled = controller._restart_background_audio_if_same_source(
        7,
        "C:/media/song.mp3",
        {"volume": 35, "muted": True, "autoplay": True},
    )

    assert handled is True
    assert adapter.calls == [
        ("volume", 35),
        ("mute", True),
        ("restart", True),
    ]
    assert controller._last_reported_background_audio_state is None
    assert progress_updates == [{"playback_state": "playing", "position_ms": 0}]


def test_restart_background_audio_if_different_source_falls_through() -> None:
    """
    不同源 OPEN 仍应走关闭旧播放器并打开新播放器的普通路径。
    :return: None
    """
    adapter = _AudioAdapterStub()
    controller = _ControllerStub(adapter)
    controller._background_audio_source_id = 7

    handled = controller._restart_background_audio_if_same_source(
        8,
        "C:/media/other.mp3",
        {"volume": 35, "muted": True, "autoplay": True},
    )

    assert handled is False
    assert adapter.calls == []
