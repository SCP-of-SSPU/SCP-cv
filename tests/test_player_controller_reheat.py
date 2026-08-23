#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
播放器关闭后重建预热的竞态保护测试。
@Project : SCP-cv
@File : test_player_controller_reheat.py
@Author : Qintsg
@Date : 2026-05-30
'''
from __future__ import annotations

import pytest

from scp_cv.apps.playback.models import MediaSource, PlaybackState, SourceType
from scp_cv.player.controller import PlayerController
from scp_cv.services.playback import get_or_create_session, open_source


class _ClosableAdapter:
    """记录关闭调用的适配器替身。"""

    def __init__(self) -> None:
        """
        初始化关闭记录。
        :return: None
        """
        self.closed = False

    def close(self) -> None:
        """
        标记适配器已关闭。
        :return: None
        """
        self.closed = True


class _WindowStub:
    """关闭流程用播放器窗口替身。"""

    def show(self) -> None:
        """
        测试中无需显示窗口。
        :return: None
        """
        return

    def raise_(self) -> None:
        """
        测试中无需置顶窗口。
        :return: None
        """
        return

    def show_black_screen(self) -> None:
        """
        测试中无需渲染黑屏。
        :return: None
        """
        return


@pytest.mark.django_db
def test_close_detached_adapter_skips_reheat_when_same_source_still_active(
    media_source_ppt: MediaSource,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """同源 OPEN 已进入会话时，旧 CLOSE 不应抢先重建 PPT 预热。"""
    adapter = _ClosableAdapter()
    controller = PlayerController()
    reheated_source_ids: list[int] = []
    monkeypatch.setattr(
        controller,
        "_reheat_source_if_enabled",
        lambda source_id: reheated_source_ids.append(source_id),
    )
    open_source(1, media_source_ppt.pk)

    controller._close_detached_adapter(
        1,
        adapter,
        SourceType.PPT,
        media_source_ppt.pk,
        restore_window=False,
        reheat=True,
    )

    assert adapter.closed is True
    assert reheated_source_ids == []


@pytest.mark.django_db
def test_close_detached_adapter_skips_ppt_reheat_after_source_reaches_idle(
    media_source_ppt: MediaSource,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PPT 预热已停用；会话空闲后关闭旧适配器不应再调度延迟预热。"""
    adapter = _ClosableAdapter()
    controller = PlayerController()
    reheated_source_ids: list[int] = []
    scheduled_callbacks: list[object] = []
    monkeypatch.setattr(
        controller,
        "_reheat_source_if_enabled",
        lambda source_id: reheated_source_ids.append(source_id),
    )
    monkeypatch.setattr(
        "scp_cv.player.controller_adapter_lifecycle.QTimer.singleShot",
        lambda _delay_ms, callback: scheduled_callbacks.append(callback),
    )
    session = get_or_create_session(1)
    session.media_source = media_source_ppt
    session.playback_state = PlaybackState.IDLE
    session.save()

    controller._close_detached_adapter(
        1,
        adapter,
        SourceType.PPT,
        media_source_ppt.pk,
        restore_window=False,
        reheat=True,
    )

    assert adapter.closed is True
    assert reheated_source_ids == []
    assert scheduled_callbacks == []


@pytest.mark.django_db
def test_delayed_ppt_reheat_skips_when_same_source_reopens(
    media_source_ppt: MediaSource,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PPT 预热已停用；同源重开场景下不再有延迟预热回调。"""
    adapter = _ClosableAdapter()
    controller = PlayerController()
    reheated_source_ids: list[int] = []
    scheduled_callbacks: list[object] = []
    monkeypatch.setattr(
        controller,
        "_reheat_source_if_enabled",
        lambda source_id: reheated_source_ids.append(source_id),
    )
    monkeypatch.setattr(
        "scp_cv.player.controller_adapter_lifecycle.QTimer.singleShot",
        lambda _delay_ms, callback: scheduled_callbacks.append(callback),
    )
    session = get_or_create_session(1)
    session.media_source = media_source_ppt
    session.playback_state = PlaybackState.IDLE
    session.save()

    controller._close_detached_adapter(
        1,
        adapter,
        SourceType.PPT,
        media_source_ppt.pk,
        restore_window=False,
        reheat=True,
    )
    open_source(1, media_source_ppt.pk)

    assert scheduled_callbacks == []
    assert reheated_source_ids == []


@pytest.mark.django_db
def test_stale_close_does_not_clear_newer_open_session(
    media_source_ppt: MediaSource,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """旧 CLOSE 完成时若新 OPEN 已进入 LOADING，不应清空会话源。"""
    adapter = _ClosableAdapter()
    controller = PlayerController()
    controller._adapters[1] = adapter
    controller._adapter_source_types[1] = SourceType.PPT
    controller._adapter_source_ids[1] = media_source_ppt.pk
    open_source(1, media_source_ppt.pk)
    monkeypatch.setattr(controller, "get_window", lambda _window_id: _WindowStub())
    monkeypatch.setattr(controller, "_schedule_reheat_source_if_enabled", lambda *_args: None)

    controller._handle_close(1, {})

    session = get_or_create_session(1)
    assert adapter.closed is True
    assert session.media_source_id == media_source_ppt.pk
    assert session.playback_state == PlaybackState.LOADING
