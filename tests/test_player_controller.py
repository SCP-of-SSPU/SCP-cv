#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
播放器控制器测试，覆盖轮询线程与 Qt 主线程的状态上报边界。
@Project : SCP-cv
@File : test_player_controller.py
@Author : Qintsg
@Date : 2026-04-30
'''
from __future__ import annotations

from unittest.mock import patch

import pytest

from scp_cv.apps.playback.models import MediaSource, PlaybackState
from scp_cv.player.adapters.base import AdapterState
from scp_cv.player.controller import PlayerController
from scp_cv.services.playback import RESET_ALL_WINDOWS_ARG, get_session_snapshot, open_source


class _StateAdapter:
    """返回固定状态的 adapter 替身，用于验证状态写回保护。"""

    def __init__(self, adapter_state: AdapterState) -> None:
        """
        初始化 adapter 替身。
        :param adapter_state: get_state 要返回的状态快照
        :return: None
        """
        self.is_open = True
        self.adapter_state = adapter_state
        self.read_count = 0

    def get_state(self) -> AdapterState:
        """
        返回固定状态并记录读取次数。
        :return: 预置的 adapter 状态
        """
        self.read_count += 1
        return self.adapter_state


class _OpenAdapter:
    """记录 OPEN 流程调用的 adapter 替身。"""

    def __init__(self) -> None:
        """
        初始化调用记录。
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
        记录打开参数。
        :param uri: 媒体 URI
        :param window_handle: 窗口句柄
        :param autoplay: 是否自动播放
        :return: None
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
        记录音量参数。
        :param volume: 音量
        :return: None
        """
        self.volumes.append(volume)

    def set_mute(self, muted: bool) -> None:
        """
        记录静音参数。
        :param muted: 是否静音
        :return: None
        """
        self.mutes.append(muted)


class _SingleLoopController(PlayerController):
    """只执行一轮轮询的控制器替身，用于验证线程边界调度。"""

    def __init__(self) -> None:
        """
        初始化测试控制器状态。
        :return: None
        """
        super().__init__()
        self.checked_windows: list[int] = []
        self.report_requested = False

    @property
    def registered_window_ids(self) -> list[int]:
        """返回固定窗口，避免依赖真实播放器窗口注册。"""
        return [1]

    def _check_and_dispatch_command(self, window_id: int) -> None:
        """
        记录被轮询的窗口。
        :param window_id: 窗口编号
        :return: None
        """
        self.checked_windows.append(window_id)

    def _request_adapter_state_report(self) -> None:
        """记录状态上报请求，并结束轮询。"""
        self.report_requested = True
        self._poll_running = False

    def _report_all_adapter_states(self) -> None:
        """轮询线程不应直接调用真实状态读取。"""
        raise AssertionError("adapter state must be reported through the Qt signal")


class _WindowStub:
    """记录播放器窗口显示/隐藏调用顺序的替身。"""

    def __init__(self) -> None:
        """
        初始化调用记录。
        :return: None
        """
        self.calls: list[str] = []
        self.web_container = object()

    def show_black_screen(self) -> None:
        """记录黑屏显示。"""
        self.calls.append("black")

    def hide_window(self) -> None:
        """记录隐藏窗口。"""
        self.calls.append("hide")

    def show(self) -> None:
        """记录显示窗口。"""
        self.calls.append("show")

    def raise_(self) -> None:
        """记录置顶窗口。"""
        self.calls.append("raise")

    def show_web_container(self) -> None:
        """记录网页容器显示。"""
        self.calls.append("web")

    def show_video_container(self) -> None:
        """记录视频容器显示。"""
        self.calls.append("video")


def test_poll_loop_requests_state_report_instead_of_reading_adapter_directly() -> None:
    """后台轮询应只发起状态上报请求，避免跨线程访问 PPT COM。"""
    controller = _SingleLoopController()
    controller._poll_running = True

    with patch("scp_cv.player.controller.time.sleep", return_value=None):
        controller._poll_loop(interval_seconds=0)

    assert controller.checked_windows == [1]
    assert controller.report_requested is True


@pytest.mark.django_db
def test_report_skips_stale_adapter_after_source_change(
    media_source_ppt: MediaSource,
    media_source_video: MediaSource,
) -> None:
    """切源后旧 adapter 的延迟错误状态不应覆盖新会话。"""
    open_source(1, media_source_ppt.pk)
    open_source(1, media_source_video.pk)

    controller = PlayerController()
    adapter = _StateAdapter(AdapterState(playback_state=PlaybackState.ERROR))
    controller._adapters[1] = adapter
    controller._adapter_source_ids[1] = media_source_ppt.pk

    controller._report_all_adapter_states()

    session = media_source_video.playback_sessions.get(window_id=1)
    assert session.playback_state == PlaybackState.LOADING
    assert adapter.read_count == 0


@pytest.mark.django_db
def test_report_persists_adapter_error_message(media_source_video: MediaSource) -> None:
    """适配器错误详情应进入会话快照，避免前端只能显示泛化提示。"""
    open_source(1, media_source_video.pk)

    controller = PlayerController()
    adapter = _StateAdapter(AdapterState(
        playback_state=PlaybackState.ERROR,
        error_message="libVLC 播放 SRT 流失败",
    ))
    controller._adapters[1] = adapter
    controller._adapter_source_ids[1] = media_source_video.pk

    controller._report_all_adapter_states()

    session = media_source_video.playback_sessions.get(window_id=1)
    snapshot = get_session_snapshot(1)
    assert session.playback_state == PlaybackState.ERROR
    assert session.error_message == "libVLC 播放 SRT 流失败"
    assert snapshot["error_message"] == "libVLC 播放 SRT 流失败"


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


@pytest.mark.django_db
def test_reset_all_windows_command_rebuilds_player_runtime(
    media_source_video: MediaSource,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """全局 reset 指令应关闭全部资源、替换窗口并重新执行网页预热。"""
    closed_adapters: list[int] = []
    closed_windows: list[int] = []
    created_windows: list[int] = []
    preheat_pool_closed: list[bool] = []
    layout_applied: list[bool] = []
    preheated: list[bool] = []
    close_callbacks: list[object] = []
    quit_on_last_window_values: list[bool] = []

    class _FakeSignal:
        """记录窗口关闭信号连接的测试替身。"""

        def connect(self, callback: object) -> None:
            """
            记录连接的回调。
            :param callback: 回调对象
            :return: None
            """
            close_callbacks.append(callback)

        def disconnect(self, callback: object) -> None:
            """
            记录断开请求；PySide 信号测试中无需真实解绑。
            :param callback: 回调对象
            :return: None
            """
            return

    class _FakePlayerWindow:
        """播放器窗口替身，用于避免测试创建真实 QWidget。"""

        def __init__(self, window_id: int, debug_mode: bool = False) -> None:
            """
            初始化测试窗口。
            :param window_id: 窗口编号
            :param debug_mode: 是否调试模式
            :return: None
            """
            self.window_id = window_id
            self.debug_mode = debug_mode
            self.window_closed = _FakeSignal()
            created_windows.append(window_id)

        def stop_all(self) -> None:
            """
            测试中无需渲染黑屏。
            :return: None
            """
            return

        def close_for_rebuild(self) -> None:
            """
            记录窗口被全局重置关闭。
            :return: None
            """
            closed_windows.append(self.window_id)

        def resize(self, width: int, height: int) -> None:
            """
            记录调试窗口尺寸接口存在。
            :param width: 宽度
            :param height: 高度
            :return: None
            """
            return

        def show(self) -> None:
            """
            记录显示接口存在。
            :return: None
            """
            return

    class _FakeAdapter:
        """播放适配器替身，记录 close 调用。"""

        def __init__(self, window_id: int) -> None:
            """
            初始化适配器替身。
            :param window_id: 窗口编号
            :return: None
            """
            self.window_id = window_id

        def close(self) -> None:
            """
            记录适配器关闭。
            :return: None
            """
            closed_adapters.append(self.window_id)

    class _FakeWebPreheatPool:
        """网页预热池替身，记录释放调用。"""

        def close_all(self) -> None:
            """
            记录预热池关闭。
            :return: None
            """
            preheat_pool_closed.append(True)

    class _FakeQtApp:
        """Qt 应用替身，记录窗口重建期间的自动退出保护。"""

        def quitOnLastWindowClosed(self) -> bool:
            """
            返回原自动退出设置。
            :return: True 表示最后窗口关闭会退出
            """
            return True

        def setQuitOnLastWindowClosed(self, enabled: bool) -> None:
            """
            记录自动退出设置变更。
            :param enabled: 是否启用最后窗口关闭即退出
            :return: None
            """
            quit_on_last_window_values.append(enabled)

    monkeypatch.setattr("scp_cv.player.window.PlayerWindow", _FakePlayerWindow)
    monkeypatch.setattr(
        "PySide6.QtWidgets.QApplication.instance",
        lambda: _FakeQtApp(),
    )
    open_source(1, media_source_video.pk)
    open_source(2, media_source_video.pk)

    controller = PlayerController()
    controller.set_window_closed_callback(lambda: None)
    controller.register_window(1, _FakePlayerWindow(1))
    controller.register_window(2, _FakePlayerWindow(2))
    controller._adapters[1] = _FakeAdapter(1)
    controller._adapters[2] = _FakeAdapter(2)
    controller._adapter_source_types[1] = "video"
    controller._adapter_source_ids[1] = media_source_video.pk
    controller._last_reported_states[1] = (PlaybackState.PLAYING, "", 0, 0, 1, 2)
    controller._web_preheat_pool = _FakeWebPreheatPool()
    monkeypatch.setattr(controller, "apply_current_layout", lambda: layout_applied.append(True))
    monkeypatch.setattr(controller, "preheat_web_sources", lambda: preheated.append(True))

    controller._handle_close(1, {RESET_ALL_WINDOWS_ARG: True})

    assert closed_adapters == [1, 2]
    assert preheat_pool_closed == [True]
    assert closed_windows == [1, 2]
    assert created_windows == [1, 2, 1, 2]
    assert controller.registered_window_ids == [1, 2]
    assert controller._adapter_source_types == {}
    assert controller._adapter_source_ids == {}
    assert controller._last_reported_states == {}
    assert layout_applied == [True]
    assert preheated == [True]
    assert len(close_callbacks) == 4
    assert quit_on_last_window_values == [False, True]
