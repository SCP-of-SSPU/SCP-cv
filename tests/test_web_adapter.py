#!/user/bin/env python
# -*- coding: UTF-8 -*-
"""网页适配器预热加载状态回归测试。"""

from __future__ import annotations

from scp_cv.player.adapters.web import WebSourceAdapter
from scp_cv.player.web_preheat import (
    PreheatedWebView,
    WebPreheatPool,
    _LOAD_STATE_ERROR,
    _LOAD_STATE_PROPERTY,
    _LOAD_STATE_SUCCESS,
)


class _SignalStub:
    def __init__(self) -> None:
        self.callbacks: list[object] = []

    def connect(self, callback: object) -> None:
        self.callbacks.append(callback)

    def disconnect(self, callback: object | None = None) -> None:
        """移除指定回调或全部回调。"""
        if callback is None:
            self.callbacks.clear()
        elif callback in self.callbacks:
            self.callbacks.remove(callback)


class _WebViewStub:
    def __init__(self, load_state: str) -> None:
        self.loadFinished = _SignalStub()
        self._properties = {_LOAD_STATE_PROPERTY: load_state}
        self.reload_calls = 0

    def property(self, name: str) -> object:
        return self._properties.get(name)

    def show(self) -> None:
        return None

    def setFocus(self) -> None:
        return None

    def updateGeometry(self) -> None:
        return None

    def update(self) -> None:
        return None

    def reload(self) -> None:
        """记录不应发生的重复导航。"""
        self.reload_calls += 1


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


def test_preheated_web_switch_reuses_same_view_without_reload(monkeypatch: object) -> None:
    """切离再切入网页只迁移实例，不应重新导航或创建 WebView。"""
    view = _WebViewStub(_LOAD_STATE_SUCCESS)

    class _PoolStub:
        """在前后台容器间归还同一网页实例。"""

        def __init__(self) -> None:
            self.available = view
            self.released: list[object] = []

        def take_preheated_view(self, *_args: object) -> object:
            """认领同一实例。"""
            result = self.available
            self.available = None
            return result

        def release_preheated_view(self, _source_id: int, _url: str, released_view: object) -> None:
            """把实例归还后台。"""
            self.released.append(released_view)
            self.available = released_view

    pool = _PoolStub()
    parent = _ParentStub()
    active_adapter = None
    for switch_index in range(50):
        active_adapter = WebSourceAdapter()
        active_adapter.set_parent_container(parent)  # type: ignore[arg-type]
        active_adapter.set_preheat_context(7, True, pool)  # type: ignore[arg-type]
        monkeypatch.setattr(active_adapter, "_configure_web_view_interaction", lambda _view: None)
        active_adapter.open("http://dashboard.test", 0)
        assert active_adapter._web_view is view
        if switch_index < 49:
            active_adapter.close()

    assert len(pool.released) == 49
    assert active_adapter is not None and active_adapter._web_view is view
    assert view.reload_calls == 0


def test_same_source_preheat_replacement_disposes_old_view(monkeypatch: object) -> None:
    """同一源强制替换预热实例时必须先释放旧 WebView。"""
    old_view = _WebViewStub(_LOAD_STATE_SUCCESS)
    disposed: list[object] = []

    class _Host:
        """提供预热布局的宿主替身。"""

        def layout(self) -> _LayoutStub:
            """返回布局。"""
            return _LayoutStub()

    pool = object.__new__(WebPreheatPool)
    pool._host = _Host()  # type: ignore[assignment]
    pool._items = {7: PreheatedWebView(7, "http://dashboard.test", old_view)}  # type: ignore[arg-type]
    monkeypatch.setattr(pool, "_dispose_view", lambda view: disposed.append(view))
    new_view = _WebViewStub(_LOAD_STATE_SUCCESS)
    new_view.setProperty = lambda _name, _value: None  # type: ignore[attr-defined]
    new_view.setUrl = lambda _url: None  # type: ignore[attr-defined]
    monkeypatch.setattr("scp_cv.player.web_preheat.QWebEngineView", lambda _host: new_view)

    pool.preheat_source(7, "http://dashboard.test", force=True)

    assert disposed == [old_view]
    assert pool._items[7].view is new_view
