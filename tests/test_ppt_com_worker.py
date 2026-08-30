#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PPT COM 工作线程单元测试，覆盖串行执行、同步等待、错误传递与关闭。
@Project : SCP-cv
@File : test_ppt_com_worker.py
@Author : Qintsg
@Date : 2026-06-10
'''
from __future__ import annotations

import threading
import time

import pytest

from scp_cv.player.adapters.ppt_com_worker import PptComWorker


def test_submit_runs_jobs_serially_on_single_worker_thread() -> None:
    """所有任务应在同一工作线程串行执行。"""
    worker = PptComWorker(name="test-ppt-com")
    thread_ids: list[int] = []
    order: list[int] = []
    done = threading.Event()

    def make_job(index: int):
        def job() -> None:
            thread_ids.append(threading.get_ident())
            order.append(index)
            if index == 3:
                done.set()
        return job

    try:
        for job_index in (1, 2, 3):
            worker.submit(f"job-{job_index}", make_job(job_index))
        assert done.wait(5.0)
        assert order == [1, 2, 3]
        assert len(set(thread_ids)) == 1
        assert thread_ids[0] != threading.get_ident()
    finally:
        worker.shutdown(timeout_seconds=5.0)


def test_submit_and_wait_returns_result_and_propagates_error() -> None:
    """同步等待应拿到返回值，任务异常应原样抛给调用方。"""
    worker = PptComWorker(name="test-ppt-com-wait")
    try:
        assert worker.submit_and_wait("ok-job", lambda: 42, timeout_seconds=5.0) == 42

        def failing_job() -> None:
            raise ValueError("com busy")

        with pytest.raises(ValueError, match="com busy"):
            worker.submit_and_wait("fail-job", failing_job, timeout_seconds=5.0)
    finally:
        worker.shutdown(timeout_seconds=5.0)


def test_submit_from_worker_thread_runs_inline_without_deadlock() -> None:
    """工作线程内再次提交任务应内联执行，避免自我死锁。"""
    worker = PptComWorker(name="test-ppt-com-inline")
    nested_result: list[object] = []

    def outer_job() -> object:
        nested_result.append(
            worker.submit_and_wait("nested", lambda: "inner", timeout_seconds=1.0)
        )
        return "outer"

    try:
        assert worker.submit_and_wait("outer", outer_job, timeout_seconds=5.0) == "outer"
        assert nested_result == ["inner"]
    finally:
        worker.shutdown(timeout_seconds=5.0)


def test_on_done_callback_receives_error_object() -> None:
    """后台任务失败时完成回调应拿到异常对象。"""
    worker = PptComWorker(name="test-ppt-com-callback")
    outcomes: list[tuple[object, object]] = []
    done = threading.Event()

    def failing_job() -> None:
        raise RuntimeError("open failed")

    def on_done(result: object, error: object) -> None:
        outcomes.append((result, error))
        done.set()

    try:
        worker.submit("failing", failing_job, on_done=on_done)
        assert done.wait(5.0)
        assert outcomes[0][0] is None
        assert isinstance(outcomes[0][1], RuntimeError)
    finally:
        worker.shutdown(timeout_seconds=5.0)


def test_shutdown_drains_pending_jobs_then_rejects_new_submissions() -> None:
    """关闭时应先执行完已排队任务，其后提交的任务通过回调报错。"""
    worker = PptComWorker(name="test-ppt-com-shutdown")
    executed: list[str] = []
    worker.submit("queued", lambda: executed.append("queued"))
    assert worker.shutdown(timeout_seconds=5.0) is True
    assert executed == ["queued"]

    rejected: list[object] = []
    worker.submit("late", lambda: executed.append("late"), on_done=lambda _r, e: rejected.append(e))
    time.sleep(0.05)
    assert executed == ["queued"]
    assert len(rejected) == 1
    assert isinstance(rejected[0], RuntimeError)


def test_high_priority_jobs_preempt_queued_low_priority_jobs() -> None:
    """排队中的低优先级预热任务应被后到的高优先级任务插队。"""
    worker = PptComWorker(name="test-ppt-com-priority")
    order: list[str] = []
    gate = threading.Event()
    done = threading.Event()

    def blocking_job() -> None:
        gate.wait(5.0)

    try:
        # 先占住工作线程，保证后续任务进入排队状态
        worker.submit("blocker", blocking_job)
        time.sleep(0.05)
        worker.submit("preheat-1", lambda: order.append("low-1"), low_priority=True)
        worker.submit("preheat-2", lambda: order.append("low-2"), low_priority=True)
        worker.submit("open", lambda: order.append("high-open"))
        worker.submit("finish", lambda: (order.append("high-finish"), done.set()))
        gate.set()
        assert done.wait(5.0)
        # 低优先级任务最终仍会执行，但高优先级先行
        deadline = time.monotonic() + 5.0
        while len(order) < 4 and time.monotonic() < deadline:
            time.sleep(0.01)
        assert order == ["high-open", "high-finish", "low-1", "low-2"]
    finally:
        worker.shutdown(timeout_seconds=5.0)


def test_discard_low_priority_jobs_drops_queued_preheats() -> None:
    """discard_low_priority_jobs 应丢弃排队中的预热任务且不影响高优先级任务。"""
    worker = PptComWorker(name="test-ppt-com-discard")
    executed: list[str] = []
    gate = threading.Event()
    done = threading.Event()

    try:
        worker.submit("blocker", lambda: gate.wait(5.0))
        time.sleep(0.05)
        worker.submit("preheat", lambda: executed.append("low"), low_priority=True)
        worker.submit("open", lambda: (executed.append("high"), done.set()))

        discarded = worker.discard_low_priority_jobs()

        gate.set()
        assert done.wait(5.0)
        assert discarded == 1
        assert executed == ["high"]
    finally:
        worker.shutdown(timeout_seconds=5.0)


def test_shutdown_drops_queued_low_priority_jobs() -> None:
    """关闭时应丢弃未执行的低优先级任务，避免退出阶段再拉起 PowerPoint。"""
    worker = PptComWorker(name="test-ppt-com-shutdown-low")
    executed: list[str] = []
    gate = threading.Event()

    worker.submit("blocker", lambda: gate.wait(5.0))
    time.sleep(0.05)
    worker.submit("preheat", lambda: executed.append("low"), low_priority=True)
    worker.submit("close", lambda: executed.append("high"))
    gate.set()

    assert worker.shutdown(timeout_seconds=5.0) is True
    assert executed == ["high"]


def test_com_initialization_failure_rejects_job_without_wait_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """STA 初始化失败时，提交任务应立即失败而不是挂起到调用超时。"""
    worker = PptComWorker(name="test-ppt-com-init-failure")
    monkeypatch.setattr(worker, "_initialize_com", lambda: False)
    completed = threading.Event()
    errors: list[BaseException | None] = []

    worker.submit(
        "should-not-run",
        lambda: pytest.fail("COM 未初始化时不应执行任务"),
        on_done=lambda _result, error: (errors.append(error), completed.set()),
    )

    assert completed.wait(timeout=1.0)
    assert isinstance(errors[0], RuntimeError)
