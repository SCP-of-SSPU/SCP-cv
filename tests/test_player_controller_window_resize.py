#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
播放器控制器窗口尺寸同步测试。
@Project : SCP-cv
@File : test_player_controller_window_resize.py
@Author : Qintsg
@Date : 2026-07-12
'''
from __future__ import annotations

import pytest

from scp_cv.player.controller import PlayerController


def test_registered_window_resize_syncs_active_adapter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PlayerWindow resize 信号应驱动当前 Adapter 同步原生输出尺寸。"""

    class _Signal:
        def __init__(self) -> None:
            self.callbacks: list[object] = []

        def connect(self, callback: object) -> None:
            self.callbacks.append(callback)

        def disconnect(self, callback: object) -> None:
            if callback in self.callbacks:
                self.callbacks.remove(callback)

        def emit(self, *args: object) -> None:
            for callback in list(self.callbacks):
                callback(*args)  # type: ignore[operator]

    class _PlayerWindow:
        def __init__(self) -> None:
            self.window_closed = _Signal()
            self.render_viewport_resized = _Signal()

        @staticmethod
        def stop_all() -> None:
            return

    class _ResizableAdapter:
        is_open = True

        def __init__(self) -> None:
            self.sizes: list[tuple[int, int]] = []

        def resize_output(self, width: int, height: int) -> None:
            self.sizes.append((width, height))

    monkeypatch.setattr("scp_cv.player.window.PlayerWindow", _PlayerWindow)
    controller = PlayerController()
    window = _PlayerWindow()
    adapter = _ResizableAdapter()
    controller.register_window(1, window)
    controller._adapters[1] = adapter

    window.render_viewport_resized.emit(1, 640, 360)

    assert adapter.sizes == [(640, 360)]
