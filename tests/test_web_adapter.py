#!/user/bin/env python
# -*- coding: UTF-8 -*-
"""网页适配器预热加载状态回归测试。"""

from __future__ import annotations

from scp_cv.player.adapters.web import WebSourceAdapter
from scp_cv.player.web_preheat import (
    _LOAD_STATE_ERROR,
    _LOAD_STATE_PROPERTY,
    _LOAD_STATE_SUCCESS,
)


class _SignalStub:
    def __init__(self) -> None:
        self.callbacks: list[object] = []

    def connect(self, callback: object) -> None:
        self.callbacks.append(callback)


class _WebViewStub:
    def __init__(self, load_state: str) -> None:
        self.loadFinished = _SignalStub()
        self._properties = {_LOAD_STATE_PROPERTY: load_state}

    def property(self, name: str) -> object:
        return self._properties.get(name)

    def show(self) -> None:
        return None

    def setFocus(self) -> None:
        return None


class _LayoutStub:
    def addWidget(self, _widget: object) -> None:
        return None


class _ParentStub:
    def __init__(self) -> None:
        self._layout = _LayoutStub()

    def layout(self) -> _LayoutStub:
        return self._layout


def _open_with_preheated_state(monkeypatch: object, load_state: str) -> WebSourceAdapter:
    adapter = WebSourceAdapter()
    adapter.set_parent_container(_ParentStub())  # type: ignore[arg-type]
    view = _WebViewStub(load_state)
    monkeypatch.setattr(adapter, "_take_preheated_view", lambda _url: view)
    monkeypatch.setattr(adapter, "_configure_web_view_interaction", lambda _view: None)
    adapter.open("http://unreachable.test", 0)
    return adapter


def test_preheated_web_failure_is_visible_after_adapter_takes_view(monkeypatch: object) -> None:
    """预热阶段已失败时，接管后的适配器必须立即上报 error。"""
    adapter = _open_with_preheated_state(monkeypatch, _LOAD_STATE_ERROR)

    state = adapter.get_state()

    assert state.playback_state == "error"
    assert "网页加载失败" in state.error_message


def test_preheated_web_success_is_playing_after_adapter_takes_view(monkeypatch: object) -> None:
    """预热阶段已成功时，接管后的适配器可立即上报 playing。"""
    adapter = _open_with_preheated_state(monkeypatch, _LOAD_STATE_SUCCESS)

    assert adapter.get_state().playback_state == "playing"


def test_web_adapter_reports_loading_until_load_finished(monkeypatch: object) -> None:
    """尚未结束的网页加载不得提前误报 playing。"""
    adapter = _open_with_preheated_state(monkeypatch, "loading")

    assert adapter.get_state().playback_state == "loading"
    adapter._on_load_finished(True)
    assert adapter.get_state().playback_state == "playing"
