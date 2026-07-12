#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PowerPoint Broker 会话引擎关闭与生命周期行为测试。
@Project : SCP-cv
@File : test_ppt_broker_engine_lifecycle.py
@Author : Qintsg
@Date : 2026-07-11
'''
from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable

import pytest

from scp_cv.player.ppt_broker import (
    PptBrokerEngine,
    PptCommand,
    PptCommandRequest,
    PptOpenRequest,
    PptPreheatRequest,
    PptSessionKey,
    PptShowExportRequest,
    PptState,
)
from tests import test_ppt_broker_engine as engine_fakes


class _ShutdownRaceBackend(engine_fakes._TransactionalBackend):
    """在后端关闭期间观察迟到前台任务是否仍会执行。"""

    def __init__(self) -> None:
        self.order: list[str] = []
        self.shutdown_started = threading.Event()
        self.release_shutdown = threading.Event()

    def open(self, request: PptOpenRequest) -> object:
        self.order.append("open")
        return super().open(request)

    def shutdown(self) -> None:
        self.order.append("shutdown")
        self.shutdown_started.set()
        if not self.release_shutdown.wait(5.0):
            raise TimeoutError("test shutdown blocker was not released")


def test_shutdown_releases_queued_low_priority_caller_with_error() -> None:
    """Broker 关闭时，被丢弃的低优先级调用必须立即结束并收到错误。"""
    backend = engine_fakes._PriorityBackend()
    broker = PptBrokerEngine(backend)
    current = PptSessionKey(1, "shutdown-player")
    export_errors: list[BaseException] = []
    blocking_errors: list[BaseException] = []
    shutdown_errors: list[BaseException] = []
    broker.open(PptOpenRequest(current, "C:/slides/current.pptx", 1001))

    def run_blocking_command() -> None:
        try:
            broker.command(PptCommandRequest(current, PptCommand.NEXT))
        except BaseException as command_error:
            blocking_errors.append(command_error)

    def run_export() -> None:
        try:
            broker.export_show(
                PptShowExportRequest(
                    "C:/slides/current.pptx",
                    "C:/cache/current.ppsx",
                    "ppsx",
                )
            )
        except BaseException as export_error:
            export_errors.append(export_error)

    def run_shutdown() -> None:
        try:
            broker.shutdown()
        except BaseException as shutdown_error:
            shutdown_errors.append(shutdown_error)

    blocker = threading.Thread(target=run_blocking_command, daemon=True)
    exporter = threading.Thread(target=run_export, daemon=True)
    shutdown = threading.Thread(target=run_shutdown, daemon=True)
    blocker.start()
    assert backend.blocking_started.wait(2.0)
    exporter.start()
    time.sleep(0.03)
    shutdown.start()
    time.sleep(0.03)
    backend.release_blocking.set()

    for operation_thread in (blocker, shutdown, exporter):
        operation_thread.join(2.0)

    assert not blocker.is_alive()
    assert not shutdown.is_alive()
    assert not exporter.is_alive()
    assert blocking_errors == []
    assert shutdown_errors == []
    assert len(export_errors) == 1
    assert isinstance(export_errors[0], RuntimeError)
    assert "STA 已关闭" in str(export_errors[0])


def test_shutdown_rejects_open_started_while_backend_is_shutting_down() -> None:
    """shutdown 开始后不得接受会在 backend.shutdown 后执行的 OPEN。"""
    backend = _ShutdownRaceBackend()
    broker = PptBrokerEngine(backend)
    late_session = PptSessionKey(1, "late-player")
    shutdown_errors: list[BaseException] = []
    open_errors: list[BaseException] = []
    open_states: list[PptState] = []
    open_finished = threading.Event()

    def run_shutdown() -> None:
        try:
            broker.shutdown()
        except BaseException as shutdown_error:
            shutdown_errors.append(shutdown_error)

    def run_late_open() -> None:
        try:
            open_states.append(
                broker.open(
                    PptOpenRequest(late_session, "C:/slides/late.pptx", 1001)
                )
            )
        except BaseException as open_error:
            open_errors.append(open_error)
        finally:
            open_finished.set()

    shutdown = threading.Thread(target=run_shutdown, daemon=True)
    late_open = threading.Thread(target=run_late_open, daemon=True)
    shutdown.start()
    assert backend.shutdown_started.wait(2.0)
    late_open.start()
    rejected_before_backend_shutdown_finished = open_finished.wait(0.5)
    backend.release_shutdown.set()

    for operation_thread in (shutdown, late_open):
        operation_thread.join(2.0)

    assert not shutdown.is_alive()
    assert not late_open.is_alive()
    assert rejected_before_backend_shutdown_finished
    assert shutdown_errors == []
    assert open_states == []
    assert len(open_errors) == 1
    assert isinstance(open_errors[0], RuntimeError)
    assert "STA 已关闭" in str(open_errors[0])
    assert backend.order == ["shutdown"]


def test_shutdown_finishes_already_queued_open_before_backend_shutdown() -> None:
    """shutdown 前已排队的高优先级 OPEN 应在后端关闭前完成。"""
    backend = engine_fakes._PriorityBackend()
    broker = PptBrokerEngine(backend)
    current = PptSessionKey(1, "current-player")
    queued = PptSessionKey(2, "queued-player")
    operation_errors: list[BaseException] = []
    broker.open(PptOpenRequest(current, "C:/slides/current.pptx", 1001))

    def run(callback: Callable[[], object]) -> None:
        try:
            callback()
        except BaseException as operation_error:
            operation_errors.append(operation_error)

    blocker = threading.Thread(
        target=run,
        args=(
            lambda: broker.command(PptCommandRequest(current, PptCommand.NEXT)),
        ),
        daemon=True,
    )
    opener = threading.Thread(
        target=run,
        args=(
            lambda: broker.open(
                PptOpenRequest(queued, "C:/slides/foreground.pptx", 1002)
            ),
        ),
        daemon=True,
    )
    shutdown = threading.Thread(target=run, args=(broker.shutdown,), daemon=True)
    blocker.start()
    assert backend.blocking_started.wait(2.0)
    opener.start()
    time.sleep(0.03)
    shutdown.start()

    deadline = time.monotonic() + 2.0
    while broker.health().ready and time.monotonic() < deadline:
        time.sleep(0.01)
    backend.release_blocking.set()

    for operation_thread in (blocker, opener, shutdown):
        operation_thread.join(2.0)

    assert not blocker.is_alive()
    assert not opener.is_alive()
    assert not shutdown.is_alive()
    assert operation_errors == []
    assert backend.order == ["blocking-command", "open", "shutdown"]


def test_lifecycle_logs_have_stable_structured_context(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """open/command/close/preheat 日志应提供稳定且可检索的生命周期字段。"""
    broker = PptBrokerEngine(
        engine_fakes._TransactionalBackend(),
        generation="test-generation",
    )
    session = PptSessionKey(1, "logged-player")
    with caplog.at_level(
        logging.INFO,
        logger="scp_cv.player.ppt_broker.engine",
    ):
        broker.open(
            PptOpenRequest(
                session,
                "C:/slides/logged.pptx",
                1001,
                source_id=17,
                request_id="open-request",
            )
        )
        broker.command(
            PptCommandRequest(
                session,
                PptCommand.NEXT,
                request_id="command-request",
            )
        )
        broker.close(session)
        broker.preheat(
            PptPreheatRequest(
                source_id=17,
                uri="C:/slides/logged.pptx",
                request_id="preheat-request",
            )
        )
        broker.shutdown()

    lifecycle_messages = [
        record.getMessage()
        for record in caplog.records
        if record.getMessage().startswith("ppt_broker_lifecycle ")
    ]
    assert len(lifecycle_messages) == 4
    for event_name in ("open", "command", "close", "preheat"):
        message = next(
            entry
            for entry in lifecycle_messages
            if f"event={event_name} " in entry
        )
        for field_name in (
            "request_id=",
            "window_id=",
            "source_id=",
            "broker_generation=test-generation",
            "broker_pid=",
            "powerpoint_pid=",
            "hwnd=",
            "parent_hwnd=",
            "elapsed_ms=",
            "result=success",
        ):
            assert field_name in message
    assert "request_id=open-request" in lifecycle_messages[0]
    assert "request_id=command-request" in lifecycle_messages[1]
    assert "request_id=-" in lifecycle_messages[2]
    assert "request_id=preheat-request" in lifecycle_messages[3]
    assert all("source_id=17" in message for message in lifecycle_messages)
