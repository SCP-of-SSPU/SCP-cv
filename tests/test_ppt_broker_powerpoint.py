#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PowerPoint Broker COM 后端打开与预热行为测试。
@Project : SCP-cv
@File : test_ppt_broker_powerpoint.py
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
    AnimatedPowerPoint as _AnimatedPowerPoint,
    AnimatedPresentation as _AnimatedPresentation,
    WindowPort as _WindowPort,
)


def test_open_keeps_untitled_presentation_dirty_until_close() -> None:
    """放映前不得写 Saved=True，关闭时再抑制 PowerPoint 保存提示。"""
    application = _AnimatedPowerPoint()
    backend = PowerPointComBackend(
        application_factory=lambda: application,
        process_id_reader=lambda _app: 4242,
        window_port=_WindowPort(),
        file_exists=lambda _uri: True,
    )
    broker = PptBrokerEngine(backend)
    session = PptSessionKey(1, "untitled-presentation")
    try:
        broker.open(PptOpenRequest(session, "C:/slides/source.pptx", 1001))
        presentation = application.Presentations.opened[0]

        assert presentation.saved_during_run is False

        broker.close(session)
        assert presentation.Saved is True
    finally:
        broker.shutdown()


def test_fallback_window_identity_uses_untitled_presentation_name() -> None:
    """独立 Untitled 副本应按实际 Presentation.Name 认领 fallback 窗口。"""
    application = _AnimatedPowerPoint()
    presentation = _AnimatedPresentation()
    presentation.Name = "演示文稿1"
    application.Presentations.Open = lambda *_args, **_kwargs: presentation
    windows = _WindowPort()
    backend = PowerPointComBackend(
        application_factory=lambda: application,
        process_id_reader=lambda _app: 4242,
        window_port=windows,
        file_exists=lambda _uri: True,
    )
    broker = PptBrokerEngine(backend)
    session = PptSessionKey(1, "untitled-window-title")
    try:
        broker.open(PptOpenRequest(session, "C:/slides/source.pptx", 1001))

        assert windows.expected_presentation_names == ["演示文稿1"]
    finally:
        broker.shutdown()


def test_preheated_presentation_stays_dirty_until_playback_close() -> None:
    """文件预热不得提前写 Saved=True，否则后续并发放映会被 PowerPoint 拒绝。"""
    application = _AnimatedPowerPoint()
    backend = PowerPointComBackend(
        application_factory=lambda: application,
        process_id_reader=lambda _app: 4242,
        window_port=_WindowPort(),
        file_exists=lambda _uri: True,
    )
    broker = PptBrokerEngine(backend)
    session = PptSessionKey(1, "preheated-presentation")
    try:
        broker.preheat(
            PptPreheatRequest(
                uri="C:/slides/source.pptx",
                source_id=24,
            )
        )
        presentation = application.Presentations.opened[0]
        assert presentation.Saved is False

        broker.open(
            PptOpenRequest(
                session,
                "C:/slides/source.pptx",
                1001,
                source_id=24,
            )
        )
        assert presentation.saved_during_run is False

        broker.close(session)
        assert presentation.Saved is True
    finally:
        broker.shutdown()


def test_open_keeps_full_show_and_navigates_to_requested_start_slide() -> None:
    """Broker 应保留完整放映范围，再显式定位请求页。"""
    application = _AnimatedPowerPoint()
    backend = PowerPointComBackend(
        application_factory=lambda: application,
        process_id_reader=lambda _app: 4242,
        window_port=_WindowPort(),
        file_exists=lambda _uri: True,
    )
    broker = PptBrokerEngine(backend)
    session = PptSessionKey(1, "start-slide")
    try:
        state = broker.open(
            PptOpenRequest(
                session,
                "C:/slides/source.pptx",
                1001,
                start_slide=3,
            )
        )

        assert state.current_slide == 3
        assert application.Presentations.opened[0].SlideShowSettings.RangeType == 1
        assert application.Presentations.opened[0].view.goto_slides == [3]
    finally:
        broker.shutdown()
