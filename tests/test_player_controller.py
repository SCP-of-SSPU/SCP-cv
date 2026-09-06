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

from scp_cv.apps.playback.models import MediaSource, PlaybackCommand, PlaybackState, SourceType
from scp_cv.player.adapters.base import AdapterState
from scp_cv.player.controller import PlayerController
from scp_cv.services.playback import (
    RESET_ALL_WINDOWS_ARG,
    get_or_create_session,
    get_session_snapshot,
    open_source,
)


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
    """记录打开流程的 adapter 替身。"""

    def __init__(self) -> None:
        """
        初始化调用记录。
        :return: None
        """
        self.opened = False

    def open(self, uri: str, window_handle: int, autoplay: bool = True) -> None:
        """
        标记媒体源已打开。
        :param uri: 媒体 URI
        :param window_handle: 播放窗口句柄
        :param autoplay: 是否自动播放
        :return: None
        """
        self.opened = bool(uri and window_handle and autoplay)

    def goto_item(self, index: int) -> None:
        """
        测试中无需执行翻页。
        :param index: 目标页码
        :return: None
        """
        return

    def set_volume(self, volume: int) -> None:
        """
        测试中无需设置音量。
        :param volume: 音量
        :return: None
        """
        return

    def set_mute(self, muted: bool) -> None:
        """
        测试中无需设置静音。
        :param muted: 是否静音
        :return: None
        """
        return

    def close(self) -> None:
        """
        测试中无需释放资源。
        :return: None
        """
        return


class _WindowStub:
    """播放器窗口替身。"""

    def show_black_screen(self) -> None:
        """
        测试中无需渲染黑屏。
        :return: None
        """
        return

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

    def show_video_container(self) -> None:
        """
        测试中无需切换视频容器。
        :return: None
        """
        return

    def show_web_container(self) -> None:
        """
        测试中无需切换网页容器。
        :return: None
        """
        return


class _SingleLoopController(PlayerController):
    """只执行一轮轮询的控制器替身，用于验证线程边界调度。"""

    def __init__(self) -> None:
        """
        初始化测试控制器状态。
        :return: None
        """
        super().__init__()
        self.checked_windows: list[int] = []
        self.checked_background_audio = False
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

    def _check_and_dispatch_background_audio_command(self) -> None:
        """记录背景音频轮询，避免该线程边界测试访问数据库。"""
        self.checked_background_audio = True

    def _touch_player_heartbeats_if_due(self) -> None:
        """该线程边界测试不访问数据库。"""
        return

    def _request_adapter_state_report(self) -> None:
        """记录状态上报请求，并结束轮询。"""
        self.report_requested = True
        self._poll_running = False

    def _report_all_adapter_states(self) -> None:
        """轮询线程不应直接调用真实状态读取。"""
        raise AssertionError("adapter state must be reported through the Qt signal")


def test_poll_loop_requests_state_report_instead_of_reading_adapter_directly() -> None:
    """后台轮询应只发起状态上报请求，避免跨线程访问 PPT COM。"""
    controller = _SingleLoopController()
    controller._poll_running = True

    with patch("scp_cv.player.controller_polling.time.sleep", return_value=None):
        controller._poll_loop(interval_seconds=0)

    assert controller.checked_windows == [1]
    assert controller.checked_background_audio is True
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


