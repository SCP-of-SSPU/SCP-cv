#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
播放器适配器能力契约回归测试。
@Project : SCP-cv
@File : test_player_adapter_capabilities.py
@Author : Qintsg
@Date : 2026-08-30
'''
from __future__ import annotations

import pytest

from scp_cv.player.adapters.base import AdapterState, SourceAdapter, UnsupportedAdapterOperation
from scp_cv.player.controller import PlayerController
from scp_cv.apps.playback.models import PlaybackCommand


class _MinimalAdapter(SourceAdapter):
    """仅具备生命周期和基础播放能力的测试适配器。"""

    def open(self, uri: str, window_handle: int, autoplay: bool = True) -> None:
        """打开测试源。"""
        self._mark_open()

    def close(self) -> None:
        """关闭测试源。"""
        self._mark_closed()

    def play(self) -> None:
        """播放测试源。"""

    def pause(self) -> None:
        """暂停测试源。"""

    def stop(self) -> None:
        """停止测试源。"""

    def get_state(self) -> AdapterState:
        """返回测试状态。"""
        return AdapterState()


def test_base_adapter_raises_for_unsupported_operations() -> None:
    """默认能力不应静默吞掉 seek/音量等请求。"""
    adapter = _MinimalAdapter()
    assert adapter.supports("seek") is False
    with pytest.raises(UnsupportedAdapterOperation, match="seek"):
        adapter.seek(100)
    with pytest.raises(UnsupportedAdapterOperation, match="set_volume"):
        adapter.set_volume(50)


def test_controller_does_not_write_paused_when_adapter_operation_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """适配器执行失败时只写错误，不得伪造 paused 状态。"""
    adapter = _MinimalAdapter()
    adapter.pause = lambda: (_ for _ in ()).throw(RuntimeError("pause failed"))  # type: ignore[method-assign]
    controller = PlayerController(enable_background_audio=False)
    controller._adapters[1] = adapter
    states: list[str] = []
    errors: list[str] = []
    monkeypatch.setattr(controller, "_update_session_state", lambda _window_id, state: states.append(state))
    monkeypatch.setattr(controller, "_update_session_error", lambda _window_id, error: errors.append(error))

    controller._execute_command_on_main_thread(1, PlaybackCommand.PAUSE, {})

    assert states == []
    assert errors == ["pause failed"]
