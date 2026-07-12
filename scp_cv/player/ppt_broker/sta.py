#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PowerPoint Broker 的单 STA 与优先级任务队列内部 seam。
@Project : SCP-cv
@File : sta.py
@Author : Qintsg
@Date : 2026-07-11
'''
from __future__ import annotations

import logging
import threading
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar

logger = logging.getLogger(__name__)
_ResultT = TypeVar("_ResultT")


@dataclass(slots=True)
class _StaJob:
    """提交给 STA 的一次同步调用。"""

    callback: Callable[[], object]
    done: threading.Event
    result: object = None
    error: BaseException | None = None


class StaExecutor:
    """带消息泵和高低优先级队列的单 STA 执行器。"""

    def __init__(self, name: str = "ppt-broker-sta") -> None:
        self._name = name
        self._high_jobs: deque[_StaJob] = deque()
        self._low_jobs: deque[_StaJob] = deque()
        self._condition = threading.Condition()
        self._started = threading.Event()
        self._thread_id = 0
        self._stopping = False
        self._accepting_low_priority = True
        self._com_initialized = False
        self._com_init_error: Exception | None = None
        self._thread = threading.Thread(target=self._run, name=name, daemon=True)
        self._thread.start()
        if not self._started.wait(5.0):
            raise RuntimeError("PowerPoint Broker STA 线程启动超时")

    @property
    def com_initialized(self) -> bool:
        """当前 STA 是否已成功初始化 COM。"""
        return self._com_initialized

    @property
    def com_init_error(self) -> Exception | None:
        """COM 初始化失败的原始异常。"""
        return self._com_init_error

    def call(
        self,
        callback: Callable[[], _ResultT],
        *,
        timeout_seconds: float = 120.0,
        low_priority: bool = False,
    ) -> _ResultT:
        """在 STA 中执行 callback 并返回结果。"""
        if threading.get_ident() == self._thread_id:
            return callback()
        job = _StaJob(callback=callback, done=threading.Event())
        with self._condition:
            if self._stopping:
                raise RuntimeError("PowerPoint Broker STA 已关闭")
            if low_priority and not self._accepting_low_priority:
                raise RuntimeError("PowerPoint Broker STA 已关闭，低优先级任务已取消")
            target_queue = self._low_jobs if low_priority else self._high_jobs
            target_queue.append(job)
            self._condition.notify_all()
        if not job.done.wait(max(0.1, timeout_seconds)):
            raise TimeoutError("等待 PowerPoint Broker STA 操作超时")
        if job.error is not None:
            raise job.error
        return job.result  # type: ignore[return-value]

    def shutdown(
        self,
        timeout_seconds: float = 10.0,
        *,
        final_callback: Callable[[], object] | None = None,
    ) -> None:
        """停止接收新任务，排空高优先级队列后执行最终回调。"""
        final_job: _StaJob | None = None
        with self._condition:
            cancelled_jobs = self._cancel_low_priority_jobs_locked()
            if not self._stopping:
                self._stopping = True
                if final_callback is not None:
                    final_job = _StaJob(
                        callback=final_callback,
                        done=threading.Event(),
                    )
                    self._high_jobs.append(final_job)
            self._condition.notify_all()
        self._finish_cancelled_jobs(cancelled_jobs)
        if threading.get_ident() == self._thread_id:
            return
        self._thread.join(max(0.1, timeout_seconds))
        if self._thread.is_alive():
            raise TimeoutError("PowerPoint Broker STA 线程关闭超时")
        if final_job is not None and final_job.error is not None:
            raise final_job.error

    def stop_accepting_low_priority(self) -> None:
        """拒绝新低优先级任务，并唤醒所有尚未执行的调用方。"""
        with self._condition:
            cancelled_jobs = self._cancel_low_priority_jobs_locked()
        self._finish_cancelled_jobs(cancelled_jobs)

    def _cancel_low_priority_jobs_locked(self) -> list[_StaJob]:
        self._accepting_low_priority = False
        cancelled_jobs = list(self._low_jobs)
        self._low_jobs.clear()
        return cancelled_jobs

    @staticmethod
    def _finish_cancelled_jobs(cancelled_jobs: list[_StaJob]) -> None:
        for cancelled_job in cancelled_jobs:
            cancelled_job.error = RuntimeError(
                "PowerPoint Broker STA 已关闭，低优先级任务已取消"
            )
            cancelled_job.done.set()

    def _run(self) -> None:
        self._thread_id = threading.get_ident()
        pythoncom = self._initialize_com()
        self._started.set()
        try:
            while True:
                job = self._next_job()
                if job is None:
                    return
                try:
                    job.result = job.callback()
                except BaseException as job_error:
                    job.error = job_error
                finally:
                    job.done.set()
                    self._pump_messages(pythoncom)
        finally:
            self._uninitialize_com(pythoncom)
            self._thread_id = 0

    def _next_job(self) -> _StaJob | None:
        with self._condition:
            while True:
                if self._high_jobs:
                    return self._high_jobs.popleft()
                if self._low_jobs and not self._stopping:
                    return self._low_jobs.popleft()
                if self._stopping:
                    return None
                self._condition.wait(timeout=0.05)
                self._pump_messages_safely()

    def _initialize_com(self) -> object | None:
        try:
            import pythoncom

            coinit_sta = getattr(pythoncom, "COINIT_APARTMENTTHREADED", 2)
            co_initialize_ex = getattr(pythoncom, "CoInitializeEx", None)
            if callable(co_initialize_ex):
                co_initialize_ex(coinit_sta)
            else:
                pythoncom.CoInitialize()
            self._com_initialized = True
            return pythoncom
        except Exception as init_error:
            self._com_init_error = init_error
            logger.warning("PowerPoint Broker STA 初始化 COM 失败：%s", init_error)
            return None

    @staticmethod
    def _pump_messages(pythoncom: object | None) -> None:
        if pythoncom is None:
            return
        pump = getattr(pythoncom, "PumpWaitingMessages", None)
        if callable(pump):
            try:
                pump()
            except Exception:
                pass

    @staticmethod
    def _pump_messages_safely() -> None:
        try:
            import pythoncom

            pump = getattr(pythoncom, "PumpWaitingMessages", None)
            if callable(pump):
                pump()
        except Exception:
            pass

    @staticmethod
    def _uninitialize_com(pythoncom: object | None) -> None:
        if pythoncom is None:
            return
        try:
            pythoncom.CoUninitialize()  # type: ignore[attr-defined]
        except Exception:
            pass


__all__ = ["StaExecutor"]
