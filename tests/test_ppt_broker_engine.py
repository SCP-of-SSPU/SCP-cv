#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PowerPoint Broker 会话引擎行为测试。
@Project : SCP-cv
@File : test_ppt_broker_engine.py
@Author : Qintsg
@Date : 2026-07-11
'''
from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass

import pytest

from scp_cv.player.ppt_broker import (
    PptBrokerEngine,
    PptCommand,
    PptCommandRequest,
    PptExportResult,
    PptOpenRequest,
    PptPreheatRequest,
    PptSessionKey,
    PptSessionNotFoundError,
    PptShowExportRequest,
    PptSlideExportRequest,
    PptState,
)


@dataclass(slots=True)
class _Handle:
    """测试后端会话句柄。"""

    parent_hwnd: int
    current_slide: int
    visible: bool = True


class _TransactionalBackend:
    """可在新会话打开阶段失败的测试后端。"""

    def open(self, request: PptOpenRequest) -> object:
        if request.uri.endswith("bad.pptx"):
            raise RuntimeError("open failed")
        return _Handle(request.parent_hwnd, request.start_slide)

    def command(self, handle: object, request: PptCommandRequest) -> None:
        del handle, request

    def get_state(self, handle: object) -> PptState:
        session = self._handle(handle)
        return PptState(
            playback_state="playing",
            current_slide=session.current_slide,
            total_slides=10,
            parent_hwnd=session.parent_hwnd,
        )

    def hide(self, handle: object) -> None:
        self._handle(handle).visible = False

    def show(self, handle: object) -> None:
        self._handle(handle).visible = True

    def close(self, handle: object) -> None:
        self._handle(handle).visible = False

    def preheat(self, request: PptPreheatRequest) -> None:
        del request

    def export_show(self, request: PptShowExportRequest) -> PptExportResult:
        return PptExportResult((request.target_uri,))

    def export_slides(self, request: PptSlideExportRequest) -> PptExportResult:
        return PptExportResult(())

    def shutdown(self) -> None:
        return

    @staticmethod
    def _handle(value: object) -> _Handle:
        if not isinstance(value, _Handle):
            raise TypeError("invalid handle")
        return value


class _SerialBackend(_TransactionalBackend):
    """记录并发度和执行线程的测试后端。"""

    def __init__(self) -> None:
        self.thread_ids: list[int] = []
        self.active_calls = 0
        self.max_active_calls = 0
        self.lock = threading.Lock()

    def command(self, handle: object, request: PptCommandRequest) -> None:
        del handle, request
        with self.lock:
            self.thread_ids.append(threading.get_ident())
            self.active_calls += 1
            self.max_active_calls = max(self.max_active_calls, self.active_calls)
        time.sleep(0.03)
        with self.lock:
            self.active_calls -= 1


class _PriorityBackend(_TransactionalBackend):
    """用阻塞前台任务观察高低优先级出队顺序。"""

    def __init__(self) -> None:
        self.order: list[str] = []
        self.blocking_started = threading.Event()
        self.release_blocking = threading.Event()

    def open(self, request: PptOpenRequest) -> object:
        if request.uri.endswith("foreground.pptx"):
            self.order.append("open")
        return super().open(request)

    def command(self, handle: object, request: PptCommandRequest) -> None:
        del handle, request
        self.order.append("blocking-command")
        self.blocking_started.set()
        if not self.release_blocking.wait(5.0):
            raise TimeoutError("test blocker was not released")

    def export_show(self, request: PptShowExportRequest) -> PptExportResult:
        self.order.append("export")
        return super().export_show(request)

    def shutdown(self) -> None:
        self.order.append("shutdown")


class _StateRefreshPriorityBackend(_TransactionalBackend):
    """记录状态刷新与前台控制操作的实际执行顺序。"""

    def __init__(self) -> None:
        self.order: list[str] = []
        self.recording = False
        self.blocking_started = threading.Event()
        self.release_blocking = threading.Event()

    def open(self, request: PptOpenRequest) -> object:
        if self.recording:
            self.order.append("open")
        return super().open(request)

    def command(self, handle: object, request: PptCommandRequest) -> None:
        del handle
        if request.request_id == "blocking-command":
            self.order.append("blocking-command")
            self.blocking_started.set()
            if not self.release_blocking.wait(5.0):
                raise TimeoutError("test blocker was not released")
            return
        self.order.append("command")

    def get_state(self, handle: object) -> PptState:
        session = self._handle(handle)
        if self.recording and session.parent_hwnd == 1002:
            self.order.append("get-state")
        return super().get_state(session)

    def close(self, handle: object) -> None:
        if self.recording:
            self.order.append("close")
        super().close(handle)


class _StateValidationBackend(_TransactionalBackend):
    """记录替换会话，并可让新会话在状态验证阶段失败。"""

    def __init__(self) -> None:
        self.handles: dict[str, _Handle] = {}
        self.closed_handles: list[_Handle] = []
        self.handle_uris: dict[int, str] = {}
        self.events: list[tuple[str, str]] = []

    def open(self, request: PptOpenRequest) -> object:
        handle = self._handle(super().open(request))
        self.handles[request.uri] = handle
        self.handle_uris[id(handle)] = request.uri
        self.events.append(("open", request.uri))
        return handle

    def get_state(self, handle: object) -> PptState:
        session = self._handle(handle)
        self.events.append(("get_state", self.handle_uris[id(session)]))
        if session is self.handles.get("C:/slides/invalid-state.pptx"):
            raise RuntimeError("state validation failed")
        return super().get_state(session)

    def close(self, handle: object) -> None:
        session = self._handle(handle)
        self.closed_handles.append(session)
        self.events.append(("close", self.handle_uris[id(session)]))
        super().close(session)


def test_failed_replacement_restores_previous_slideshow() -> None:
    """新 PPT 打开失败时，旧会话应恢复并继续作为当前状态。"""
    backend = _TransactionalBackend()
    broker = PptBrokerEngine(backend)
    old_session = PptSessionKey(1, "old-player")
    new_session = PptSessionKey(1, "new-player")
    try:
        broker.open(
            PptOpenRequest(old_session, "C:/slides/good.pptx", 1001, start_slide=3)
        )

        with pytest.raises(RuntimeError, match="open failed"):
            broker.open(PptOpenRequest(new_session, "C:/slides/bad.pptx", 1001))

        assert broker.get_state(old_session).current_slide == 3
    finally:
        broker.shutdown()


def test_failed_state_validation_keeps_previous_slideshow_and_discards_new() -> None:
    """新会话状态验证失败时，旧画面可用且失败会话不得残留。"""
    backend = _StateValidationBackend()
    broker = PptBrokerEngine(backend)
    old_session = PptSessionKey(1, "old-player")
    new_session = PptSessionKey(1, "new-player")
    old_uri = "C:/slides/good.pptx"
    new_uri = "C:/slides/invalid-state.pptx"
    try:
        broker.open(PptOpenRequest(old_session, old_uri, 1001, start_slide=3))

        with pytest.raises(RuntimeError, match="state validation failed"):
            broker.open(PptOpenRequest(new_session, new_uri, 1001))

        assert backend.handles[old_uri].visible
        assert any(
            handle is backend.handles[new_uri]
            for handle in backend.closed_handles
        )
        assert broker.get_state(old_session).current_slide == 3
        with pytest.raises(PptSessionNotFoundError):
            broker.get_state(new_session)
    finally:
        broker.shutdown()


def test_successful_replacement_validates_new_slideshow_before_closing_old() -> None:
    """成功切源只能在新会话状态验证完成后释放旧会话。"""
    backend = _StateValidationBackend()
    broker = PptBrokerEngine(backend)
    old_session = PptSessionKey(1, "old-player")
    new_session = PptSessionKey(1, "new-player")
    old_uri = "C:/slides/good.pptx"
    new_uri = "C:/slides/replacement.pptx"
    try:
        broker.open(PptOpenRequest(old_session, old_uri, 1001))
        backend.events.clear()

        state = broker.open(PptOpenRequest(new_session, new_uri, 1001))

        assert state.playback_state == "playing"
        assert backend.events == [
            ("open", new_uri),
            ("get_state", new_uri),
            ("close", old_uri),
        ]
    finally:
        broker.shutdown()


def test_concurrent_clients_execute_serially_on_one_sta_thread() -> None:
    """并发客户端不得让 PowerPoint 后端同时执行或跨 STA 线程漂移。"""
    backend = _SerialBackend()
    broker = PptBrokerEngine(backend)
    left = PptSessionKey(1, "left-player")
    right = PptSessionKey(2, "right-player")
    errors: list[BaseException] = []
    try:
        broker.open(PptOpenRequest(left, "C:/slides/left.pptx", 1001))
        broker.open(PptOpenRequest(right, "C:/slides/right.pptx", 1002))

        def advance(session: PptSessionKey) -> None:
            try:
                broker.command(PptCommandRequest(session, PptCommand.NEXT))
            except BaseException as command_error:
                errors.append(command_error)

        callers = [
            threading.Thread(target=advance, args=(left,)),
            threading.Thread(target=advance, args=(right,)),
        ]
        for caller in callers:
            caller.start()
        for caller in callers:
            caller.join(5.0)

        assert errors == []
        assert backend.max_active_calls == 1
        assert len(set(backend.thread_ids)) == 1
        assert backend.thread_ids[0] != threading.get_ident()
    finally:
        broker.shutdown()


def test_foreground_open_preempts_queued_low_priority_export() -> None:
    """前台 OPEN 应插到已排队但未执行的导出任务之前。"""
    backend = _PriorityBackend()
    broker = PptBrokerEngine(backend)
    current = PptSessionKey(1, "current-player")
    foreground = PptSessionKey(2, "foreground-player")
    errors: list[BaseException] = []
    try:
        broker.open(PptOpenRequest(current, "C:/slides/current.pptx", 1001))

        def run(callback: Callable[[], object]) -> None:
            try:
                callback()
            except BaseException as operation_error:
                errors.append(operation_error)

        blocker = threading.Thread(
            target=run,
            args=(
                lambda: broker.command(
                    PptCommandRequest(current, PptCommand.NEXT)
                ),
            ),
        )
        blocker.start()
        assert backend.blocking_started.wait(2.0)
        export = threading.Thread(
            target=run,
            args=(
                lambda: broker.export_show(
                    PptShowExportRequest(
                        "C:/slides/current.pptx",
                        "C:/cache/current.ppsx",
                        "ppsx",
                    )
                ),
            ),
        )
        export.start()
        time.sleep(0.03)
        opener = threading.Thread(
            target=run,
            args=(
                lambda: broker.open(
                    PptOpenRequest(
                        foreground,
                        "C:/slides/foreground.pptx",
                        1002,
                    )
                ),
            ),
        )
        opener.start()
        time.sleep(0.03)
        backend.release_blocking.set()

        for operation_thread in (blocker, export, opener):
            operation_thread.join(5.0)

        assert errors == []
        assert backend.order == ["blocking-command", "open", "export"]
    finally:
        broker.shutdown()


def test_state_refresh_yields_to_open_command_and_close() -> None:
    """状态刷新应低优先级排队，且既有控制调用合同保持不变。"""
    backend = _StateRefreshPriorityBackend()
    broker = PptBrokerEngine(backend)
    blocking = PptSessionKey(1, "blocking-player")
    refreshing = PptSessionKey(2, "refreshing-player")
    navigating = PptSessionKey(3, "navigating-player")
    closing = PptSessionKey(4, "closing-player")
    opening = PptSessionKey(5, "opening-player")
    results: dict[str, object] = {}
    errors: list[BaseException] = []

    def run(name: str, callback: Callable[[], object]) -> None:
        try:
            results[name] = callback()
        except BaseException as operation_error:
            errors.append(operation_error)

    try:
        for session in (blocking, refreshing, navigating, closing):
            broker.open(
                PptOpenRequest(
                    session,
                    f"C:/slides/{session.window_id}.pptx",
                    1000 + session.window_id,
                )
            )
        backend.recording = True

        operations = [
            threading.Thread(
                target=run,
                args=(
                    "blocker",
                    lambda: broker.command(
                        PptCommandRequest(
                            blocking,
                            PptCommand.NEXT,
                            request_id="blocking-command",
                        )
                    ),
                ),
            ),
            threading.Thread(
                target=run,
                args=("state", lambda: broker.get_state(refreshing)),
            ),
            threading.Thread(
                target=run,
                args=(
                    "open",
                    lambda: broker.open(
                        PptOpenRequest(
                            opening,
                            "C:/slides/opening.pptx",
                            1005,
                        )
                    ),
                ),
            ),
            threading.Thread(
                target=run,
                args=(
                    "command",
                    lambda: broker.command(
                        PptCommandRequest(navigating, PptCommand.NEXT)
                    ),
                ),
            ),
            threading.Thread(
                target=run,
                args=("close", lambda: broker.close(closing)),
            ),
        ]
        operations[0].start()
        assert backend.blocking_started.wait(2.0)
        for operation in operations[1:]:
            operation.start()
            time.sleep(0.03)
        backend.release_blocking.set()

        for operation in operations:
            operation.join(5.0)

        assert all(not operation.is_alive() for operation in operations)
        assert errors == []
        assert isinstance(results["state"], PptState)
        assert isinstance(results["open"], PptState)
        assert isinstance(results["command"], PptState)
        assert results["close"] is None
        assert backend.order == [
            "blocking-command",
            "open",
            "command",
            "close",
            "get-state",
        ]
    finally:
        backend.release_blocking.set()
        backend.recording = False
        broker.shutdown()
