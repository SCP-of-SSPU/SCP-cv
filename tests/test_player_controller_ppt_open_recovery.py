#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
播放器旧 PPT 在新源打开失败后的恢复测试。
@Project : SCP-cv
@File : test_player_controller_ppt_open_recovery.py
@Author : Qintsg
@Date : 2026-07-12
'''
from __future__ import annotations

import pytest

from scp_cv.player.controller import PlayerController
from tests.player_controller_open_recovery_test_support import (
    OpenAdapter as _OpenAdapter,
    WindowStub as _WindowStub,
)


def test_handle_open_keeps_previous_ppt_when_factory_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    """PPT 切换前的新 adapter 创建失败时不应提前关闭旧 PPT。"""
    controller = PlayerController()
    previous_adapter = _OpenAdapter()
    window = _WindowStub()

    controller._adapters[1] = previous_adapter  # type: ignore[assignment]
    controller._adapter_source_types[1] = "ppt"
    controller._adapter_source_ids[1] = 77
    monkeypatch.setattr(
        "scp_cv.player.controller_handlers.create_adapter",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("bad ppt")),
    )
    monkeypatch.setattr(controller, "get_window", lambda _window_id: window)

    with pytest.raises(ValueError, match="bad ppt"):
        controller._handle_open(1, {
            "source_id": 8,
            "source_type": "ppt",
            "uri": "C:/demo/bad.pptx",
            "autoplay": True,
        })

    assert previous_adapter.closed is False
    assert previous_adapter.detached_for_fast_switch is True
    assert previous_adapter.restored_after_failed_switch is True
    assert controller._adapters[1] is previous_adapter
    assert controller._adapter_source_types[1] == "ppt"
    assert controller._adapter_source_ids[1] == 77
    assert window.calls == ["video", "show", "raise"]
    assert window.topmost == [True]


def test_handle_open_keeps_previous_ppt_when_window_handle_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """窗口句柄不可用时不应提前关闭旧 PPT，且应释放新 adapter。"""
    controller = PlayerController()
    previous_adapter = _OpenAdapter()
    new_adapter = _OpenAdapter()
    window = _WindowStub()

    controller._adapters[1] = previous_adapter  # type: ignore[assignment]
    controller._adapter_source_types[1] = "ppt"
    controller._adapter_source_ids[1] = 77
    monkeypatch.setattr("scp_cv.player.controller_handlers.create_adapter", lambda *_args, **_kwargs: new_adapter)
    monkeypatch.setattr(controller, "get_window_handle", lambda _window_id: 0)
    monkeypatch.setattr(controller, "get_window", lambda _window_id: window)

    with pytest.raises(RuntimeError, match="没有可用窗口句柄"):
        controller._handle_open(1, {
            "source_id": 8,
            "source_type": "ppt",
            "uri": "C:/demo/next.pptx",
            "autoplay": True,
        })

    assert previous_adapter.closed is False
    assert previous_adapter.detached_for_fast_switch is True
    assert previous_adapter.restored_after_failed_switch is True
    assert new_adapter.closed is True
    assert controller._adapters[1] is previous_adapter
    assert controller._adapter_source_types[1] == "ppt"
    assert controller._adapter_source_ids[1] == 77
    assert window.calls == ["video", "show", "raise"]
    assert window.topmost == [True]


def test_handle_open_restores_previous_ppt_after_new_source_open_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """新源打开失败时应恢复旧 PPT 嵌入窗口，而不是预关闭旧 PPT。"""
    controller = PlayerController()
    previous_adapter = _OpenAdapter()
    new_adapter = _OpenAdapter()
    new_adapter.fail_open = True
    window = _WindowStub()
    calls: list[str] = []

    def detach_previous() -> None:
        """
        记录旧 PPT 隐藏调用。
        :return: None
        """
        calls.append("previous_detach")
        previous_adapter.detached_for_fast_switch = True

    def restore_previous() -> None:
        """
        记录旧 PPT 恢复调用。
        :return: None
        """
        calls.append("previous_restore")
        previous_adapter.restored_after_failed_switch = True

    previous_adapter.detach_for_fast_switch = detach_previous  # type: ignore[method-assign]
    previous_adapter.restore_after_failed_switch = restore_previous  # type: ignore[method-assign]
    controller._adapters[1] = previous_adapter  # type: ignore[assignment]
    controller._adapter_source_types[1] = "ppt"
    controller._adapter_source_ids[1] = 77

    monkeypatch.setattr("scp_cv.player.controller_handlers.create_adapter", lambda *_args, **_kwargs: new_adapter)
    monkeypatch.setattr(controller, "get_window_handle", lambda _window_id: 2001)
    monkeypatch.setattr(controller, "get_window", lambda _window_id: window)
    monkeypatch.setattr(controller, "_reheat_source_if_enabled", lambda source_id: calls.append(f"reheat:{source_id}"))

    with pytest.raises(RuntimeError, match="open failed"):
        controller._handle_open(1, {
            "source_id": 8,
            "source_type": "video",
            "uri": "C:/demo/fail.mp4",
            "autoplay": True,
        })

    assert calls == ["previous_detach", "previous_restore"]
    assert previous_adapter.closed is False
    assert previous_adapter.detached_for_fast_switch is True
    assert previous_adapter.restored_after_failed_switch is True
    assert new_adapter.closed is True
    assert controller._adapters[1] is previous_adapter
    assert controller._adapter_source_types[1] == "ppt"
    assert controller._adapter_source_ids[1] == 77
    assert window.calls == [
        "black",
        "show",
        "raise",
        "video",
        "show",
        "raise",
    ]
    assert window.topmost == [True, True]
