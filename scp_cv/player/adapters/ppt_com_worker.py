#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PowerPoint COM 专用工作线程。
所有 PowerPoint COM 对象统一创建并运行在该 STA 线程上，
让冷启动、打开演示文稿、放映启动等慢操作不再阻塞 Qt 主线程，
同时天然串行化多窗口放映的窗口认领，避免并发 Run 抢窗口。
任务分高/低两个优先级：前台打开、关闭等指令走高优先级，
后台预热走低优先级，保证前台操作不被预热队列挡住。
@Project : SCP-cv
@File : ppt_com_worker.py
@Author : Qintsg
@Date : 2026-06-10
'''
from __future__ import annotations

import logging
import threading
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

_DEFAULT_WAIT_TIMEOUT_SECONDS = 30.0


@dataclass
class _PptComJob:
    """单个排队的 COM 任务。"""

    description: str
    fn: Callable[[], object]
    on_done: Optional[Callable[[object, Optional[BaseException]], None]] = None


class PptComWorker:
    """
    共享 PowerPoint COM 工作线程。

    - 线程内执行 pythoncom.CoInitialize，所有任务在同一 STA 中运行；
    - submit 为后台投递（可带完成回调），submit_and_wait 为同步等待；
    - 高优先级任务（默认）始终先于低优先级任务（预热）执行，
      同一优先级内保持 FIFO，保证打开/关闭等指令的相对顺序；
    - 工作线程内再次提交任务时直接内联执行，避免自我死锁；
    - shutdown 排空剩余高优先级任务、丢弃未执行的低优先级任务。
    """

    def __init__(self, name: str = "ppt-com-worker") -> None:
        """
        初始化工作线程容器，线程在首次提交任务时才启动。
        :param name: 线程名称，便于日志和调试定位
        :return: None
        """
        self._name = name
        self._high_jobs: deque[_PptComJob] = deque()
        self._low_jobs: deque[_PptComJob] = deque()
        self._wake = threading.Condition()
        self._thread: Optional[threading.Thread] = None
        self._thread_id: Optional[int] = None
        self._lifecycle_lock = threading.Lock()
        self._shutdown_requested = False
        self._initialization_error: BaseException | None = None

    @property
    def is_current_thread(self) -> bool:
        """
        判断当前线程是否就是 COM 工作线程。
        :return: True 表示调用方已在工作线程内
        """
        return self._thread_id is not None and threading.get_ident() == self._thread_id

    @property
    def is_running(self) -> bool:
        """
        判断工作线程是否处于可接收任务状态。
        :return: True 表示线程存活且未请求关闭
        """
        return (
            not self._shutdown_requested
            and self._thread is not None
            and self._thread.is_alive()
        )

    def start(self) -> None:
        """
        启动工作线程；重复调用幂等。
        :return: None
        """
        with self._lifecycle_lock:
            if self._shutdown_requested:
                raise RuntimeError("PPT COM 工作线程已关闭，无法重新启动")
            if self._thread is not None and self._thread.is_alive():
                return
            self._thread = threading.Thread(
                target=self._run,
                daemon=True,
                name=self._name,
            )
            self._thread.start()

    def submit(
        self,
        description: str,
        fn: Callable[[], object],
        on_done: Optional[Callable[[object, Optional[BaseException]], None]] = None,
        low_priority: bool = False,
    ) -> None:
        """
        投递后台 COM 任务。
        :param description: 任务描述，用于日志
        :param fn: 在工作线程执行的可调用对象
        :param on_done: 完成回调 (result, error)，在工作线程内调用
        :param low_priority: True 表示低优先级（预热类），可被前台任务插队和丢弃
        :return: None
        """
        if self.is_current_thread:
            self._execute_job(_PptComJob(description, fn, on_done))
            return
        if self._shutdown_requested:
            error = RuntimeError("PPT COM 工作线程已关闭")
            logger.warning("丢弃 COM 任务（线程已关闭）：%s", description)
            if on_done is not None:
                on_done(None, error)
            return
        self.start()
        job = _PptComJob(description, fn, on_done)
        rejection_error: BaseException | None = None
        with self._wake:
            if self._shutdown_requested:
                rejection_error = self._initialization_error or RuntimeError(
                    "PPT COM 工作线程已关闭"
                )
            elif low_priority:
                self._low_jobs.append(job)
            else:
                self._high_jobs.append(job)
            if rejection_error is None:
                self._wake.notify_all()
        if rejection_error is not None:
            logger.warning("拒绝 COM 任务：%s：%s", description, rejection_error)
            if on_done is not None:
                on_done(None, rejection_error)

    def submit_and_wait(
        self,
        description: str,
        fn: Callable[[], object],
        timeout_seconds: float = _DEFAULT_WAIT_TIMEOUT_SECONDS,
    ) -> object:
        """
        投递任务并阻塞等待结果。
        :param description: 任务描述，用于日志
        :param fn: 在工作线程执行的可调用对象
        :param timeout_seconds: 等待超时秒数
        :return: 任务返回值
        :raises TimeoutError: 等待超时
        :raises BaseException: 任务内部抛出的原始异常
        """
        if self.is_current_thread:
            return fn()

        done_event = threading.Event()
        outcome: dict[str, object] = {}

        def record_outcome(result: object, error: Optional[BaseException]) -> None:
            outcome["result"] = result
            outcome["error"] = error
            done_event.set()

        self.submit(description, fn, on_done=record_outcome)
        if not done_event.wait(max(0.1, timeout_seconds)):
            raise TimeoutError(f"等待 PPT COM 任务超时：{description}")
        error = outcome.get("error")
        if isinstance(error, BaseException):
            raise error
        return outcome.get("result")

    def discard_low_priority_jobs(self) -> int:
        """
        丢弃所有尚未执行的低优先级任务（预热类）。
        :return: 被丢弃的任务数量
        """
        with self._wake:
            discarded = len(self._low_jobs)
            self._low_jobs.clear()
        if discarded:
            logger.info("已丢弃 %d 个排队中的低优先级 PPT 任务", discarded)
        return discarded

    def shutdown(self, timeout_seconds: float = 10.0) -> bool:
        """
        请求关闭：排空剩余高优先级任务、丢弃低优先级任务后退出线程。
        :param timeout_seconds: join 等待秒数
        :return: True 表示线程已退出
        """
        with self._lifecycle_lock:
            self._shutdown_requested = True
            worker_thread = self._thread
        with self._wake:
            self._low_jobs.clear()
            self._wake.notify_all()
        if worker_thread is None or not worker_thread.is_alive():
            return True
        worker_thread.join(timeout=max(0.1, timeout_seconds))
        still_alive = worker_thread.is_alive()
        if still_alive:
            logger.warning("PPT COM 工作线程关闭超时，可能存在挂起的 COM 调用")
        return not still_alive

    def _run(self) -> None:
        """
        工作线程主循环：初始化 COM、按优先级顺序执行任务、退出时释放 COM。
        :return: None
        """
        self._thread_id = threading.get_ident()
        com_initialized = self._initialize_com()
        if not com_initialized:
            self._initialization_error = RuntimeError("PPT COM 工作线程初始化失败")
            with self._wake:
                jobs = list(self._high_jobs) + list(self._low_jobs)
                self._high_jobs.clear()
                self._low_jobs.clear()
                self._shutdown_requested = True
            init_error = self._initialization_error
            for job in jobs:
                if job.on_done is not None:
                    try:
                        job.on_done(None, init_error)
                    except Exception as callback_error:
                        logger.error("COM 初始化失败回调异常：%s：%s", job.description, callback_error)
            self._thread_id = None
            return
        try:
            while True:
                job = self._next_job()
                if job is None:
                    break
                self._execute_job(job)
        finally:
            if com_initialized:
                self._uninitialize_com()
            self._thread_id = None

    def _next_job(self) -> Optional[_PptComJob]:
        """
        取出下一个待执行任务；高优先级优先，关闭且队列耗尽时返回 None。
        :return: 任务或 None（应退出）
        """
        with self._wake:
            while True:
                if self._high_jobs:
                    return self._high_jobs.popleft()
                if self._low_jobs and not self._shutdown_requested:
                    return self._low_jobs.popleft()
                if self._shutdown_requested:
                    return None
                self._wake.wait(timeout=1.0)

    @staticmethod
    def _execute_job(job: _PptComJob) -> None:
        """
        执行单个任务并分发完成回调。
        :param job: 待执行任务
        :return: None
        """
        result: object = None
        error: Optional[BaseException] = None
        try:
            result = job.fn()
        except BaseException as job_error:
            error = job_error
            logger.error("PPT COM 任务失败：%s：%s", job.description, job_error)
        if job.on_done is None:
            return
        try:
            job.on_done(result, error)
        except Exception as callback_error:
            logger.error(
                "PPT COM 任务回调异常：%s：%s", job.description, callback_error
            )

    @staticmethod
    def _initialize_com() -> bool:
        """
        在工作线程内初始化 COM（STA）。
        :return: True 表示初始化成功
        """
        try:
            import pythoncom

            pythoncom.CoInitialize()
            return True
        except Exception as init_error:
            logger.warning("PPT COM 线程初始化 COM 失败：%s", init_error)
            return False

    @staticmethod
    def _uninitialize_com() -> None:
        """
        释放工作线程持有的 COM 初始化。
        :return: None
        """
        try:
            import pythoncom

            pythoncom.CoUninitialize()
        except Exception:
            pass


__all__ = ["PptComWorker"]
