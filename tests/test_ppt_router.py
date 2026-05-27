#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PPT 后端路由测试，覆盖显式 LibreOffice / PowerPoint / WPS 选择行为。
@Project : SCP-cv
@File : test_ppt_router.py
@Author : Qintsg
@Date : 2026-05-26
'''
from __future__ import annotations

import pytest
from pytest import MonkeyPatch

from scp_cv.player.adapters import create_adapter, ppt_router
from scp_cv.player.adapters.base import AdapterState, SourceAdapter


class _FakePptBackend(SourceAdapter):
    """可控的 PPT 后端替身。"""

    def __init__(self, name: str, fail_open: bool = False) -> None:
        """
        初始化后端替身。
        :param name: 后端名称
        :param fail_open: 是否在 open 时抛错
        :return: None
        """
        super().__init__(adapter_name=name)
        self.fail_open = fail_open
        self.open_called = False
        self.close_called = False
        self.next_called = False

    def open(self, uri: str, window_handle: int, autoplay: bool = True) -> None:
        """
        记录打开调用。
        :param uri: PPT 文件路径
        :param window_handle: 窗口句柄
        :param autoplay: 是否自动播放
        :return: None
        """
        self.open_called = True
        if self.fail_open:
            raise RuntimeError(f"{self.adapter_name} failed")
        self._mark_open()

    def close(self) -> None:
        """
        记录关闭调用。
        :return: None
        """
        self.close_called = True
        self._mark_closed()

    def play(self) -> None:
        """播放。"""

    def pause(self) -> None:
        """暂停。"""

    def stop(self) -> None:
        """停止。"""

    def next_item(self) -> None:
        """
        记录下一项调用。
        :return: None
        """
        self.next_called = True

    def get_state(self) -> AdapterState:
        """
        返回测试状态。
        :return: AdapterState
        """
        return AdapterState(playback_state="playing", current_slide=2, total_slides=5)


def test_create_adapter_routes_ppt_to_backend_router() -> None:
    """工厂创建 PPT 时应返回路由适配器，并接收显式后端。"""
    adapter = create_adapter("ppt", ppt_backend="libreoffice")

    assert isinstance(adapter, ppt_router.PptSourceAdapter)
    assert adapter.configured_backend == "libreoffice"


def test_backend_uses_explicit_libreoffice(monkeypatch: MonkeyPatch) -> None:
    """显式 LibreOffice 时只创建 LibreOffice 后端。"""
    created: dict[str, _FakePptBackend] = {}

    def factory(backend: str) -> SourceAdapter:
        fake_backend = _FakePptBackend(backend)
        created[backend] = fake_backend
        return fake_backend

    monkeypatch.setattr(ppt_router, "create_ppt_backend_adapter", factory)
    adapter = ppt_router.PptSourceAdapter("libreoffice")

    adapter.open("demo.pptx", 1001, autoplay=True)
    adapter.next_item()

    assert adapter.active_backend == "libreoffice"
    assert created["libreoffice"].open_called is True
    assert created["libreoffice"].next_called is True
    assert "powerpoint" not in created


def test_backend_uses_explicit_powerpoint(monkeypatch: MonkeyPatch) -> None:
    """显式 PowerPoint 时只创建 PowerPoint 后端。"""
    created: dict[str, _FakePptBackend] = {}

    def factory(backend: str) -> SourceAdapter:
        fake_backend = _FakePptBackend(backend)
        created[backend] = fake_backend
        return fake_backend

    monkeypatch.setattr(ppt_router, "create_ppt_backend_adapter", factory)
    adapter = ppt_router.PptSourceAdapter("powerpoint")

    adapter.open("demo.pptx", 1001, autoplay=True)

    assert adapter.active_backend == "powerpoint"
    assert created["powerpoint"].open_called is True
    assert "libreoffice" not in created


def test_backend_uses_explicit_wps(monkeypatch: MonkeyPatch) -> None:
    """显式 WPS 时只创建 WPS 后端。"""
    created: dict[str, _FakePptBackend] = {}

    def factory(backend: str) -> SourceAdapter:
        fake_backend = _FakePptBackend(backend)
        created[backend] = fake_backend
        return fake_backend

    monkeypatch.setattr(ppt_router, "create_ppt_backend_adapter", factory)
    adapter = ppt_router.PptSourceAdapter("wps")

    adapter.open("demo.pptx", 1001, autoplay=True)

    assert adapter.active_backend == "wps"
    assert created["wps"].open_called is True
    assert "libreoffice" not in created
    assert "powerpoint" not in created


def test_explicit_backend_failure_does_not_fallback(monkeypatch: MonkeyPatch) -> None:
    """显式后端失败时不应触发另一个后端兜底。"""
    requested_backends: list[str] = []

    def factory(backend: str) -> SourceAdapter:
        requested_backends.append(backend)
        return _FakePptBackend(backend, fail_open=True)

    monkeypatch.setattr(ppt_router, "create_ppt_backend_adapter", factory)
    adapter = ppt_router.PptSourceAdapter("libreoffice")

    with pytest.raises(RuntimeError, match="libreoffice failed"):
        adapter.open("demo.pptx", 1001, autoplay=True)

    assert requested_backends == ["libreoffice"]
    assert adapter.active_backend == ""


def test_rejects_auto_backend() -> None:
    """auto 已删除，传入 auto 应直接报错。"""
    with pytest.raises(ValueError, match="不支持"):
        ppt_router.PptSourceAdapter("auto")


def test_create_backend_adapter_routes_wps() -> None:
    """后端工厂应把 wps 路由到 WPS 适配器。"""
    from scp_cv.player.adapters.ppt_wps import WpsPptSourceAdapter

    adapter = ppt_router.create_ppt_backend_adapter("wps")

    assert isinstance(adapter, WpsPptSourceAdapter)
