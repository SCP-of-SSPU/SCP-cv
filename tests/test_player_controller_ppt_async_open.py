#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
播放器 PPT 异步打开流程测试：完成回调收尾、失败恢复、打开期间指令排队。
@Project : SCP-cv
@File : test_player_controller_ppt_async_open.py
@Author : Qintsg
@Date : 2026-06-10
'''
from __future__ import annotations

from typing import Callable, Optional

import pytest

from scp_cv.player.controller import PlayerController


class _AsyncPptAdapter:
    """支持 open_async 的 PPT 适配器替身，可手动触发完成回调。"""

    def __init__(self, finish_immediately: bool = False, error: Exception | None = None) -> None:
        """
        初始化替身。
        :param finish_immediately: open_async 内是否立即同步回调
        :param error: 立即回调时上报的异常；None 表示成功
        :return: None
        """
        self.finish_immediately = finish_immediately
        self.error = error
        self.open_async_args: dict[str, object] = {}
        self.com_workers: list[object] = []
        self.on_finished: Optional[Callable[[Optional[BaseException]], None]] = None
        self.closed = False
        self.close_count = 0
        self.detached = False
        self.restored = False
        self.volumes: list[int] = []
        self.mutes: list[bool] = []

    def set_com_worker(self, com_worker: object) -> None:
        """
        记录注入的 COM 工作线程。
        :param com_worker: worker 或 None
        :return: None
        """
        self.com_workers.append(com_worker)

    def open_async(
        self,
        uri: str,
        window_handle: int,
        autoplay: bool = True,
        start_slide: int = 0,
        on_finished: Optional[Callable[[Optional[BaseException]], None]] = None,
    ) -> None:
        """
        记录打开参数；按配置立即回调或交由测试手动触发。
        :param uri: 媒体 URI
        :param window_handle: 窗口句柄
        :param autoplay: 是否自动播放
        :param start_slide: 起始页码
        :param on_finished: 完成回调
        :return: None
        """
        self.open_async_args = {
            "uri": uri,
            "window_handle": window_handle,
            "autoplay": autoplay,
            "start_slide": start_slide,
        }
        self.on_finished = on_finished
        if self.finish_immediately and on_finished is not None:
            on_finished(self.error)

    def close(self) -> None:
        """记录关闭调用。"""
        self.closed = True
        self.close_count += 1

    def detach_for_fast_switch(self) -> None:
        """记录嵌入窗口隐藏调用。"""
        self.detached = True

    def restore_after_failed_switch(self) -> None:
        """记录嵌入窗口恢复调用。"""
        self.restored = True

    def set_volume(self, volume: int) -> None:
        """
        记录音量设置。
        :param volume: 音量
        :return: None
        """
        self.volumes.append(volume)

    def set_mute(self, muted: bool) -> None:
        """
        记录静音设置。
        :param muted: 是否静音
        :return: None
        """
        self.mutes.append(muted)


class _WindowStub:
    """记录窗口显示调用的替身。"""

    def __init__(self) -> None:
        """初始化记录。"""
        self.calls: list[str] = []
        self.topmost: list[bool] = []
        self.web_container = object()
        self.top_level_window_handle = 5001

    def show_black_screen(self) -> None:
        self.calls.append("black")

    def show(self) -> None:
        self.calls.append("show")

    def raise_(self) -> None:
        self.calls.append("raise")

    def set_always_on_top(self, enabled: bool) -> None:
        self.topmost.append(enabled)

    def show_web_container(self) -> None:
        self.calls.append("web")

    def show_video_container(self) -> None:
        self.calls.append("video")

    def prepare_ppt_container(self) -> None:
        self.calls.append("ppt_container")


def _make_controller(monkeypatch: pytest.MonkeyPatch, adapter: object) -> tuple[PlayerController, _WindowStub, list[tuple[int, str]], list[tuple[int, str]]]:
    """
    构造带桩的控制器。
    :param monkeypatch: pytest monkeypatch
    :param adapter: create_adapter 返回的适配器替身
    :return: (controller, window, states, errors)
    """
    controller = PlayerController()
    window = _WindowStub()
    states: list[tuple[int, str]] = []
    errors: list[tuple[int, str]] = []

    monkeypatch.setattr(
        "scp_cv.player.controller_handlers.create_adapter",
        lambda *_args, **_kwargs: adapter,
    )
    monkeypatch.setattr(controller, "get_window_handle", lambda _window_id: 2001)
    monkeypatch.setattr(controller, "get_window", lambda _window_id: window)
    monkeypatch.setattr(controller, "_cleanup_temporary_source", lambda _command_args: None)
    monkeypatch.setattr(
        controller,
        "_update_session_state",
        lambda window_id, state: states.append((window_id, state)),
    )
    monkeypatch.setattr(
        controller,
        "_update_session_error",
        lambda window_id, message: errors.append((window_id, message)),
    )
    return controller, window, states, errors


def test_async_ppt_open_success_registers_adapter_after_completion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """open_async 成功回调后才注册适配器并切到放映容器。"""
    adapter = _AsyncPptAdapter(finish_immediately=True)
    controller, window, states, errors = _make_controller(monkeypatch, adapter)

    controller._handle_open(1, {
        "source_id": 7,
        "source_type": "ppt",
        "uri": "C:/demo/demo.pptx",
        "autoplay": True,
        "target_slide": 4,
        "volume": 66,
        "muted": True,
    })

    assert adapter.open_async_args == {
        "uri": "C:/demo/demo.pptx",
        "window_handle": 2001,
        "autoplay": True,
        "start_slide": 4,
    }
    assert adapter.com_workers == [None]
    assert adapter.volumes == [66]
    assert adapter.mutes == [True]
    assert controller._adapters[1] is adapter
    assert controller._adapter_source_types[1] == "ppt"
    assert controller._adapter_source_ids[1] == 7
    assert controller._pending_ppt_opens == {}
    assert states == [(1, "loading"), (1, "playing")]
    assert errors == []
    assert window.calls == ["black", "show", "raise", "ppt_container", "video", "show", "raise"]


def test_ppt_to_ppt_switch_closes_previous_slideshow_before_opening_next(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PowerPoint 单实例不能可靠并行 Run；PPT 切 PPT 必须先关闭旧放映再打开新放映。"""
    events: list[str] = []
    previous_adapter = _AsyncPptAdapter()
    new_adapter = _AsyncPptAdapter()
    controller, _window, _states, _errors = _make_controller(monkeypatch, new_adapter)
    controller._adapters[1] = previous_adapter  # type: ignore[assignment]
    controller._adapter_source_types[1] = "ppt"
    controller._adapter_source_ids[1] = 77

    previous_adapter.close = lambda: events.append("previous_close")  # type: ignore[method-assign]

    def open_next(
        uri: str,
        window_handle: int,
        autoplay: bool = True,
        start_slide: int = 0,
        on_finished: Optional[Callable[[Optional[BaseException]], None]] = None,
    ) -> None:
        events.append("next_open")
        if on_finished is not None:
            on_finished(None)

    new_adapter.open_async = open_next  # type: ignore[method-assign]
    reheated: list[tuple[int, int]] = []
    monkeypatch.setattr(
        controller,
        "_schedule_reheat_source_if_enabled",
        lambda window_id, source_id: reheated.append((window_id, source_id)),
    )

    controller._handle_open(1, {
        "source_id": 8,
        "source_type": "ppt",
        "uri": "C:/demo/next.pptx",
        "autoplay": True,
    })

    assert events == ["previous_close", "next_open"]
    assert reheated == []
    assert controller._adapters[1] is new_adapter


def test_async_ppt_to_ppt_open_failure_does_not_restore_closed_previous_adapter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PPT 切 PPT 已先关闭旧放映；新源失败时应保持黑屏并明确上报错误。"""
    previous_adapter = _AsyncPptAdapter()
    new_adapter = _AsyncPptAdapter(finish_immediately=True, error=RuntimeError("ppt broken"))
    controller, window, states, errors = _make_controller(monkeypatch, new_adapter)
    controller._adapters[1] = previous_adapter  # type: ignore[assignment]
    controller._adapter_source_types[1] = "ppt"
    controller._adapter_source_ids[1] = 77

    controller._handle_open(1, {
        "source_id": 8,
        "source_type": "ppt",
        "uri": "C:/demo/fail.pptx",
        "autoplay": True,
    })

    assert new_adapter.closed is True
    assert previous_adapter.closed is True
    assert previous_adapter.restored is False
    assert controller._adapters == {}
    assert controller._pending_ppt_opens == {}
    assert states == [(1, "loading")]
    assert errors == [(1, "ppt broken")]


def test_commands_are_deferred_until_async_open_completes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """打开进行中时同窗口指令应排队，完成后按序重放。"""
    from scp_cv.apps.playback.models import PlaybackCommand

    adapter = _AsyncPptAdapter(finish_immediately=False)
    controller, window, states, errors = _make_controller(monkeypatch, adapter)
    goto_calls: list[int] = []
    adapter.goto_item = goto_calls.append  # type: ignore[attr-defined]

    controller._handle_open(1, {
        "source_id": 7,
        "source_type": "ppt",
        "uri": "C:/demo/slow.pptx",
        "autoplay": True,
    })

    assert 1 in controller._pending_ppt_opens
    # 打开期间到达的 GOTO 应排队而不是立即执行
    controller._execute_command_on_main_thread(1, PlaybackCommand.GOTO, {"target_index": 3})
    assert goto_calls == []
    assert controller._pending_ppt_opens[1].deferred == [
        (PlaybackCommand.GOTO, {"target_index": 3}),
    ]

    # 完成回调后：注册适配器并重放排队指令
    assert adapter.on_finished is not None
    adapter.on_finished(None)

    assert controller._adapters[1] is adapter
    assert goto_calls == [3]
    assert controller._pending_ppt_opens == {}
    assert states == [(1, "loading"), (1, "playing")]


def test_second_open_supersedes_inflight_ppt_open(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """打开期间再次 OPEN 应取代在途打开：旧请求适配器被释放，新 OPEN 重放执行。"""
    from scp_cv.apps.playback.models import PlaybackCommand

    first_adapter = _AsyncPptAdapter(finish_immediately=False)
    second_adapter = _AsyncPptAdapter(finish_immediately=True)
    adapters = iter([first_adapter, second_adapter])
    controller, window, states, errors = _make_controller(monkeypatch, first_adapter)
    monkeypatch.setattr(
        "scp_cv.player.controller_handlers.create_adapter",
        lambda *_args, **_kwargs: next(adapters),
    )

    controller._handle_open(1, {
        "source_id": 7,
        "source_type": "ppt",
        "uri": "C:/demo/first.pptx",
        "autoplay": True,
    })
    controller._execute_command_on_main_thread(1, PlaybackCommand.OPEN, {
        "source_id": 9,
        "source_type": "ppt",
        "uri": "C:/demo/second.pptx",
        "autoplay": True,
    })

    assert controller._pending_ppt_opens[1].superseded is True

    assert first_adapter.on_finished is not None
    first_adapter.on_finished(None)

    assert first_adapter.closed is True
    assert controller._adapters[1] is second_adapter
    assert controller._adapter_source_ids[1] == 9
    assert controller._pending_ppt_opens == {}


def test_abort_pending_ppt_opens_marks_superseded_and_clears_queue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """全局重置/退出前应取消在途打开并清空积压指令。"""
    from scp_cv.apps.playback.models import PlaybackCommand

    adapter = _AsyncPptAdapter(finish_immediately=False)
    controller, window, states, errors = _make_controller(monkeypatch, adapter)

    controller._handle_open(1, {
        "source_id": 7,
        "source_type": "ppt",
        "uri": "C:/demo/slow.pptx",
        "autoplay": True,
    })
    controller._execute_command_on_main_thread(1, PlaybackCommand.PAUSE, {})

    controller._abort_pending_ppt_opens()
    entry = controller._pending_ppt_opens[1]
    assert entry.superseded is True
    assert entry.deferred == []
    # 资源释放不依赖 Qt 完成回调：abort 时已直接调度 adapter.close
    assert adapter.closed is True
    assert adapter.close_count == 1

    assert adapter.on_finished is not None
    adapter.on_finished(None)

    # 完成回调到达时不再重复关闭
    assert adapter.close_count == 1
    assert controller._adapters == {}
    assert controller._pending_ppt_opens == {}


def test_close_during_open_supersedes_and_replays_without_playing_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """加载中点 CLOSE：取代在途打开，完成后不得写 playing，CLOSE 按序重放。"""
    from scp_cv.apps.playback.models import PlaybackCommand

    adapter = _AsyncPptAdapter(finish_immediately=False)
    controller, window, states, errors = _make_controller(monkeypatch, adapter)
    close_calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        controller,
        "_handle_close",
        lambda _window_id, command_args: close_calls.append(dict(command_args)),
    )

    controller._handle_open(1, {
        "source_id": 7,
        "source_type": "ppt",
        "uri": "C:/demo/slow.pptx",
        "autoplay": True,
    })
    controller._execute_command_on_main_thread(1, PlaybackCommand.CLOSE, {})

    entry = controller._pending_ppt_opens[1]
    assert entry.superseded is True
    assert close_calls == []

    assert adapter.on_finished is not None
    adapter.on_finished(None)

    # 在途适配器被释放且不注册；会话状态只有 loading，不得复活为 playing
    assert adapter.closed is True
    assert controller._adapters == {}
    assert states == [(1, "loading")]
    # CLOSE 在完成后按序重放
    assert close_calls == [{}]


def test_reset_command_deferred_during_open_is_not_deduplicated_on_replay(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """加载中收到带 reset_token 的指令：排队阶段不记录 token，重放时应正常执行。"""
    from scp_cv.apps.playback.models import PlaybackCommand
    from scp_cv.services.playback import RESET_TOKEN_ARG

    adapter = _AsyncPptAdapter(finish_immediately=False)
    controller, window, states, errors = _make_controller(monkeypatch, adapter)
    reset_calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        controller,
        "_handle_reset_ppt",
        lambda _window_id, command_args: reset_calls.append(dict(command_args)),
    )

    controller._handle_open(1, {
        "source_id": 7,
        "source_type": "ppt",
        "uri": "C:/demo/slow.pptx",
        "autoplay": True,
    })
    reset_args = {RESET_TOKEN_ARG: "token-1", "restart_sessions": []}
    controller._execute_command_on_main_thread(1, PlaybackCommand.RESET_PPT, dict(reset_args))

    # 排队阶段不得记录 reset token，否则重放会被误判为重复广播
    assert controller._last_reset_ppt_token == ""
    assert reset_calls == []

    assert adapter.on_finished is not None
    adapter.on_finished(None)

    assert reset_calls == [reset_args]
    assert controller._last_reset_ppt_token == "token-1"


def test_terminal_command_compacts_deferred_queue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """终止/替换类指令入队时应清空之前排队的普通指令，只保留本条。"""
    from scp_cv.apps.playback.models import PlaybackCommand

    adapter = _AsyncPptAdapter(finish_immediately=False)
    controller, window, states, errors = _make_controller(monkeypatch, adapter)

    controller._handle_open(1, {
        "source_id": 7,
        "source_type": "ppt",
        "uri": "C:/demo/slow.pptx",
        "autoplay": True,
    })
    for target_index in (2, 3, 4):
        controller._execute_command_on_main_thread(
            1, PlaybackCommand.GOTO, {"target_index": target_index}
        )
    controller._execute_command_on_main_thread(1, PlaybackCommand.CLOSE, {})

    entry = controller._pending_ppt_opens[1]
    assert entry.superseded is True
    assert entry.deferred == [(PlaybackCommand.CLOSE, {})]


def test_overflow_never_evicts_terminal_command(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """普通指令积压超限时只淘汰普通指令，CLOSE/OPEN 等终止类必须保留。"""
    from scp_cv.apps.playback.models import PlaybackCommand
    from scp_cv.player.controller_ppt_open import _MAX_DEFERRED_COMMANDS

    adapter = _AsyncPptAdapter(finish_immediately=False)
    controller, window, states, errors = _make_controller(monkeypatch, adapter)

    controller._handle_open(1, {
        "source_id": 7,
        "source_type": "ppt",
        "uri": "C:/demo/slow.pptx",
        "autoplay": True,
    })
    controller._execute_command_on_main_thread(1, PlaybackCommand.CLOSE, {})
    for target_index in range(1, _MAX_DEFERRED_COMMANDS + 3):
        controller._execute_command_on_main_thread(
            1, PlaybackCommand.GOTO, {"target_index": target_index}
        )

    entry = controller._pending_ppt_opens[1]
    assert entry.deferred[0] == (PlaybackCommand.CLOSE, {})
    assert len(entry.deferred) == _MAX_DEFERRED_COMMANDS
    # 淘汰的是最早的普通指令，最新指令保留在队尾
    assert entry.deferred[-1] == (
        PlaybackCommand.GOTO,
        {"target_index": _MAX_DEFERRED_COMMANDS + 2},
    )
