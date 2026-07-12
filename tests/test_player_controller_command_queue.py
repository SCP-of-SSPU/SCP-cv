#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
播放器控制器持久化命令领取、确认与背景音频测试。
@Project : SCP-cv
@File : test_player_controller_command_queue.py
@Author : Qintsg
@Date : 2026-07-11
'''
from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone

from scp_cv.apps.playback.models import (
    BackgroundAudioCommand,
    BackgroundAudioState,
    ControlCommandStatus,
    ControlCommandTarget,
    PlaybackCommand,
    PlaybackState,
)
from scp_cv.player.controller import PlayerController
from scp_cv.services.command_queue import claim_next, enqueue
from scp_cv.services.playback import RESET_ALL_WINDOWS_ARG, get_or_create_session
from tests.player_controller_test_support import _SingleLoopController


class _ShowIdWindowStub:
    """支持窗口编号覆盖层的最小窗口替身。"""

    def show_id_overlay(self) -> None:
        """测试中无需渲染窗口编号。"""
        return


class _ClosableAdapter:
    """记录缺少窗口句柄时的新适配器释放。"""

    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        """记录适配器已释放。"""
        self.closed = True


class _CloseTimeoutAdapter:
    """模拟 PowerPoint Broker 关闭超时。"""

    def close(self) -> None:
        """抛出调用方必须能够观察到的关闭超时。"""
        raise TimeoutError("PowerPoint Broker close timeout=10.0s")


def test_poll_loop_prunes_command_history_at_most_once_per_hour(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """常驻播放器应低频清理终态命令，且不能每轮查询数据库。"""
    controller = _SingleLoopController()
    controller._next_command_prune_at = 0.0
    prune_calls: list[bool] = []
    monkeypatch.setattr(
        "scp_cv.services.command_queue.prune",
        lambda: prune_calls.append(True) or 0,
    )
    monkeypatch.setattr("scp_cv.player.controller.time.monotonic", lambda: 100.0)

    with patch("scp_cv.player.controller.time.sleep", return_value=None):
        controller._poll_running = True
        controller._poll_loop(interval_seconds=0)
        controller._poll_running = True
        controller._poll_loop(interval_seconds=0)

    assert prune_calls == [True]


@pytest.mark.django_db
def test_polled_command_stays_executing_until_qt_handler_finishes() -> None:
    """领取指令只表示开始执行，发出 Qt 信号后不得提前确认或清空镜像。"""
    get_or_create_session(1)
    queued = enqueue(ControlCommandTarget.WINDOW_1, PlaybackCommand.SHOW_ID)
    controller = PlayerController()
    captured: list[tuple[object, ...]] = []
    controller.sig_dispatch_queued_command.disconnect()
    controller.sig_dispatch_queued_command.connect(
        lambda *payload: captured.append(payload)
    )

    controller._check_and_dispatch_command(1)

    queued.refresh_from_db()
    session = get_or_create_session(1)
    assert captured
    assert queued.status == ControlCommandStatus.EXECUTING
    assert session.pending_command == PlaybackCommand.SHOW_ID


@pytest.mark.django_db
def test_stopping_controller_releases_its_unfinished_command() -> None:
    """播放器停止时应立即失败未派送完成的指令，不能留下 executing 单槽。"""
    get_or_create_session(1)
    queued = enqueue(ControlCommandTarget.WINDOW_1, PlaybackCommand.SHOW_ID)
    controller = PlayerController(enable_background_audio=False)
    controller.sig_dispatch_queued_command.disconnect()

    controller._check_and_dispatch_command(1)
    controller.stop_polling()

    queued.refresh_from_db()
    assert queued.status == ControlCommandStatus.FAILED
    assert "播放器已停止" in queued.error_message


@pytest.mark.django_db
def test_controller_renews_its_lease_before_periodic_recovery() -> None:
    """周期维护必须先续约自身，再判断同目标上是否存在遗留消费者。"""
    queued = enqueue(ControlCommandTarget.WINDOW_1, PlaybackCommand.OPEN)
    controller = PlayerController(enable_background_audio=False)
    controller._windows[1] = object()
    claim_next(
        ControlCommandTarget.WINDOW_1,
        controller._command_consumer_identity,
    )
    expired_at = timezone.now() - timedelta(minutes=1)
    type(queued).objects.filter(pk=queued.pk).update(
        consumer_heartbeat_at=expired_at,
    )
    controller._next_command_consumer_maintenance_at = 0.0

    controller._maintain_command_consumer_if_due()

    queued.refresh_from_db()
    assert queued.status == ControlCommandStatus.EXECUTING
    assert queued.consumer_heartbeat_at is not None
    assert queued.consumer_heartbeat_at > expired_at


@pytest.mark.django_db
def test_synchronous_qt_handler_confirms_queued_command(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """同步 Qt 处理槽返回后应确认指令，并把 legacy 镜像推进到下一项。"""
    get_or_create_session(1)
    queued = enqueue(ControlCommandTarget.WINDOW_1, PlaybackCommand.SHOW_ID)
    controller = PlayerController()
    monkeypatch.setattr(
        controller,
        "get_window",
        lambda _window_id: _ShowIdWindowStub(),
    )

    controller._check_and_dispatch_command(1)

    queued.refresh_from_db()
    session = get_or_create_session(1)
    assert queued.status == ControlCommandStatus.SUCCEEDED
    assert session.pending_command == PlaybackCommand.NONE


@pytest.mark.django_db
def test_queued_show_id_fails_when_window_is_missing() -> None:
    """SHOW_ID 找不到目标窗口时必须进入 failed。"""
    get_or_create_session(1)
    queued = enqueue(ControlCommandTarget.WINDOW_1, PlaybackCommand.SHOW_ID)
    controller = PlayerController()

    controller._check_and_dispatch_command(1)

    queued.refresh_from_db()
    assert queued.status == ControlCommandStatus.FAILED
    assert "没有可用播放器窗口" in queued.error_message


@pytest.mark.django_db
def test_queued_adapter_command_fails_when_window_has_no_adapter() -> None:
    """依赖播放适配器的指令不得在适配器缺失时静默成功。"""
    get_or_create_session(1)
    queued = enqueue(ControlCommandTarget.WINDOW_1, PlaybackCommand.NEXT)
    controller = PlayerController()

    controller._check_and_dispatch_command(1)

    queued.refresh_from_db()
    session = get_or_create_session(1)
    assert queued.status == ControlCommandStatus.FAILED
    assert "无可用播放适配器" in queued.error_message
    assert session.playback_state == PlaybackState.ERROR


@pytest.mark.django_db
def test_queued_close_fails_when_adapter_close_times_out() -> None:
    """CLOSE 的真实释放失败必须写入命令和会话，不能静默确认成功。"""
    session = get_or_create_session(1)
    queued = enqueue(ControlCommandTarget.WINDOW_1, PlaybackCommand.CLOSE)
    controller = PlayerController(enable_background_audio=False)
    controller._adapters[1] = _CloseTimeoutAdapter()  # type: ignore[assignment]
    controller._adapter_source_types[1] = "ppt"

    controller._check_and_dispatch_command(1)

    queued.refresh_from_db()
    session.refresh_from_db()
    assert queued.status == ControlCommandStatus.FAILED
    assert "PowerPoint Broker close timeout=10.0s" in queued.error_message
    assert session.playback_state == PlaybackState.ERROR
    assert "PowerPoint Broker close timeout=10.0s" in session.error_message


@pytest.mark.django_db
def test_queued_reset_continues_cleanup_and_reports_close_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """全局重置应尝试关闭所有窗口，同时把任一释放失败写成 failed。"""
    get_or_create_session(1)
    remaining_adapter = _ClosableAdapter()
    queued = enqueue(
        ControlCommandTarget.WINDOW_1,
        PlaybackCommand.CLOSE,
        {RESET_ALL_WINDOWS_ARG: True},
    )
    controller = PlayerController(enable_background_audio=False)
    controller._adapters[1] = _CloseTimeoutAdapter()  # type: ignore[assignment]
    controller._adapters[2] = remaining_adapter  # type: ignore[assignment]
    monkeypatch.setattr(controller, "rebuild_registered_windows", lambda: None)
    monkeypatch.setattr(controller, "preheat_sources", lambda: None)

    controller._check_and_dispatch_command(1)

    queued.refresh_from_db()
    assert queued.status == ControlCommandStatus.FAILED
    assert "PowerPoint Broker close timeout=10.0s" in queued.error_message
    assert remaining_adapter.closed is True


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("command", "arguments"),
    [
        (PlaybackCommand.PLAY, {}),
        (PlaybackCommand.PAUSE, {}),
        (PlaybackCommand.STOP, {}),
        (PlaybackCommand.PREV, {}),
        (PlaybackCommand.GOTO, {"target_index": 2}),
        (PlaybackCommand.SEEK, {"position_ms": 1000}),
        (
            PlaybackCommand.PPT_MEDIA,
            {"media_action": PlaybackCommand.PLAY, "media_id": "m1"},
        ),
        (PlaybackCommand.SET_LOOP, {"enabled": True}),
        (PlaybackCommand.SET_VOLUME, {"volume": 80}),
        (PlaybackCommand.SET_MUTE, {"muted": True}),
    ],
)
def test_other_queued_adapter_commands_fail_without_adapter(
    command: str,
    arguments: dict[str, object],
) -> None:
    """所有依赖窗口适配器的控制动作都应持久化相同的缺失错误。"""
    get_or_create_session(1)
    queued = enqueue(ControlCommandTarget.WINDOW_1, command, arguments)
    controller = PlayerController()

    controller._check_and_dispatch_command(1)

    queued.refresh_from_db()
    assert queued.status == ControlCommandStatus.FAILED
    assert "无可用播放适配器" in queued.error_message


@pytest.mark.django_db
def test_queued_open_fails_when_required_arguments_are_missing() -> None:
    """OPEN 缺少源类型或 URI 时必须进入 failed，不能仅记录 warning。"""
    get_or_create_session(1)
    queued = enqueue(
        ControlCommandTarget.WINDOW_1,
        PlaybackCommand.OPEN,
        {"source_type": "ppt"},
    )
    controller = PlayerController()

    controller._check_and_dispatch_command(1)

    queued.refresh_from_db()
    assert queued.status == ControlCommandStatus.FAILED
    assert "缺少 source_type 或 uri" in queued.error_message


@pytest.mark.django_db
def test_queued_open_fails_when_window_handle_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """OPEN 找不到父窗口句柄时应释放新适配器并持久化失败。"""
    get_or_create_session(1)
    adapter = _ClosableAdapter()
    monkeypatch.setattr(
        "scp_cv.player.controller_handlers.create_adapter",
        lambda *_args, **_kwargs: adapter,
    )
    controller = PlayerController()
    monkeypatch.setattr(controller, "get_window_handle", lambda _window_id: 0)
    queued = enqueue(
        ControlCommandTarget.WINDOW_1,
        PlaybackCommand.OPEN,
        {"source_type": "video", "uri": "C:/demo/video.mp4"},
    )

    controller._check_and_dispatch_command(1)

    queued.refresh_from_db()
    assert queued.status == ControlCommandStatus.FAILED
    assert "没有可用窗口句柄" in queued.error_message
    assert adapter.closed is True


@pytest.mark.django_db
def test_background_audio_handler_confirms_queued_command(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """背景音频也必须通过同一领取/确认协议，不能继续使用单槽清空。"""
    state = BackgroundAudioState.get_instance()
    queued = enqueue(
        ControlCommandTarget.BACKGROUND_AUDIO,
        BackgroundAudioCommand.PLAY,
    )
    controller = PlayerController()
    played: list[bool] = []
    monkeypatch.setattr(
        controller,
        "_handle_background_audio_play",
        lambda _args: played.append(True),
    )

    controller._check_and_dispatch_background_audio_command()

    queued.refresh_from_db()
    state.refresh_from_db()
    assert played == [True]
    assert queued.status == ControlCommandStatus.SUCCEEDED
    assert state.pending_command == BackgroundAudioCommand.NONE


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("command", "arguments"),
    [
        (BackgroundAudioCommand.PLAY, {}),
        (BackgroundAudioCommand.PAUSE, {}),
        (BackgroundAudioCommand.STOP, {}),
        (BackgroundAudioCommand.SEEK, {"position_ms": 1000}),
        (BackgroundAudioCommand.SET_VOLUME, {"volume": 80}),
        (BackgroundAudioCommand.SET_MUTE, {"muted": True}),
    ],
)
def test_background_audio_adapter_commands_fail_without_adapter(
    command: str,
    arguments: dict[str, object],
) -> None:
    """依赖背景音频适配器的命令不得在适配器缺失时静默成功。"""
    state = BackgroundAudioState.get_instance()
    queued = enqueue(
        ControlCommandTarget.BACKGROUND_AUDIO,
        command,
        arguments,
    )
    controller = PlayerController()

    controller._check_and_dispatch_background_audio_command()

    queued.refresh_from_db()
    state.refresh_from_db()
    assert queued.status == ControlCommandStatus.FAILED
    assert "无可用背景音频适配器" in queued.error_message
    assert state.playback_state == PlaybackState.ERROR
