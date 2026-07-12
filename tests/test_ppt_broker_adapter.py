#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PPT Broker SourceAdapter 行为测试。
@Project : SCP-cv
@File : test_ppt_broker_adapter.py
@Author : Qintsg
@Date : 2026-07-11
'''
from __future__ import annotations

import threading
from concurrent.futures import CancelledError

import pytest

from scp_cv.player.adapters import create_adapter
from scp_cv.player.adapters.ppt_broker import PptBrokerSourceAdapter
from scp_cv.player.ppt_broker import (
    InMemoryPptBroker,
    PptCommand,
    PptCommandRequest,
    PptOpenRequest,
    PptSessionNotFoundError,
    PptState,
)


class _FailingOpenBroker(InMemoryPptBroker):
    """打开时返回确定性错误的 Broker 测试 Adapter。"""

    def open(self, request: PptOpenRequest) -> PptState:
        """拒绝打开，验证异步错误回调。"""
        del request
        raise RuntimeError("broker open failed")


class _BlockingOpenBroker(InMemoryPptBroker):
    """允许测试精确控制异步打开完成时点的 Broker。"""

    def __init__(self) -> None:
        super().__init__()
        self.open_started = threading.Event()
        self.allow_open = threading.Event()
        self.open_request: PptOpenRequest | None = None

    def open(self, request: PptOpenRequest) -> PptState:
        """等测试放行后才真正创建 Broker 会话。"""
        self.open_request = request
        self.open_started.set()
        if not self.allow_open.wait(2.0):
            raise TimeoutError("test did not release blocked PPT open")
        return super().open(request)


class _RecordingCommandBroker(InMemoryPptBroker):
    """记录 Adapter 发送到 Broker 的会话命令。"""

    def __init__(self) -> None:
        super().__init__()
        self.commands: list[PptCommand] = []

    def command(self, request: PptCommandRequest) -> PptState:
        self.commands.append(request.command)
        return super().command(request)


def test_adapter_requires_broker_client() -> None:
    """缺少 Broker 时应在创建阶段给出可操作错误，不留下异步假失败。"""
    with pytest.raises(ValueError, match="run_ppt_broker"):
        PptBrokerSourceAdapter(
            broker=None,  # type: ignore[arg-type]
            window_id=1,
            owner_prefix="player-a",
        )


def test_factory_routes_ppt_to_broker_adapter() -> None:
    """PPT 工厂入口必须创建 Broker Adapter，运行时不得回到本地 COM。"""
    broker = InMemoryPptBroker()
    try:
        adapter = create_adapter(
            "ppt",
            broker=broker,
            window_id=2,
            owner_prefix="player-a",
        )

        assert isinstance(adapter, PptBrokerSourceAdapter)
    finally:
        broker.shutdown()


def test_adapter_maps_commands_and_state_through_broker() -> None:
    """SourceAdapter 的控制和状态接口应完整映射到 Broker 会话。"""
    broker = InMemoryPptBroker()
    adapter = PptBrokerSourceAdapter(
        broker=broker,
        window_id=1,
        owner_prefix="player-a",
    )
    try:
        adapter.open("C:/demo/slides.pptx", window_handle=1001, autoplay=False)
        assert adapter.get_state().playback_state == "stopped"

        adapter.play()
        adapter.goto_item(7)
        adapter.next_item()
        adapter.pause()

        state = adapter.get_state()
        assert state.playback_state == "paused"
        assert state.current_slide == 8
        assert state.total_slides == 100
    finally:
        adapter.close()
        broker.shutdown()


def test_adapter_maps_viewport_resize_to_broker_session_command() -> None:
    """Qt 渲染容器 resize 应通过 Broker 串行同步 PowerPoint HWND。"""
    broker = _RecordingCommandBroker()
    adapter = PptBrokerSourceAdapter(
        broker=broker,
        window_id=1,
        owner_prefix="player-a",
    )
    try:
        adapter.open("C:/demo/slides.pptx", window_handle=1001)

        adapter.resize_output(640, 360)

        assert broker.commands == [PptCommand.RESIZE]
    finally:
        adapter.close()
        broker.shutdown()


def test_async_open_reports_success_after_state_is_available() -> None:
    """异步 OPEN 成功回调发生时，Adapter 状态必须已经可读取。"""
    broker = InMemoryPptBroker()
    adapter = PptBrokerSourceAdapter(
        broker=broker,
        window_id=3,
        owner_prefix="player-a",
    )
    finished = threading.Event()
    errors: list[BaseException | None] = []

    def on_finished(error: BaseException | None) -> None:
        errors.append(error)
        finished.set()

    try:
        adapter.open_async(
            "C:/demo/slides.pptx",
            window_handle=3001,
            start_slide=5,
            on_finished=on_finished,
        )

        assert finished.wait(2.0)
        assert errors == [None]
        assert adapter.is_open is True
        assert adapter.get_state().current_slide == 5
    finally:
        adapter.close()
        broker.shutdown()


def test_async_open_reports_broker_failure_without_marking_open() -> None:
    """异步 OPEN 失败必须原样回调错误，且不能留下假打开状态。"""
    broker = _FailingOpenBroker()
    adapter = PptBrokerSourceAdapter(
        broker=broker,
        window_id=4,
        owner_prefix="player-a",
    )
    finished = threading.Event()
    errors: list[BaseException | None] = []

    def on_finished(error: BaseException | None) -> None:
        errors.append(error)
        finished.set()

    try:
        adapter.open_async(
            "C:/demo/broken.pptx",
            window_handle=4001,
            on_finished=on_finished,
        )

        assert finished.wait(2.0)
        assert len(errors) == 1
        assert isinstance(errors[0], RuntimeError)
        assert str(errors[0]) == "broker open failed"
        assert adapter.is_open is False
    finally:
        adapter.close()
        broker.shutdown()


def test_close_cancels_inflight_async_open_without_orphan_session() -> None:
    """close 返回后，迟到的异步 OPEN 不得重新创建并标记活动会话。"""
    broker = _BlockingOpenBroker()
    adapter = PptBrokerSourceAdapter(
        broker=broker,
        window_id=1,
        owner_prefix="player-a",
    )
    open_finished = threading.Event()
    close_started = threading.Event()
    close_finished = threading.Event()
    errors: list[BaseException | None] = []

    def on_open_finished(error: BaseException | None) -> None:
        errors.append(error)
        open_finished.set()

    def close_adapter() -> None:
        close_started.set()
        adapter.close()
        close_finished.set()

    close_thread = threading.Thread(target=close_adapter)
    try:
        adapter.open_async(
            "C:/demo/slides.pptx",
            window_handle=1001,
            on_finished=on_open_finished,
        )
        assert broker.open_started.wait(1.0)

        close_thread.start()
        assert close_started.wait(1.0)
        # 旧实现会让 close 先对尚不存在的会话 no-op；给它充分时间触发该顺序。
        close_finished.wait(0.5)
        broker.allow_open.set()

        assert open_finished.wait(2.0)
        assert close_finished.wait(2.0)
        close_thread.join(timeout=1.0)
        assert not close_thread.is_alive()
        assert len(errors) == 1
        assert isinstance(errors[0], CancelledError)
        assert adapter.is_open is False
        assert adapter.get_state().playback_state == "idle"
        assert broker.open_request is not None
        with pytest.raises(PptSessionNotFoundError):
            broker.get_state(broker.open_request.session)
    finally:
        broker.allow_open.set()
        close_thread.join(timeout=2.0)
        broker.shutdown()


def test_close_is_idempotent() -> None:
    """重复关闭同一 Adapter 必须安全，并稳定返回 idle 快照。"""
    broker = InMemoryPptBroker()
    adapter = PptBrokerSourceAdapter(
        broker=broker,
        window_id=1,
        owner_prefix="player-a",
    )
    try:
        adapter.open("C:/demo/slides.pptx", window_handle=1001)

        adapter.close()
        adapter.close()

        assert adapter.is_open is False
        assert adapter.get_state().playback_state == "idle"
    finally:
        broker.shutdown()


def test_old_adapter_close_cannot_close_replacement_session() -> None:
    """同窗口新 PPT 打开后，旧 Adapter 的延迟关闭不得杀掉新会话。"""
    broker = InMemoryPptBroker()
    first = PptBrokerSourceAdapter(
        broker=broker,
        window_id=1,
        owner_prefix="player-a",
    )
    second = PptBrokerSourceAdapter(
        broker=broker,
        window_id=1,
        owner_prefix="player-a",
    )
    try:
        first.open("C:/demo/first.pptx", window_handle=1001)
        second.open("C:/demo/second.pptx", window_handle=1001)

        first.close()

        second.next_item()
        state = second.get_state()
        assert state.playback_state == "playing"
        assert state.current_slide == 2
    finally:
        second.close()
        broker.shutdown()
