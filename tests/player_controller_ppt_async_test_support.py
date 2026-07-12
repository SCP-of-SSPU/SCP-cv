#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
播放器 PPT 异步打开测试共用替身。
@Project : SCP-cv
@File : player_controller_ppt_async_test_support.py
@Author : Qintsg
@Date : 2026-07-11
'''
from __future__ import annotations

from typing import Callable, Optional

import pytest

from scp_cv.player.controller import PlayerController


class _AsyncPptAdapter:
    """支持 open_async 的 PPT 适配器替身，可手动触发完成回调。"""

    def __init__(self, finish_immediately: bool = False, error: Exception | None = None) -> None:
        """
        初始化替身。
        :param finish_immediately: open_async 内是否立即同步回调
        :param error: 立即回调时上报的异常；None 表示成功
        :return: None
        """
        self.finish_immediately = finish_immediately
        self.error = error
        self.open_async_args: dict[str, object] = {}
        self.on_finished: Optional[Callable[[Optional[BaseException]], None]] = None
        self.closed = False
        self.close_count = 0
        self.detached = False
        self.restored = False
        self.volumes: list[int] = []
        self.mutes: list[bool] = []

    def open_async(
        self,
        uri: str,
        window_handle: int,
        autoplay: bool = True,
        start_slide: int = 0,
        on_finished: Optional[Callable[[Optional[BaseException]], None]] = None,
    ) -> None:
        """
        记录打开参数；按配置立即回调或交由测试手动触发。
        :param uri: 媒体 URI
        :param window_handle: 窗口句柄
        :param autoplay: 是否自动播放
        :param start_slide: 起始页码
        :param on_finished: 完成回调
        :return: None
        """
        self.open_async_args = {
            "uri": uri,
            "window_handle": window_handle,
            "autoplay": autoplay,
            "start_slide": start_slide,
        }
        self.on_finished = on_finished
        if self.finish_immediately and on_finished is not None:
            on_finished(self.error)

    def close(self) -> None:
        """记录关闭调用。"""
        self.closed = True
        self.close_count += 1

    def detach_for_fast_switch(self) -> None:
        """记录嵌入窗口隐藏调用。"""
        self.detached = True

    def restore_after_failed_switch(self) -> None:
        """记录嵌入窗口恢复调用。"""
        self.restored = True

    def set_volume(self, volume: int) -> None:
        """
        记录音量设置。
        :param volume: 音量
        :return: None
        """
        self.volumes.append(volume)

    def set_mute(self, muted: bool) -> None:
        """
        记录静音设置。
        :param muted: 是否静音
        :return: None
        """
        self.mutes.append(muted)


class _WindowStub:
    """记录窗口显示调用的替身。"""

    def __init__(self) -> None:
        """初始化记录。"""
        self.calls: list[str] = []
        self.topmost: list[bool] = []
        self.web_container = object()
        self.top_level_window_handle = 5001

    def show_black_screen(self) -> None:
        self.calls.append("black")

    def show(self) -> None:
        self.calls.append("show")

    def raise_(self) -> None:
        self.calls.append("raise")

    def set_always_on_top(self, enabled: bool) -> None:
        self.topmost.append(enabled)

    def show_web_container(self) -> None:
        self.calls.append("web")

    def show_video_container(self) -> None:
        self.calls.append("video")

    def prepare_ppt_container(self) -> None:
        self.calls.append("ppt_container")


def _make_controller(
    monkeypatch: pytest.MonkeyPatch,
    adapter: object,
) -> tuple[
    PlayerController,
    _WindowStub,
    list[tuple[int, str]],
    list[tuple[int, str]],
]:
    """
    构造带桩的控制器。
    :param monkeypatch: pytest monkeypatch
    :param adapter: create_adapter 返回的适配器替身
    :return: (controller, window, states, errors)
    """
    controller = PlayerController()
    window = _WindowStub()
    states: list[tuple[int, str]] = []
    errors: list[tuple[int, str]] = []

    monkeypatch.setattr(
        "scp_cv.player.controller_handlers.create_adapter",
        lambda *_args, **_kwargs: adapter,
    )
    monkeypatch.setattr(controller, "get_window_handle", lambda _window_id: 2001)
    monkeypatch.setattr(controller, "get_window", lambda _window_id: window)
    monkeypatch.setattr(controller, "_cleanup_temporary_source", lambda _command_args: None)
    monkeypatch.setattr(
        controller,
        "_update_session_state",
        lambda window_id, state: states.append((window_id, state)),
    )
    monkeypatch.setattr(
        controller,
        "_update_session_error",
        lambda window_id, message: errors.append((window_id, message)),
    )
    return controller, window, states, errors
