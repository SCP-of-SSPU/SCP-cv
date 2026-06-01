#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
播放器 OPEN 指令失败恢复测试，覆盖 PPT 预关闭边界。
@Project : SCP-cv
@File : test_player_controller_open_recovery.py
@Author : Qintsg
@Date : 2026-05-29
'''
from __future__ import annotations

import pytest

from scp_cv.player.controller import PlayerController


class _OpenAdapter:
    """记录 OPEN/close 调用的 adapter 替身。"""

    def __init__(self) -> None:
        """
        初始化调用状态。
        :return: None
        """
        self.open_args: dict[str, object] = {}
        self.goto_items: list[int] = []
        self.volumes: list[int] = []
        self.mutes: list[bool] = []
        self.closed = False
        self.fail_open = False
        self.has_external_slideshow_window = True

    def open(self, uri: str, window_handle: int, autoplay: bool = True) -> None:
        """
        模拟打开媒体源。
        :param uri: 媒体 URI
        :param window_handle: 窗口句柄
        :param autoplay: 是否自动播放
        :return: None
        :raises RuntimeError: fail_open 为 True 时抛出
        """
        self.open_args = {
            "uri": uri,
            "window_handle": window_handle,
            "autoplay": autoplay,
        }
        if self.fail_open:
            raise RuntimeError("open failed")

    def close(self) -> None:
        """
        记录关闭调用。
        :return: None
        """
        self.closed = True

    def goto_item(self, index: int) -> None:
        """
        记录跳页参数。
        :param index: 目标页码
        :return: None
        """
        self.goto_items.append(index)

    def set_volume(self, volume: int) -> None:
        """
        模拟设置音量。
        :param volume: 音量
        :return: None
        """
        self.volumes.append(volume)

    def set_mute(self, muted: bool) -> None:
        """
        模拟设置静音。
        :param muted: 是否静音
        :return: None
        """
        self.mutes.append(muted)


class _WindowStub:
    """记录播放器窗口显示状态的替身。"""

    def __init__(self) -> None:
        """
        初始化调用记录。
        :return: None
        """
        self.calls: list[str] = []
        self.web_container = object()

    def show_black_screen(self) -> None:
        """
        记录黑屏显示。
        :return: None
        """
        self.calls.append("black")

    def hide_window(self) -> None:
        """
        记录隐藏窗口。
        :return: None
        """
        self.calls.append("hide")

    def show(self) -> None:
        """
        记录显示窗口。
        :return: None
        """
        self.calls.append("show")

    def raise_(self) -> None:
        """
        记录置顶窗口。
        :return: None
        """
        self.calls.append("raise")

    def show_web_container(self) -> None:
        """
        记录网页容器显示。
        :return: None
        """
        self.calls.append("web")

    def show_video_container(self) -> None:
        """
        记录视频容器显示。
        :return: None
        """
        self.calls.append("video")


def test_handle_open_passes_wps_backend_to_adapter(monkeypatch: pytest.MonkeyPatch) -> None:
    """播放器处理 OPEN 指令时应把 WPS 后端透传给适配器工厂。"""
    controller = PlayerController()
    adapter = _OpenAdapter()
    window = _WindowStub()
    created_options: dict[str, object] = {}
    states: list[tuple[int, str]] = []

    def create_adapter_stub(source_type: str, **adapter_options: object) -> _OpenAdapter:
        """
        记录适配器创建参数。
        :param source_type: 源类型
        :param adapter_options: 适配器选项
        :return: adapter 替身
        """
        created_options["source_type"] = source_type
        created_options.update(adapter_options)
        return adapter

    monkeypatch.setattr("scp_cv.player.controller_handlers.create_adapter", create_adapter_stub)
    monkeypatch.setattr(controller, "get_window_handle", lambda _window_id: 2001)
    monkeypatch.setattr(controller, "get_window", lambda _window_id: window)
    monkeypatch.setattr(controller, "_close_adapter", lambda _window_id: None)
    monkeypatch.setattr(controller, "_cleanup_temporary_source", lambda _command_args: None)
    monkeypatch.setattr(controller, "_update_session_state", lambda window_id, state: states.append((window_id, state)))

    controller._handle_open(1, {
        "source_id": 7,
        "source_type": "ppt",
        "uri": "C:/demo/wps.pptx",
        "autoplay": True,
        "ppt_backend": "wps",
        "target_slide": 4,
        "volume": 88,
        "muted": True,
    })

    assert created_options == {"source_type": "ppt", "ppt_backend": "wps"}
    assert adapter.open_args == {"uri": "C:/demo/wps.pptx", "window_handle": 2001, "autoplay": True}
    assert adapter.goto_items == [4]
    assert adapter.volumes == [88]
    assert adapter.mutes == [True]
    assert controller._adapters[1] is adapter
    assert controller._adapter_source_ids[1] == 7
    assert states == [(1, "playing")]
    assert window.calls == ["black", "show", "raise", "hide"]


def test_handle_open_keeps_black_window_when_ppt_has_no_slideshow(monkeypatch: pytest.MonkeyPatch) -> None:
    """PPT 未自动放映时应保留 PySide 黑屏窗口，避免露出桌面。"""
    controller = PlayerController()
    adapter = _OpenAdapter()
    adapter.has_external_slideshow_window = False
    window = _WindowStub()
    states: list[tuple[int, str]] = []

    monkeypatch.setattr("scp_cv.player.controller_handlers.create_adapter", lambda *_args, **_kwargs: adapter)
    monkeypatch.setattr(controller, "get_window_handle", lambda _window_id: 2001)
    monkeypatch.setattr(controller, "get_window", lambda _window_id: window)
    monkeypatch.setattr(controller, "_close_adapter", lambda _window_id: None)
    monkeypatch.setattr(controller, "_cleanup_temporary_source", lambda _command_args: None)
    monkeypatch.setattr(controller, "_update_session_state", lambda window_id, state: states.append((window_id, state)))

    controller._handle_open(1, {
        "source_id": 7,
        "source_type": "ppt",
        "uri": "C:/demo/manual.pptx",
        "autoplay": False,
    })

    assert window.calls == ["black", "show", "raise", "show", "raise", "black"]
    assert states == [(1, "loading")]


def test_handle_open_restores_window_when_ppt_open_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    """PPT 外部窗口打开失败时应关闭适配器并恢复 PySide 黑屏窗口。"""
    controller = PlayerController()
    adapter = _OpenAdapter()
    adapter.fail_open = True
    window = _WindowStub()

    monkeypatch.setattr("scp_cv.player.controller_handlers.create_adapter", lambda *_args, **_kwargs: adapter)
    monkeypatch.setattr(controller, "get_window_handle", lambda _window_id: 2001)
    monkeypatch.setattr(controller, "get_window", lambda _window_id: window)
    monkeypatch.setattr(controller, "_close_adapter", lambda _window_id: None)
    monkeypatch.setattr(controller, "_cleanup_temporary_source", lambda _command_args: None)

    with pytest.raises(RuntimeError, match="open failed"):
        controller._handle_open(1, {
            "source_id": 7,
            "source_type": "ppt",
            "uri": "C:/demo/fail.pptx",
            "autoplay": True,
        })

    assert adapter.closed is True
    assert controller._adapters == {}
    assert window.calls == ["black", "show", "raise", "show", "raise", "black"]


def test_handle_stop_restores_black_window_for_ppt(monkeypatch: pytest.MonkeyPatch) -> None:
    """停止 PPT 后应恢复 PySide 黑屏窗口。"""
    controller = PlayerController()
    adapter = _OpenAdapter()
    window = _WindowStub()
    states: list[tuple[int, str]] = []
    stop_calls: list[bool] = []

    def stop_adapter() -> None:
        """记录 stop 调用并模拟外部放映窗口已关闭。"""
        stop_calls.append(True)
        adapter.has_external_slideshow_window = False

    adapter.stop = stop_adapter  # type: ignore[method-assign]
    controller._adapters[1] = adapter  # type: ignore[assignment]
    controller._adapter_source_types[1] = "ppt"
    monkeypatch.setattr(controller, "get_window", lambda _window_id: window)
    monkeypatch.setattr(controller, "_update_session_state", lambda window_id, state: states.append((window_id, state)))

    controller._handle_stop(1, {})

    assert stop_calls == [True]
    assert window.calls == ["show", "raise", "black"]
    assert states == [(1, "stopped")]


def test_handle_open_restores_window_for_non_ppt_source(monkeypatch: pytest.MonkeyPatch) -> None:
    """从 PPT 切换到非 PPT 内容时应恢复 PySide 播放窗口。"""
    controller = PlayerController()
    adapter = _OpenAdapter()
    window = _WindowStub()
    states: list[tuple[int, str]] = []

    monkeypatch.setattr("scp_cv.player.controller_handlers.create_adapter", lambda *_args, **_kwargs: adapter)
    monkeypatch.setattr(controller, "get_window_handle", lambda _window_id: 2001)
    monkeypatch.setattr(controller, "get_window", lambda _window_id: window)
    monkeypatch.setattr(controller, "_close_adapter", lambda _window_id: None)
    monkeypatch.setattr(controller, "_cleanup_temporary_source", lambda _command_args: None)
    monkeypatch.setattr(controller, "_update_session_state", lambda window_id, state: states.append((window_id, state)))

    controller._handle_open(1, {
        "source_id": 8,
        "source_type": "video",
        "uri": "C:/demo/video.mp4",
        "autoplay": True,
    })

    assert window.calls == ["black", "show", "raise", "video"]
    assert states == [(1, "playing")]


def test_handle_open_restores_previous_adapter_when_factory_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    """新适配器创建失败时应恢复旧 adapter，避免旧内容失控或泄漏。"""
    controller = PlayerController()
    previous_adapter = _OpenAdapter()
    window = _WindowStub()

    controller._adapters[1] = previous_adapter  # type: ignore[assignment]
    controller._adapter_source_types[1] = "video"
    controller._adapter_source_ids[1] = 77
    monkeypatch.setattr("scp_cv.player.controller_handlers.create_adapter", lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("bad source")))
    monkeypatch.setattr(controller, "get_window", lambda _window_id: window)

    with pytest.raises(ValueError, match="bad source"):
        controller._handle_open(1, {
            "source_id": 8,
            "source_type": "bad_type",
            "uri": "C:/demo/bad.bin",
            "autoplay": True,
        })

    assert controller._adapters[1] is previous_adapter
    assert controller._adapter_source_types[1] == "video"
    assert controller._adapter_source_ids[1] == 77
    assert window.calls == ["show", "raise", "video"]


def test_handle_open_closes_stale_ppt_before_new_source(monkeypatch: pytest.MonkeyPatch) -> None:
    """旧 PPT 未建立外部窗口时应先关闭，再打开新源，避免后端阻塞后续 open。"""
    controller = PlayerController()
    previous_adapter = _OpenAdapter()
    previous_adapter.has_external_slideshow_window = False
    new_adapter = _OpenAdapter()
    window = _WindowStub()
    calls: list[str] = []
    states: list[tuple[int, str]] = []

    def close_previous() -> None:
        """
        记录旧 PPT 关闭顺序。
        :return: None
        """
        calls.append("previous_close")
        previous_adapter.closed = True

    def open_new(uri: str, window_handle: int, autoplay: bool = True) -> None:
        """
        记录新源打开顺序。
        :param uri: 媒体 URI
        :param window_handle: 窗口句柄
        :param autoplay: 是否自动播放
        :return: None
        """
        calls.append("new_open")
        new_adapter.open_args = {"uri": uri, "window_handle": window_handle, "autoplay": autoplay}

    previous_adapter.close = close_previous  # type: ignore[method-assign]
    new_adapter.open = open_new  # type: ignore[method-assign]
    controller._adapters[1] = previous_adapter  # type: ignore[assignment]
    controller._adapter_source_types[1] = "ppt"
    controller._adapter_source_ids[1] = 77

    monkeypatch.setattr("scp_cv.player.controller_handlers.create_adapter", lambda *_args, **_kwargs: new_adapter)
    monkeypatch.setattr(controller, "get_window_handle", lambda _window_id: 2001)
    monkeypatch.setattr(controller, "get_window", lambda _window_id: window)
    monkeypatch.setattr(controller, "_cleanup_temporary_source", lambda _command_args: None)
    monkeypatch.setattr(controller, "_reheat_source_if_enabled", lambda source_id: calls.append(f"reheat:{source_id}"))
    monkeypatch.setattr(controller, "_update_session_state", lambda window_id, state: states.append((window_id, state)))

    controller._handle_open(1, {
        "source_id": 8,
        "source_type": "video",
        "uri": "C:/demo/video.mp4",
        "autoplay": True,
    })

    assert calls == ["previous_close", "new_open", "reheat:77"]
    assert previous_adapter.closed is True
    assert controller._adapters[1] is new_adapter
    assert controller._adapter_source_types[1] == "video"
    assert window.calls == ["show", "raise", "black", "black", "show", "raise", "video"]
    assert states == [(1, "playing")]


def test_handle_open_closes_previous_ppt_before_reopening_ppt(monkeypatch: pytest.MonkeyPatch) -> None:
    """PPT 切 PPT 应先释放旧放映后端，避免两个 Office/LibreOffice 打开流程竞争。"""
    controller = PlayerController()
    previous_adapter = _OpenAdapter()
    previous_adapter.has_external_slideshow_window = True
    new_adapter = _OpenAdapter()
    window = _WindowStub()
    calls: list[str] = []

    def close_previous() -> None:
        """
        记录旧 PPT 关闭顺序。
        :return: None
        """
        calls.append("previous_close")
        previous_adapter.closed = True

    def open_new(uri: str, window_handle: int, autoplay: bool = True) -> None:
        """
        记录新 PPT 打开顺序。
        :param uri: 媒体 URI
        :param window_handle: 窗口句柄
        :param autoplay: 是否自动播放
        :return: None
        """
        calls.append("new_open")
        new_adapter.open_args = {"uri": uri, "window_handle": window_handle, "autoplay": autoplay}

    previous_adapter.close = close_previous  # type: ignore[method-assign]
    new_adapter.open = open_new  # type: ignore[method-assign]
    controller._adapters[1] = previous_adapter  # type: ignore[assignment]
    controller._adapter_source_types[1] = "ppt"
    controller._adapter_source_ids[1] = 77

    monkeypatch.setattr("scp_cv.player.controller_handlers.create_adapter", lambda *_args, **_kwargs: new_adapter)
    monkeypatch.setattr(controller, "get_window_handle", lambda _window_id: 2001)
    monkeypatch.setattr(controller, "get_window", lambda _window_id: window)
    monkeypatch.setattr(controller, "_cleanup_temporary_source", lambda _command_args: None)
    monkeypatch.setattr(controller, "_reheat_source_if_enabled", lambda source_id: calls.append(f"reheat:{source_id}"))
    monkeypatch.setattr(controller, "_update_session_state", lambda _window_id, _state: None)

    controller._handle_open(1, {
        "source_id": 9,
        "source_type": "ppt",
        "uri": "C:/demo/next.pptx",
        "autoplay": True,
    })

    assert calls == ["previous_close", "new_open", "reheat:77"]
    assert previous_adapter.closed is True
    assert controller._adapters[1] is new_adapter
    assert window.calls == ["show", "raise", "black", "black", "show", "raise", "hide"]


def test_stop_polling_closes_adapters_without_reheat(monkeypatch: pytest.MonkeyPatch) -> None:
    """播放器退出时不应先重新预热当前源再立刻关闭预热池。"""
    controller = PlayerController()
    close_calls: list[tuple[int, bool]] = []

    def close_adapter(window_id: int, restore_window: bool = True, reheat: bool = True) -> None:
        """
        记录关闭参数。
        :param window_id: 窗口编号
        :param restore_window: 是否恢复窗口
        :param reheat: 是否触发重新预热
        :return: None
        """
        close_calls.append((window_id, reheat))

    controller._adapters[1] = _OpenAdapter()  # type: ignore[assignment]
    monkeypatch.setattr(controller, "_close_adapter", close_adapter)

    controller.stop_polling()

    assert close_calls == [(1, False)]


def test_handle_open_stops_stream_preheat_when_reuse_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """打开直播前即使本次禁用预热复用，也应停止后台预连接避免抢流。"""
    controller = PlayerController()
    adapter = _OpenAdapter()
    window = _WindowStub()
    states: list[tuple[int, str]] = []
    stop_stream_calls: list[int] = []

    class _FakePreheatPool:
        """记录直播预热停止调用的预热池替身。"""

        def stop_stream_preheat(self, source_id: int) -> None:
            """
            记录前台打开前释放竞争资源。
            :param source_id: 媒体源 ID
            :return: None
            """
            stop_stream_calls.append(source_id)

    monkeypatch.setattr("scp_cv.player.controller_handlers.create_adapter", lambda *_args, **_kwargs: adapter)
    monkeypatch.setattr(controller, "get_window_handle", lambda _window_id: 2001)
    monkeypatch.setattr(controller, "get_window", lambda _window_id: window)
    monkeypatch.setattr(controller, "_cleanup_temporary_source", lambda _command_args: None)
    monkeypatch.setattr(controller, "_update_session_state", lambda window_id, state: states.append((window_id, state)))
    controller._preheat_pool = _FakePreheatPool()

    controller._handle_open(1, {
        "source_id": 9,
        "source_type": "srt_stream",
        "uri": "srt://127.0.0.1:8890?streamid=read:test",
        "preheat_enabled": False,
    })

    assert stop_stream_calls == [9]
    assert states == [(1, "loading")]
    assert window.calls == ["black", "show", "raise", "video"]


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
    assert controller._adapters[1] is previous_adapter
    assert controller._adapter_source_types[1] == "ppt"
    assert controller._adapter_source_ids[1] == 77
    assert window.calls == ["hide"]


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

    controller._handle_open(1, {
        "source_id": 8,
        "source_type": "ppt",
        "uri": "C:/demo/next.pptx",
        "autoplay": True,
    })

    assert previous_adapter.closed is False
    assert new_adapter.closed is True
    assert controller._adapters[1] is previous_adapter
    assert controller._adapter_source_types[1] == "ppt"
    assert controller._adapter_source_ids[1] == 77
    assert window.calls == ["hide"]


def test_handle_open_restores_black_after_preclosed_ppt_open_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    """必须预关闭旧 PPT 后，新源打开失败时应显式恢复黑屏并重建旧源预热。"""
    controller = PlayerController()
    previous_adapter = _OpenAdapter()
    previous_adapter.has_external_slideshow_window = False
    new_adapter = _OpenAdapter()
    new_adapter.fail_open = True
    window = _WindowStub()
    calls: list[str] = []

    def close_previous() -> None:
        """
        记录旧 PPT 关闭调用。
        :return: None
        """
        calls.append("previous_close")
        previous_adapter.closed = True

    previous_adapter.close = close_previous  # type: ignore[method-assign]
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

    assert calls == ["previous_close", "reheat:77"]
    assert previous_adapter.closed is True
    assert new_adapter.closed is True
    assert controller._adapters == {}
    assert window.calls == [
        "show",
        "raise",
        "black",
        "black",
        "show",
        "raise",
        "show",
        "raise",
        "black",
    ]
