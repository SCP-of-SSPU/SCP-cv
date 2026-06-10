#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
播放器 OPEN 指令失败恢复测试，覆盖 PPT 嵌入窗口快速切源边界。
@Project : SCP-cv
@File : test_player_controller_open_recovery.py
@Author : Qintsg
@Date : 2026-05-29
'''
from __future__ import annotations

import pytest

from scp_cv.player.controller import PlayerController
from scp_cv.player import controller_handlers


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
        self.detached_for_fast_switch = False
        self.restored_after_failed_switch = False

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

    def detach_for_fast_switch(self) -> None:
        """
        记录 PPT 嵌入子窗口隐藏调用。
        :return: None
        """
        self.detached_for_fast_switch = True

    def restore_after_failed_switch(self) -> None:
        """
        记录 PPT 嵌入子窗口恢复调用。
        :return: None
        """
        self.restored_after_failed_switch = True

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
        self.topmost: list[bool] = []
        self.top_level_window_handle = 5001

    def show_black_screen(self) -> None:
        """
        记录黑屏显示。
        :return: None
        """
        self.calls.append("black")

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

    def set_always_on_top(self, enabled: bool) -> None:
        """
        记录置顶状态切换。
        :param enabled: 是否置顶
        :return: None
        """
        self.topmost.append(enabled)

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

    def prepare_ppt_container(self) -> None:
        """
        记录 PPT 嵌入容器预激活。
        :return: None
        """
        self.calls.append("ppt_container")


def test_handle_open_ignores_legacy_ppt_backend_option(monkeypatch: pytest.MonkeyPatch) -> None:
    """播放器处理 OPEN 指令时应忽略旧 ppt_backend 字段。"""
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
        "uri": "C:/demo/demo.pptx",
        "autoplay": True,
        "ppt_backend": "wps",
        "target_slide": 4,
        "volume": 88,
        "muted": True,
    })

    assert created_options == {"source_type": "ppt"}
    assert adapter.open_args == {"uri": "C:/demo/demo.pptx", "window_handle": 2001, "autoplay": True}
    assert adapter.goto_items == [4]
    assert adapter.volumes == [88]
    assert adapter.mutes == [True]
    assert controller._adapters[1] is adapter
    assert controller._adapter_source_ids[1] == 7
    assert states == [(1, "playing")]
    assert window.calls == ["black", "show", "raise", "ppt_container", "video", "show", "raise"]
    assert window.topmost == [True, True]


def test_handle_open_keeps_ppt_container_visible_when_autoplay_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """PPT 未自动放映时也应保持 PySide 嵌入容器可见稳定。"""
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
        "source_id": 7,
        "source_type": "ppt",
        "uri": "C:/demo/manual.pptx",
        "autoplay": False,
    })

    assert window.calls == ["black", "show", "raise", "ppt_container", "video", "show", "raise"]
    assert window.topmost == [True, True]
    assert states == [(1, "loading")]


def test_handle_open_restores_window_when_ppt_open_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    """PPT 打开失败时应关闭新适配器并恢复 PySide 黑屏窗口。"""
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
    assert window.calls == ["black", "show", "raise", "ppt_container", "black", "show", "raise"]
    assert window.topmost == [True, True]


def test_handle_stop_restores_black_window_for_ppt(monkeypatch: pytest.MonkeyPatch) -> None:
    """停止 PPT 后应恢复 PySide 黑屏窗口。"""
    controller = PlayerController()
    adapter = _OpenAdapter()
    window = _WindowStub()
    states: list[tuple[int, str]] = []
    stop_calls: list[bool] = []

    def stop_adapter() -> None:
        """记录 stop 调用。"""
        stop_calls.append(True)

    adapter.stop = stop_adapter  # type: ignore[method-assign]
    controller._adapters[1] = adapter  # type: ignore[assignment]
    controller._adapter_source_types[1] = "ppt"
    monkeypatch.setattr(controller, "get_window", lambda _window_id: window)
    monkeypatch.setattr(controller, "_update_session_state", lambda window_id, state: states.append((window_id, state)))

    controller._handle_stop(1, {})

    assert stop_calls == [True]
    assert window.calls == ["black", "show", "raise"]
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


def test_handle_open_detaches_previous_ppt_before_new_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PPT 切视频时应先隐藏旧嵌入子窗口，再显示新内容并延迟关闭旧 PPT。"""
    controller = PlayerController()
    previous_adapter = _OpenAdapter()
    new_adapter = _OpenAdapter()
    window = _WindowStub()
    calls: list[str] = []
    states: list[tuple[int, str]] = []

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

    previous_adapter.detach_for_fast_switch = lambda: calls.append("previous_detach")  # type: ignore[method-assign]
    new_adapter.open = open_new  # type: ignore[method-assign]
    controller._adapters[1] = previous_adapter  # type: ignore[assignment]
    controller._adapter_source_types[1] = "ppt"
    controller._adapter_source_ids[1] = 77

    monkeypatch.setattr("scp_cv.player.controller_handlers.create_adapter", lambda *_args, **_kwargs: new_adapter)
    monkeypatch.setattr(controller, "get_window_handle", lambda _window_id: 2001)
    monkeypatch.setattr(controller, "get_window", lambda _window_id: window)
    monkeypatch.setattr(controller, "_cleanup_temporary_source", lambda _command_args: None)
    monkeypatch.setattr(
        controller,
        "_schedule_close_detached_adapter",
        lambda *_args, **_kwargs: calls.append("scheduled_close"),
    )
    monkeypatch.setattr(controller, "_update_session_state", lambda window_id, state: states.append((window_id, state)))

    controller._handle_open(1, {
        "source_id": 8,
        "source_type": "video",
        "uri": "C:/demo/video.mp4",
        "autoplay": True,
    })

    assert calls == ["previous_detach", "new_open", "scheduled_close"]
    assert previous_adapter.closed is False
    assert controller._adapters[1] is new_adapter
    assert controller._adapter_source_types[1] == "video"
    assert window.calls == ["black", "show", "raise", "video"]
    assert window.topmost == [True]
    assert states == [(1, "playing")]


def test_handle_open_detaches_previous_ppt_before_reopening_ppt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PPT 切 PPT 时应先隐藏旧嵌入子窗口，新 PPT 可见后再调度关闭旧 PPT。"""
    controller = PlayerController()
    previous_adapter = _OpenAdapter()
    new_adapter = _OpenAdapter()
    window = _WindowStub()
    calls: list[str] = []

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

    previous_adapter.detach_for_fast_switch = lambda: calls.append("previous_detach")  # type: ignore[method-assign]
    new_adapter.open = open_new  # type: ignore[method-assign]
    controller._adapters[1] = previous_adapter  # type: ignore[assignment]
    controller._adapter_source_types[1] = "ppt"
    controller._adapter_source_ids[1] = 77

    monkeypatch.setattr("scp_cv.player.controller_handlers.create_adapter", lambda *_args, **_kwargs: new_adapter)
    monkeypatch.setattr(controller, "get_window_handle", lambda _window_id: 2001)
    monkeypatch.setattr(controller, "get_window", lambda _window_id: window)
    monkeypatch.setattr(controller, "_cleanup_temporary_source", lambda _command_args: None)
    monkeypatch.setattr(
        controller,
        "_schedule_close_detached_adapter",
        lambda *_args, **_kwargs: calls.append("scheduled_close"),
    )
    monkeypatch.setattr(controller, "_update_session_state", lambda _window_id, _state: None)

    controller._handle_open(1, {
        "source_id": 9,
        "source_type": "ppt",
        "uri": "C:/demo/next.pptx",
        "autoplay": True,
    })

    assert calls == ["previous_detach", "new_open", "scheduled_close"]
    assert previous_adapter.closed is False
    assert controller._adapters[1] is new_adapter
    assert window.calls == [
        "black",
        "show",
        "raise",
        "ppt_container",
        "video",
        "show",
        "raise",
    ]
    assert window.topmost == [True, True]


def test_schedule_close_detached_adapter_delays_ppt_close(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """旧 PPT 关闭应短延迟执行，给新内容先完成一次绘制。"""
    controller = PlayerController()
    adapter = _OpenAdapter()
    scheduled: list[tuple[int, object]] = []
    close_calls: list[tuple[int, str | None]] = []
    monkeypatch.setattr(
        "scp_cv.player.controller_handlers.QTimer.singleShot",
        lambda delay_ms, callback: scheduled.append((delay_ms, callback)),
    )
    monkeypatch.setattr(
        controller,
        "_close_detached_adapter",
        lambda window_id, _adapter, source_type, *_args: close_calls.append(
            (window_id, source_type)
        ),
    )

    controller._schedule_close_detached_adapter(
        1,
        adapter,
        "ppt",
        7,
        restore_window=False,
        reheat=True,
    )

    assert scheduled[0][0] == controller_handlers._PPT_DETACHED_CLOSE_DELAY_MS
    assert close_calls == []

    scheduled[0][1]()

    assert close_calls == [(1, "ppt")]


def test_schedule_close_detached_adapter_keeps_non_ppt_immediate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """非 PPT 旧适配器关闭保持下一轮事件循环执行，不引入额外等待。"""
    controller = PlayerController()
    scheduled: list[int] = []
    monkeypatch.setattr(
        "scp_cv.player.controller_handlers.QTimer.singleShot",
        lambda delay_ms, _callback: scheduled.append(delay_ms),
    )

    controller._schedule_close_detached_adapter(
        1,
        _OpenAdapter(),
        "video",
        8,
        restore_window=False,
        reheat=True,
    )

    assert scheduled == [0]


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
    assert window.calls == ["black", "show", "raise", "video", "show", "raise", "video"]


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
