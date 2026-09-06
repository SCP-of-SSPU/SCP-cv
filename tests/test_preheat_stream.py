#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
直播预热续热与后台重建回归测试。
@Project : SCP-cv
@File : test_preheat_stream.py
@Author : Qintsg
@Date : 2026-08-30
'''
from __future__ import annotations

from pytest import MonkeyPatch

from scp_cv.player.preheat_stream import StreamPreheatHandle


class _Player:
    """返回直播连接状态的播放器替身。"""

    def __init__(self, state: object) -> None:
        self.state = state

    def get_state(self) -> object:
        """返回当前连接状态。"""
        return self.state


def test_expired_stream_preheat_refreshes_valid_connection(
    monkeypatch: MonkeyPatch,
) -> None:
    """过期但仍有效的连接应续热而不是被无条件丢弃。"""
    now = [601.0]
    monkeypatch.setattr("scp_cv.player.preheat_stream.time.monotonic", lambda: now[0])
    handle = StreamPreheatHandle(1, "srt://example/live")
    handle._instance = object()
    handle._player = _Player("playing")
    handle._media = object()
    handle._ready_at = 1.0
    now[0] = 601.0

    assert handle.refresh() is True
    assert handle.is_stale() is False


def test_failed_stream_preheat_is_rebuilt_in_background(
    monkeypatch: MonkeyPatch,
) -> None:
    """连接进入错误状态时应关闭旧句柄并后台启动新句柄。"""
    handle = StreamPreheatHandle(2, "srt://example/live")
    handle._instance = object()
    handle._player = _Player("error")
    handle._media = object()
    rebuilt = []
    monkeypatch.setattr(handle, "close", lambda: rebuilt.append("close"))
    monkeypatch.setattr(handle, "start", lambda: (rebuilt.append("start"), setattr(handle, "_instance", object()), setattr(handle, "_player", object()), setattr(handle, "_media", object())))

    assert handle.refresh() is True
    assert rebuilt == ["close", "start"]
