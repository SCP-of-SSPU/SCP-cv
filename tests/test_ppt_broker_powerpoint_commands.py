#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PowerPoint Broker COM 播放状态指令测试。
@Project : SCP-cv
@File : test_ppt_broker_powerpoint_commands.py
@Author : Qintsg
@Date : 2026-07-11
'''
from __future__ import annotations

from collections.abc import Callable

import pytest

from scp_cv.player.ppt_broker import (
    PptBrokerEngine,
    PptCommand,
    PptCommandRequest,
    PptOpenRequest,
    PptSessionKey,
)
from scp_cv.player.ppt_broker.powerpoint import PowerPointComBackend


class _TransientComError(RuntimeError):
    """模拟 RPC_E_CALL_REJECTED。"""

    hresult = -2_147_418_111


class _SentinelPresentation:
    """无窗口、无放映的 Application sentinel 替身。"""

    Saved = False

    def Close(self, *_args: object) -> None:
        return


class _PlaybackView:
    """可按需拒绝 State 写入的 SlideShowView 替身。"""

    def __init__(self) -> None:
        self.CurrentShowPosition = 1
        self._state = 1
        self.state_write_attempts = 0
        self.state_write_failure: Callable[[], BaseException | None] | None = None

    @property
    def State(self) -> int:
        return self._state

    @State.setter
    def State(self, value: int) -> None:
        self.state_write_attempts += 1
        if self.state_write_failure is not None:
            write_error = self.state_write_failure()
            if write_error is not None:
                raise write_error
        self._state = int(value)

    def Exit(self) -> None:
        self._state = 5


class _Presentation:
    """提供窗口化放映入口的 Presentation 替身。"""

    def __init__(self, view: _PlaybackView) -> None:
        self.Name = "演示文稿1"
        self.Saved = False
        self.Slides = type("_Slides", (), {"Count": 3})()
        slideshow_window = type("_SlideShowWindow", (), {"View": view})()

        class _Settings:
            ShowType = 0
            RangeType = 1
            StartingSlide = 1
            EndingSlide = 3
            ShowPresenterView = True

            def Run(settings_self: object) -> object:
                return slideshow_window

        self.SlideShowSettings = _Settings()

    def Close(self, *_args: object) -> None:
        return


class _Application:
    """只返回一个指定 Presentation 的 PowerPoint Application 替身。"""

    def __init__(self, presentation: _Presentation) -> None:
        class _Presentations:
            Count = 0

            @staticmethod
            def Add(WithWindow: bool = False) -> _SentinelPresentation:
                assert WithWindow is False
                return _SentinelPresentation()

            def Open(
                presentations_self: object,
                *_args: object,
                **_kwargs: object,
            ) -> _Presentation:
                return presentation

        self.Presentations = _Presentations()
        self.DisplayAlerts = 2

    def Quit(self) -> None:
        return


class _WindowPort:
    """不依赖 Win32 的放映窗口端口。"""

    def snapshot(self, _process_id: int) -> dict[int, object]:
        return {}

    def resolve(
        self,
        _slideshow_window: object,
        _before: dict[int, object],
        _process_id: int,
        _forbidden_hwnds: object,
        expected_presentation_name: str = "",
    ) -> int:
        return 8001

    def embed(self, _hwnd: int, _parent_hwnd: int, _owner_token: int) -> tuple[int, int]:
        return 960, 540

    def hide(self, _hwnd: int) -> None:
        return

    def show(self, _hwnd: int, _parent_hwnd: int) -> None:
        return

    def close(self, _hwnd: int, _owner_token: int) -> None:
        return


@pytest.mark.parametrize(
    ("command", "expected_playback_state"),
    [
        (PptCommand.PLAY, "playing"),
        (PptCommand.PAUSE, "paused"),
    ],
)
def test_playback_state_command_retries_transient_powerpoint_rejection(
    command: PptCommand,
    expected_playback_state: str,
) -> None:
    """PLAY/PAUSE 的瞬时 COM 拒绝应在公开 Broker 指令中有限重试。"""
    view = _PlaybackView()
    presentation = _Presentation(view)
    application = _Application(presentation)
    backend = PowerPointComBackend(
        application_factory=lambda: application,
        process_id_reader=lambda _app: 4242,
        window_port=_WindowPort(),
        file_exists=lambda _uri: True,
        retry_delays=(0.0, 0.0),
    )
    broker = PptBrokerEngine(backend)
    session = PptSessionKey(1, f"retry-{command.value}")
    try:
        broker.open(PptOpenRequest(session, "C:/slides/source.pptx", 1001))
        failures_remaining = 2

        def transient_failure() -> BaseException | None:
            nonlocal failures_remaining
            if failures_remaining > 0:
                failures_remaining -= 1
                return _TransientComError("PowerPoint is busy")
            return None

        view.state_write_failure = transient_failure

        state = broker.command(PptCommandRequest(session, command))

        assert view.state_write_attempts == 3
        assert state.playback_state == expected_playback_state
    finally:
        view.state_write_failure = None
        broker.shutdown()


@pytest.mark.parametrize("command", [PptCommand.PLAY, PptCommand.PAUSE])
def test_playback_state_command_does_not_retry_deterministic_error(
    command: PptCommand,
) -> None:
    """PLAY/PAUSE 的确定性 State 写入错误必须首次失败即返回。"""
    view = _PlaybackView()
    presentation = _Presentation(view)
    application = _Application(presentation)
    backend = PowerPointComBackend(
        application_factory=lambda: application,
        process_id_reader=lambda _app: 4242,
        window_port=_WindowPort(),
        file_exists=lambda _uri: True,
        retry_delays=(0.0, 0.0, 0.0),
    )
    broker = PptBrokerEngine(backend)
    session = PptSessionKey(1, f"deterministic-{command.value}")
    try:
        broker.open(PptOpenRequest(session, "C:/slides/source.pptx", 1001))
        view.state_write_failure = lambda: ValueError("invalid slideshow state")

        with pytest.raises(ValueError, match="invalid slideshow state"):
            broker.command(PptCommandRequest(session, command))

        assert view.state_write_attempts == 1
    finally:
        view.state_write_failure = None
        broker.shutdown()
