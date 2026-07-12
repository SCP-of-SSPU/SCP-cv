#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PowerPoint Broker COM 导航与尺寸同步测试。
@Project : SCP-cv
@File : test_ppt_broker_powerpoint_navigation.py
@Author : Qintsg
@Date : 2026-07-12
'''
from __future__ import annotations

from scp_cv.player.ppt_broker import (
    PptBrokerEngine,
    PptCommand,
    PptCommandRequest,
    PptOpenRequest,
    PptSessionKey,
)
from scp_cv.player.ppt_broker.powerpoint import PowerPointComBackend
from tests.ppt_broker_powerpoint_test_support import (
    AnimatedPowerPoint as _AnimatedPowerPoint,
    AnimatedPresentation as _AnimatedPresentation,
    AnimatedView as _AnimatedView,
    TransientComError as _TransientComError,
    WindowPort as _WindowPort,
)


def test_first_and_last_slide_still_dispatch_animation_clicks() -> None:
    """首尾页边界不得提前吞掉仍可能存在的动画点击。"""
    application = _AnimatedPowerPoint()
    backend = PowerPointComBackend(
        application_factory=lambda: application,
        process_id_reader=lambda _app: 4242,
        window_port=_WindowPort(),
        file_exists=lambda _uri: True,
    )
    broker = PptBrokerEngine(backend)
    last = PptSessionKey(1, "last-slide-player")
    first = PptSessionKey(2, "first-slide-player")
    try:
        broker.open(PptOpenRequest(last, "C:/slides/last.pptx", 1001, start_slide=3))
        broker.open(PptOpenRequest(first, "C:/slides/first.pptx", 1002, start_slide=1))

        broker.command(PptCommandRequest(last, PptCommand.NEXT))
        broker.command(PptCommandRequest(first, PptCommand.PREVIOUS))

        assert application.Presentations.opened[0].view.next_clicks == 1
        assert application.Presentations.opened[1].view.previous_clicks == 1
    finally:
        broker.shutdown()


def test_navigation_retries_transient_powerpoint_rejection() -> None:
    """NEXT 的 RPC_E_CALL_REJECTED 应由 COM 后端有限重试。"""

    class _RetryNavigationView(_AnimatedView):
        def GotoNextClick(self) -> None:
            self.next_clicks += 1
            if self.next_clicks < 3:
                raise _TransientComError("PowerPoint is busy")

    application = _AnimatedPowerPoint()
    view = _RetryNavigationView()
    presentation = _AnimatedPresentation(view)
    application.Presentations.Open = lambda *_args, **_kwargs: presentation
    backend = PowerPointComBackend(
        application_factory=lambda: application,
        process_id_reader=lambda _app: 4242,
        window_port=_WindowPort(),
        file_exists=lambda _uri: True,
        retry_delays=(0.0, 0.0),
    )
    broker = PptBrokerEngine(backend)
    session = PptSessionKey(1, "retry-navigation-player")
    try:
        broker.open(PptOpenRequest(session, "C:/slides/source.pptx", 1001))

        broker.command(PptCommandRequest(session, PptCommand.NEXT))

        assert view.next_clicks == 3
    finally:
        broker.shutdown()


def test_resize_command_resynchronizes_active_slideshow_parent() -> None:
    """Broker resize 指令应使用会话注册的 HWND 与 Player 父容器。"""
    application = _AnimatedPowerPoint()
    windows = _WindowPort()
    backend = PowerPointComBackend(
        application_factory=lambda: application,
        process_id_reader=lambda _app: 4242,
        window_port=windows,
        file_exists=lambda _uri: True,
    )
    broker = PptBrokerEngine(backend)
    session = PptSessionKey(1, "resize-player")
    try:
        opened = broker.open(PptOpenRequest(session, "C:/slides/source.pptx", 1001))

        broker.command(PptCommandRequest(session, PptCommand.RESIZE))

        assert windows.resize_calls == [(opened.slideshow_hwnd, 1001)]
    finally:
        broker.shutdown()