@pytest.mark.django_db
def test_open_confirms_session_source_after_stale_close_cleared_it(
    media_source_ppt: MediaSource,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """OPEN 成功后应修复慢速 CLOSE 延迟清空的会话源关系。"""
    adapter = _OpenAdapter()
    controller = PlayerController()
    monkeypatch.setattr("scp_cv.player.controller_handlers.create_adapter", lambda _source_type, **_options: adapter)
    monkeypatch.setattr(controller, "get_window_handle", lambda _window_id: 2001)
    monkeypatch.setattr(controller, "get_window", lambda _window_id: _WindowStub())
    get_or_create_session(1)

    controller._handle_open(1, {
        "source_id": media_source_ppt.pk,
        "source_type": SourceType.PPT,
        "uri": media_source_ppt.uri,
        "autoplay": True,
        "target_slide": 1,
    })

    snapshot = get_session_snapshot(1)
    assert adapter.opened is True
    assert snapshot["source_id"] == media_source_ppt.pk
    assert snapshot["source_type"] == SourceType.PPT
    assert snapshot["playback_state"] == PlaybackState.PLAYING


@pytest.mark.django_db
def test_reheat_skips_temporary_source() -> None:
    """临时源切离后会被删除，不应重新建立后台预热。"""
    controller = PlayerController()
    preheated: list[tuple[int, str, str]] = []
    source = MediaSource.objects.create(
        source_type=SourceType.VIDEO,
        name="临时视频",
        uri="C:/demo/temp.mp4",
        is_available=True,
        is_temporary=True,
        keep_alive=True,
    )

    class _FakePreheatPool:
        """记录预热请求的预热池替身。"""

        def preheat_source(self, source_id: int, source_type: str, uri: str, force: bool = False) -> None:
            """
            记录预热请求。
            :param source_id: 媒体源 ID
            :param source_type: 媒体源类型
            :param uri: 媒体 URI
            :param force: 是否强制重建
            :return: None
            """
            preheated.append((source_id, source_type, uri))

    controller._preheat_pool = _FakePreheatPool()

    controller._reheat_source_if_enabled(source.pk)

    assert preheated == []


@pytest.mark.django_db
def test_reheat_web_source_keeps_returned_preheated_view() -> None:
    """网页源切走后 WebView 已归还预热池，不应 force 重载导致登录态丢失。"""
    controller = PlayerController()
    preheated: list[tuple[int, str, bool]] = []
    source = MediaSource.objects.create(
        source_type=SourceType.WEB,
        name="网页看板",
        uri="http://example.local",
        is_available=True,
        keep_alive=True,
    )

    class _FakePreheatPool:
        """记录预热请求的预热池替身。"""

        def preheat_source(self, source_id: int, source_type: str, uri: str, force: bool = False) -> None:
            """
            记录预热请求。
            :param source_id: 媒体源 ID
            :param source_type: 媒体源类型
            :param uri: 媒体 URI
            :param force: 是否强制重建
            :return: None
            """
            preheated.append((source_id, source_type, force))

    controller._preheat_pool = _FakePreheatPool()

    controller._reheat_source_if_enabled(source.pk)

    assert preheated == [(source.pk, SourceType.WEB, False)]


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

    class _FakePreheatPool:
        """统一预热池替身，记录释放调用。"""

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
    controller._preheat_pool = _FakePreheatPool()
    monkeypatch.setattr(controller, "apply_current_layout", lambda: layout_applied.append(True))
    monkeypatch.setattr(controller, "preheat_sources", lambda: preheated.append(True))

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


def test_reset_broadcast_token_is_consumed_once_in_single_process(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """单进程调试路径收到同一 reset 广播时应只执行一次。"""
    controller = PlayerController()
    reset_all_calls: list[int] = []
    reset_ppt_calls: list[int] = []

    monkeypatch.setattr(
        controller,
        "_handle_reset_all_windows",
        lambda: reset_all_calls.append(1),
    )
    monkeypatch.setattr(
        controller,
        "_handle_reset_ppt",
        lambda window_id, _args: reset_ppt_calls.append(window_id),
    )

    controller._execute_command_on_main_thread(
        1,
        PlaybackCommand.CLOSE,
        {RESET_ALL_WINDOWS_ARG: True, "reset_token": "all-1"},
    )
    controller._execute_command_on_main_thread(
        2,
        PlaybackCommand.CLOSE,
        {RESET_ALL_WINDOWS_ARG: True, "reset_token": "all-1"},
    )
    controller._execute_command_on_main_thread(
        1,
        PlaybackCommand.RESET_PPT,
        {"restart_sessions": [], "reset_token": "ppt-1"},
    )
    controller._execute_command_on_main_thread(
        2,
        PlaybackCommand.RESET_PPT,
        {"restart_sessions": [], "reset_token": "ppt-1"},
    )

    assert reset_all_calls == [1]
    assert reset_ppt_calls == [1]
