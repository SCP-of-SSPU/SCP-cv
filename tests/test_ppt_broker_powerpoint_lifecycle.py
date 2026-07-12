#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PowerPoint Broker Application 与放映资源生命周期测试。
@Project : SCP-cv
@File : test_ppt_broker_powerpoint_lifecycle.py
@Author : Qintsg
@Date : 2026-07-11
'''
from __future__ import annotations

from scp_cv.player.ppt_broker import (
    PptBrokerEngine,
    PptOpenRequest,
    PptPreheatRequest,
    PptSessionKey,
)
from scp_cv.player.ppt_broker.powerpoint import PowerPointComBackend
from tests.ppt_broker_powerpoint_test_support import (
    AnimatedPowerPoint as _SharedAnimatedPowerPoint,
    AnimatedPresentation as _SharedAnimatedPresentation,
    SentinelPresentation as _SharedSentinelPresentation,
    WindowPort as _SharedWindowPort,
)


class _PowerPointRunError(RuntimeError):
    """模拟 PowerPoint 零放映后再次 Run 返回 E_FAIL。"""

    hresult = -2_147_467_259


class _SentinelPresentation:
    """无编辑窗口、无 SlideShowWindow 的 Application sentinel。"""

    def __init__(self, presentations: _Presentations) -> None:
        self._presentations = presentations
        self.Saved = False
        self.closed = False

    def Close(self, *_args: object) -> None:
        self.closed = True
        self._presentations.remove(self)


class _ExternalPresentation:
    """启动前已由用户打开、Broker 不得关闭的外部文档。"""

    closed = False


class _SlideshowView:
    """关闭时只终止所属源放映。"""

    def __init__(self, application: _Application) -> None:
        self._application = application
        self.State = 1
        self.CurrentShowPosition = 1

    def Exit(self) -> None:
        self.State = 5
        self._application.sentinel_seen_on_exit.append(
            self._application.Presentations.has_open_sentinel
        )
        self._application.active_slideshows = 0
        self._application.completed_slideshow = True


class _SourcePresentation:
    """可启动一次窗口化放映的源 Presentation。"""

    def __init__(
        self,
        application: _Application,
        presentations: _Presentations,
    ) -> None:
        self._application = application
        self._presentations = presentations
        self.Name = "演示文稿1"
        self.Saved = False
        self.Slides = type("_Slides", (), {"Count": 5})()
        self.view = _SlideshowView(application)
        slideshow_window = type("_SlideShowWindow", (), {"View": self.view})()

        class _Settings:
            ShowType = 0
            RangeType = 1
            StartingSlide = 1
            EndingSlide = 5
            ShowPresenterView = True

            def Run(settings_self: object) -> object:
                if (
                    application.completed_slideshow
                    and not presentations.has_open_sentinel
                ):
                    raise _PowerPointRunError("SlideShowSettings.Run E_FAIL")
                application.active_slideshows = 1
                self.view.State = 1
                return slideshow_window

        self.SlideShowSettings = _Settings()
        self.closed = False

    def Close(self, *_args: object) -> None:
        self.closed = True
        self._presentations.remove(self)


class _Presentations:
    """区分 Application sentinel 与源 Presentation 的集合。"""

    def __init__(self, application: _Application) -> None:
        self._application = application
        self.items: list[
            _ExternalPresentation | _SentinelPresentation | _SourcePresentation
        ] = []
        self.sentinels: list[_SentinelPresentation] = []
        self.sources: list[_SourcePresentation] = []

    @property
    def Count(self) -> int:
        return len(self.items)

    @property
    def has_open_sentinel(self) -> bool:
        return any(not sentinel.closed for sentinel in self.sentinels)

    def Add(self, WithWindow: bool = False) -> _SentinelPresentation:
        assert WithWindow is False
        sentinel = _SentinelPresentation(self)
        self.items.append(sentinel)
        self.sentinels.append(sentinel)
        return sentinel

    def Open(self, *_args: object, **_kwargs: object) -> _SourcePresentation:
        source = _SourcePresentation(self._application, self)
        self.items.append(source)
        self.sources.append(source)
        return source

    def remove(
        self,
        presentation: _SentinelPresentation | _SourcePresentation,
    ) -> None:
        if presentation in self.items:
            self.items.remove(presentation)


class _SlideShowWindows:
    """只暴露真实源放映数量，sentinel 永远不占放映窗口。"""

    def __init__(self, application: _Application) -> None:
        self._application = application

    @property
    def Count(self) -> int:
        return self._application.active_slideshows


class _Application:
    """模拟 PowerPoint 在放映数归零后需要 sentinel 才能再次 Run。"""

    def __init__(self, *, external_presentation: bool = False) -> None:
        self.active_slideshows = 0
        self.completed_slideshow = False
        self.sentinel_seen_on_exit: list[bool] = []
        self.Presentations = _Presentations(self)
        self.external_presentation = (
            _ExternalPresentation() if external_presentation else None
        )
        if self.external_presentation is not None:
            self.Presentations.items.append(self.external_presentation)
        self.SlideShowWindows = _SlideShowWindows(self)
        self.DisplayAlerts = 2
        self.quit_called = False

    def Quit(self) -> None:
        self.quit_called = True


class _WindowPort:
    """记录每个源放映 HWND 是否完成释放。"""

    def __init__(self) -> None:
        self.next_hwnd = 9000
        self.closed: list[int] = []

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
        self.next_hwnd += 1
        return self.next_hwnd

    def embed(self, _hwnd: int, _parent_hwnd: int, _owner_token: int) -> tuple[int, int]:
        return 960, 540

    def hide(self, _hwnd: int) -> None:
        return

    def show(self, _hwnd: int, _parent_hwnd: int) -> None:
        return

    def prepare_close(self, _hwnd: int, _owner_token: int) -> None:
        return

    def close(self, hwnd: int, _owner_token: int) -> None:
        self.closed.append(hwnd)


def test_broker_reopens_after_all_source_slideshows_are_fully_released() -> None:
    """无放映 sentinel 应允许同一 Broker 在零公开会话后再次打开。"""
    application = _Application()
    windows = _WindowPort()
    backend = PowerPointComBackend(
        application_factory=lambda: application,
        process_id_reader=lambda _app: 4242,
        window_port=windows,
        file_exists=lambda _uri: True,
    )
    broker = PptBrokerEngine(backend)
    first = PptSessionKey(1, "first-cycle")
    second = PptSessionKey(1, "second-cycle")
    try:
        first_state = broker.open(
            PptOpenRequest(first, "C:/slides/source.pptx", 1001)
        )
        broker.close(first)

        assert application.SlideShowWindows.Count == 0
        assert all(source.closed for source in application.Presentations.sources)
        assert application.sentinel_seen_on_exit == [True]
        assert windows.closed == [first_state.slideshow_hwnd]

        second_state = broker.open(
            PptOpenRequest(second, "C:/slides/source.pptx", 1001)
        )
        broker.close(second)

        assert second_state.slideshow_hwnd != first_state.slideshow_hwnd
        assert application.SlideShowWindows.Count == 0
        assert all(source.closed for source in application.Presentations.sources)
        assert application.Presentations.has_open_sentinel is True
        assert not hasattr(
            application.Presentations.sentinels[0],
            "SlideShowSettings",
        )
    finally:
        broker.shutdown()

    assert application.Presentations.Count == 0


def test_final_close_preserves_unrelated_preheated_presentation() -> None:
    """创建 sentinel 和关闭当前源不得清理尚未消费的文件预热。"""
    application = _Application()
    backend = PowerPointComBackend(
        application_factory=lambda: application,
        process_id_reader=lambda _app: 4242,
        window_port=_WindowPort(),
        file_exists=lambda _uri: True,
    )
    broker = PptBrokerEngine(backend)
    active = PptSessionKey(1, "active-source")
    preheated = PptSessionKey(1, "preheated-source")
    try:
        broker.preheat(
            PptPreheatRequest(
                source_id=25,
                uri="C:/slides/preheated.pptx",
            )
        )
        cached_source = application.Presentations.sources[0]
        broker.open(
            PptOpenRequest(
                active,
                "C:/slides/active.pptx",
                1001,
                source_id=26,
            )
        )
        broker.close(active)

        assert cached_source.closed is False

        broker.open(
            PptOpenRequest(
                preheated,
                "C:/slides/preheated.pptx",
                1001,
                source_id=25,
            )
        )
        broker.close(preheated)
        assert cached_source.closed is True
    finally:
        broker.shutdown()


def test_shared_external_application_only_closes_broker_presentations() -> None:
    """非自有 Application 中 sentinel/source 可回收，外部文档和告警保持不变。"""
    application = _Application(external_presentation=True)
    application.DisplayAlerts = 73
    backend = PowerPointComBackend(
        application_factory=lambda: application,
        process_id_reader=lambda _app: 4242,
        process_snapshot=lambda: {4242: 20.0},
        window_port=_WindowPort(),
        file_exists=lambda _uri: True,
    )
    broker = PptBrokerEngine(backend)
    session = PptSessionKey(1, "shared-application")

    broker.open(PptOpenRequest(session, "C:/slides/source.pptx", 1001))
    broker.close(session)
    sentinel = application.Presentations.sentinels[0]
    broker.shutdown()

    assert sentinel.closed is True
    assert application.external_presentation is not None
    assert application.external_presentation.closed is False
    assert application.Presentations.items == [application.external_presentation]
    assert application.DisplayAlerts == 73
    assert application.quit_called is False


def test_last_close_keeps_owned_application_for_next_open() -> None:
    """关闭前先脱离远端父链后，共享 Application 应继续服务下一次打开。"""
    applications = [_SharedAnimatedPowerPoint()]
    application_index = 0

    def create_application() -> object:
        nonlocal application_index
        application = applications[application_index]
        application_index += 1
        return application

    backend = PowerPointComBackend(
        application_factory=create_application,
        process_id_reader=lambda _app: 999_999,
        window_port=_SharedWindowPort(),
        file_exists=lambda _uri: True,
    )
    broker = PptBrokerEngine(backend)
    first = PptSessionKey(1, "first-application")
    second = PptSessionKey(1, "second-application")
    try:
        broker.open(PptOpenRequest(first, "C:/slides/source.pptx", 1001))
        broker.close(first)

        assert applications[0].quit_called is False

        broker.open(PptOpenRequest(second, "C:/slides/source.pptx", 1001))
        assert application_index == 1
    finally:
        broker.shutdown()


def test_last_close_releases_slideshow_presentation_and_hwnd() -> None:
    """公开关闭最后一个会话后不得保留隐藏放映或 Presentation。"""

    class _GuardPresentation(_SharedAnimatedPresentation):
        def __init__(self) -> None:
            super().__init__()
            self.close_called = False

        def Close(self, *_args: object) -> None:
            self.close_called = True

    class _GuardPresentations:
        Count = 0

        def __init__(self) -> None:
            self.opened: list[_GuardPresentation] = []

        @staticmethod
        def Add(WithWindow: bool = False) -> _SharedSentinelPresentation:
            assert WithWindow is False
            return _SharedSentinelPresentation()

        def Open(self, *_args: object, **_kwargs: object) -> _GuardPresentation:
            presentation = _GuardPresentation()
            self.opened.append(presentation)
            return presentation

    class _GuardPowerPoint(_SharedAnimatedPowerPoint):
        def __init__(self) -> None:
            super().__init__()
            self.Presentations = _GuardPresentations()

    class _GuardWindowPort(_SharedWindowPort):
        def __init__(self) -> None:
            super().__init__()
            self.prepared: list[int] = []
            self.closed: list[int] = []

        def prepare_close(self, hwnd: int, _owner_token: int) -> None:
            self.prepared.append(hwnd)

        def close(self, hwnd: int, _owner_token: int) -> None:
            self.closed.append(hwnd)

    application = _GuardPowerPoint()
    window_port = _GuardWindowPort()
    backend = PowerPointComBackend(
        application_factory=lambda: application,
        process_id_reader=lambda _app: 4242,
        window_port=window_port,
        file_exists=lambda _uri: True,
    )
    broker = PptBrokerEngine(backend)
    first = PptSessionKey(1, "first-guard")
    try:
        broker.open(PptOpenRequest(first, "C:/slides/source.pptx", 1001))
        broker.close(first)
        first_presentation = application.Presentations.opened[0]

        assert first_presentation.view.State == 5
        assert first_presentation.close_called is True
        assert window_port.prepared == [8001]
        assert window_port.closed == [8001]
    finally:
        broker.shutdown()
