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

import pytest

from tests.player_controller_ppt_async_test_support import (
    _AsyncPptAdapter,
    _make_controller,
)


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
    assert adapter.volumes == [66]
    assert adapter.mutes == [True]
    assert controller._adapters[1] is adapter
    assert controller._adapter_source_types[1] == "ppt"
    assert controller._adapter_source_ids[1] == 7
    assert controller._pending_ppt_opens == {}
    assert states == [(1, "loading"), (1, "playing")]
    assert errors == []
    assert window.calls == ["black", "show", "raise", "ppt_container", "video", "show", "raise"]


def test_async_ppt_open_failure_restores_previous_adapter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """打开失败时应释放新适配器、恢复旧适配器并写入错误状态。"""
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
    assert previous_adapter.detached is True
    assert previous_adapter.restored is True
    assert controller._adapters[1] is previous_adapter
    assert controller._adapter_source_ids[1] == 77
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
