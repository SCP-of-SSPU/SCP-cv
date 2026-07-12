#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PowerPoint Broker COM 会话关闭与幂等释放测试。
@Project : SCP-cv
@File : test_ppt_broker_powerpoint_close.py
@Author : Qintsg
@Date : 2026-07-11
'''
from __future__ import annotations

import pytest

from scp_cv.player.ppt_broker import (
    PptBrokerEngine,
    PptOpenRequest,
    PptSessionKey,
    PptSessionNotFoundError,
)
from scp_cv.player.ppt_broker.powerpoint import PowerPointComBackend


class _TransientComError(RuntimeError):
    """模拟 RPC_E_CALL_REJECTED。"""

    hresult = -2_147_418_111


class _ReleasedComObjectError(RuntimeError):
    """模拟 View.Exit 后 COM 代理返回 RPC_E_DISCONNECTED。"""

    hresult = -2_147_417_848


class _PowerPointObjectMissingError(RuntimeError):
    """模拟 PowerPoint 通过 DISP_E_EXCEPTION 包装的 Object does not exist。"""

    hresult = -2_147_352_567

    def __init__(self) -> None:
        super().__init__(
            -2_147_352_567,
            "发生意外。",
            (
                0,
                "Microsoft PowerPoint",
                "SlideShowView.Exit : Object does not exist.",
                "",
                0,
                -2_147_188_720,
            ),
            None,
        )


class _SentinelPresentation:
    """无窗口、无放映的 Application sentinel 替身。"""

    Saved = False

    def Close(self, *_args: object) -> None:
        return


class _AnimatedView:
    """最小 PowerPoint SlideShowView 替身。"""

    State = 1

    def __init__(self) -> None:
        self.CurrentShowPosition = 1

    def Exit(self) -> None:
        self.State = 5


class _AnimatedPresentation:
    """带可替换视图的 Presentation 替身。"""

    def __init__(self, view: _AnimatedView | None = None) -> None:
        self.Saved = False
        self.Slides = type("_Slides", (), {"Count": 3})()
        self.view = view or _AnimatedView()
        slideshow_window = type("_SlideShowWindow", (), {"View": self.view})()

        class _Settings:
            ShowType = 0
            StartingSlide = 1
            EndingSlide = 3
            ShowPresenterView = True

            def Run(settings_self) -> object:
                self.view.CurrentShowPosition = settings_self.StartingSlide
                return slideshow_window

        self.SlideShowSettings = _Settings()

    def Close(self, *_args: object) -> None:
        return


class _AnimatedPresentations:
    """每次 Open 创建独立的 Presentation。"""

    Count = 0

    @staticmethod
    def Add(WithWindow: bool = False) -> _SentinelPresentation:
        assert WithWindow is False
        return _SentinelPresentation()

    @staticmethod
    def Open(*_args: object, **_kwargs: object) -> _AnimatedPresentation:
        return _AnimatedPresentation()


class _AnimatedPowerPoint:
    """最小 PowerPoint Application 替身。"""

    def __init__(self) -> None:
        self.Presentations = _AnimatedPresentations()
        self.DisplayAlerts = 2

    def Quit(self) -> None:
        return


class _WindowPort:
    """不依赖 Win32 的放映窗口 Adapter。"""

    def __init__(self) -> None:
        self.next_hwnd = 8000

    @staticmethod
    def snapshot(_process_id: int) -> dict[int, object]:
        return {}

    def resolve(
        self,
        _slideshow_window: object,
        _before: dict[int, object],
        _process_id: int,
        _forbidden_hwnds: object,
        expected_presentation_name: str = "",
    ) -> int:
        del expected_presentation_name
        self.next_hwnd += 1
        return self.next_hwnd

    @staticmethod
    def embed(
        _hwnd: int,
        _parent_hwnd: int,
        _owner_token: int,
    ) -> tuple[int, int]:
        return 960, 540

    @staticmethod
    def hide(_hwnd: int) -> None:
        return

    @staticmethod
    def show(_hwnd: int, _parent_hwnd: int) -> None:
        return

    @staticmethod
    def close(_hwnd: int, _owner_token: int) -> None:
        return


def _build_broker(presentation: _AnimatedPresentation) -> PptBrokerEngine:
    application = _AnimatedPowerPoint()
    application.Presentations.Open = lambda *_args, **_kwargs: presentation
    backend = PowerPointComBackend(
        application_factory=lambda: application,
        process_id_reader=lambda _app: 4242,
        window_port=_WindowPort(),
        file_exists=lambda _uri: True,
        retry_delays=(0.0, 0.0),
    )
    return PptBrokerEngine(backend)


def test_close_does_not_mark_presentation_saved_before_view_exit() -> None:
    """untitled Presentation 只能在显式 Close 前标记，不能污染 View.Exit。"""
    presentation = _AnimatedPresentation()
    saved_during_exit: list[bool] = []
    original_exit = presentation.view.Exit

    def record_saved_then_exit() -> None:
        saved_during_exit.append(bool(presentation.Saved))
        original_exit()

    presentation.view.Exit = record_saved_then_exit  # type: ignore[method-assign]
    broker = _build_broker(presentation)
    session = PptSessionKey(1, "saved-before-exit")
    try:
        broker.open(PptOpenRequest(session, "C:/slides/source.pptx", 1001))
        broker.close(session)

        assert saved_during_exit == [False]
        assert presentation.Saved is True
    finally:
        broker.shutdown()


def test_close_detaches_window_host_before_view_exit() -> None:
    """PowerPoint 销毁放映前必须先切断跨进程 Player 父链。"""
    events: list[str] = []

    class _OrderingView(_AnimatedView):
        def Exit(self) -> None:
            events.append("view_exit")
            super().Exit()

    class _OrderingWindowPort(_WindowPort):
        @staticmethod
        def prepare_close(_hwnd: int, _owner_token: int) -> None:
            events.append("prepare_close")

    class _OrderingPresentations:
        Count = 0

        def __init__(self) -> None:
            self.open_count = 0

        @staticmethod
        def Add(WithWindow: bool = False) -> _SentinelPresentation:
            assert WithWindow is False
            return _SentinelPresentation()

        def Open(self, *_args: object, **_kwargs: object) -> _AnimatedPresentation:
            self.open_count += 1
            view = _OrderingView() if self.open_count == 1 else _AnimatedView()
            return _AnimatedPresentation(view)

    application = _AnimatedPowerPoint()
    application.Presentations = _OrderingPresentations()
    backend = PowerPointComBackend(
        application_factory=lambda: application,
        process_id_reader=lambda _app: 4242,
        window_port=_OrderingWindowPort(),
        file_exists=lambda _uri: True,
    )
    broker = PptBrokerEngine(backend)
    session = PptSessionKey(1, "close-order")
    other_session = PptSessionKey(2, "close-order-other")
    try:
        broker.open(PptOpenRequest(session, "C:/slides/source.pptx", 1001))
        broker.open(PptOpenRequest(other_session, "C:/slides/other.pptx", 1002))
        broker.close(session)

        assert events[:2] == ["prepare_close", "view_exit"]
    finally:
        broker.shutdown()


def test_close_retries_transient_view_exit_rejection() -> None:
    """关闭会话时，View.Exit 的瞬时 RPC 拒绝应有限重试后成功。"""

    class _RetryExitView(_AnimatedView):
        """前两次 Exit 被 PowerPoint 暂时拒绝。"""

        def __init__(self) -> None:
            super().__init__()
            self.exit_attempts = 0

        def Exit(self) -> None:
            self.exit_attempts += 1
            if self.exit_attempts < 3:
                raise _TransientComError("PowerPoint is busy")
            super().Exit()

    view = _RetryExitView()
    broker = _build_broker(_AnimatedPresentation(view))
    session = PptSessionKey(1, "retry-exit-player")
    try:
        broker.open(PptOpenRequest(session, "C:/slides/retry-exit.pptx", 1001))

        broker.close(session)

        assert view.exit_attempts == 3
    finally:
        broker.shutdown()


def test_close_treats_powerpoint_object_missing_as_released(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """PowerPoint 专用 Object does not exist 应按已释放幂等处理。"""

    class _MissingExitView(_AnimatedView):
        def Exit(self) -> None:
            raise _PowerPointObjectMissingError()

    broker = _build_broker(_AnimatedPresentation(_MissingExitView()))
    session = PptSessionKey(1, "missing-exit-player")
    try:
        broker.open(PptOpenRequest(session, "C:/slides/missing-exit.pptx", 1001))

        with caplog.at_level(
            "DEBUG",
            logger="scp_cv.player.ppt_broker.powerpoint",
        ):
            broker.close(session)

        with pytest.raises(PptSessionNotFoundError, match="没有属于"):
            broker.get_state(session)
        assert not [record for record in caplog.records if record.levelname == "ERROR"]
    finally:
        broker.shutdown()


def test_close_retries_transient_presentation_close_rejection() -> None:
    """关闭会话时，Presentation.Close 的瞬时 RPC 拒绝应有限重试。"""

    class _RetryClosePresentation(_AnimatedPresentation):
        """前两次 Close 被 PowerPoint 暂时拒绝。"""

        def __init__(self) -> None:
            super().__init__()
            self.close_attempts = 0

        def Close(self, *_args: object) -> None:
            self.close_attempts += 1
            if self.close_attempts < 3:
                raise _TransientComError("PowerPoint is busy")

    presentation = _RetryClosePresentation()
    broker = _build_broker(presentation)
    session = PptSessionKey(1, "retry-close-player")
    try:
        broker.open(PptOpenRequest(session, "C:/slides/retry-close.pptx", 1001))

        broker.close(session)

        assert presentation.close_attempts == 3
    finally:
        broker.shutdown()


def test_close_propagates_deterministic_view_exit_error_without_retry() -> None:
    """View.Exit 的确定性错误必须立即上抛，不能记录日志后假成功。"""

    class _FailingExitView(_AnimatedView):
        """始终以确定性错误拒绝 Exit。"""

        def __init__(self) -> None:
            super().__init__()
            self.exit_attempts = 0

        def Exit(self) -> None:
            self.exit_attempts += 1
            raise ValueError("invalid slideshow state")

    view = _FailingExitView()
    broker = _build_broker(_AnimatedPresentation(view))
    session = PptSessionKey(1, "invalid-exit-player")
    try:
        broker.open(PptOpenRequest(session, "C:/slides/invalid-exit.pptx", 1001))

        with pytest.raises(ValueError, match="invalid slideshow state"):
            broker.close(session)

        assert view.exit_attempts == 1
    finally:
        broker.shutdown()


def test_close_propagates_deterministic_presentation_close_error() -> None:
    """Presentation.Close 的确定性错误必须立即上抛，不能静默成功。"""

    class _FailingClosePresentation(_AnimatedPresentation):
        """始终以确定性错误拒绝 Close。"""

        def __init__(self) -> None:
            super().__init__()
            self.close_attempts = 0

        def Close(self, *_args: object) -> None:
            self.close_attempts += 1
            raise ValueError("invalid presentation state")

    presentation = _FailingClosePresentation()
    broker = _build_broker(presentation)
    session = PptSessionKey(1, "invalid-close-player")
    try:
        broker.open(PptOpenRequest(session, "C:/slides/invalid-close.pptx", 1001))

        with pytest.raises(ValueError, match="invalid presentation state"):
            broker.close(session)

        assert presentation.close_attempts == 1
    finally:
        broker.shutdown()


def test_close_treats_presentation_destroyed_by_view_exit_as_released() -> None:
    """View.Exit 已销毁 Presentation 时，后续 Close 断连应幂等视为释放。"""

    class _DestroyedPresentation(_AnimatedPresentation):
        """放映退出后 COM Presentation 代理立即失效。"""

        def __init__(self) -> None:
            super().__init__()
            self.destroyed = False
            original_exit = self.view.Exit

            def exit_and_destroy() -> None:
                original_exit()
                self.destroyed = True

            self.view.Exit = exit_and_destroy  # type: ignore[method-assign]

        def Close(self, *_args: object) -> None:
            if self.destroyed:
                raise _ReleasedComObjectError("COM object disconnected")

    presentation = _DestroyedPresentation()
    broker = _build_broker(presentation)
    session = PptSessionKey(1, "destroyed-presentation-player")
    try:
        broker.open(PptOpenRequest(session, "C:/slides/destroyed.pptx", 1001))

        broker.close(session)

        assert presentation.destroyed is True
    finally:
        broker.shutdown()
