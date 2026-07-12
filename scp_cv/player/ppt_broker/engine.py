#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PowerPoint Broker 会话注册表与单 STA 串行执行引擎。
@Project : SCP-cv
@File : engine.py
@Author : Qintsg
@Date : 2026-07-11
'''
from __future__ import annotations

import logging
import os
import threading
import time
import uuid
from dataclasses import dataclass, replace
from typing import Protocol

from scp_cv.player.ppt_broker.contracts import (
    BrokerHealth,
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
from scp_cv.player.ppt_broker.sta import StaExecutor

logger = logging.getLogger(__name__)


class PptBackend(Protocol):
    """仅供 Broker 实现使用的 PowerPoint 后端 seam。"""

    def open(self, request: PptOpenRequest) -> object: ...

    def command(self, handle: object, request: PptCommandRequest) -> None: ...

    def get_state(self, handle: object) -> PptState: ...

    def hide(self, handle: object) -> None: ...

    def show(self, handle: object) -> None: ...

    def close(self, handle: object) -> None: ...

    def preheat(self, request: PptPreheatRequest) -> None: ...

    def export_show(self, request: PptShowExportRequest) -> PptExportResult: ...

    def export_slides(self, request: PptSlideExportRequest) -> PptExportResult: ...

    def shutdown(self) -> None: ...


@dataclass(slots=True)
class _RegisteredSession:
    """Broker 内部会话所有权记录。"""

    key: PptSessionKey
    handle: object
    source_id: int
    last_state: PptState


class PptBrokerEngine:
    """把全部 PowerPoint 行为收进一个 STA 和一个会话注册表。"""

    def __init__(self, backend: PptBackend, *, generation: str | None = None) -> None:
        self._backend = backend
        self._generation = generation or uuid.uuid4().hex
        self._sessions: dict[int, _RegisteredSession] = {}
        self._executor = StaExecutor()
        if bool(getattr(backend, "requires_com", False)) and not self._executor.com_initialized:
            init_error = self._executor.com_init_error
            self._executor.shutdown()
            raise RuntimeError(
                "PowerPoint Broker 无法初始化 COM STA；请确认正在 Windows 交互桌面运行，"
                "并检查 pywin32 安装。"
            ) from init_error
        self._shutdown_lock = threading.Lock()
        self._closed = False

    def open(self, request: PptOpenRequest) -> PptState:
        """事务式打开并替换同一播放器窗口的旧会话。"""
        started_at = time.perf_counter()
        try:
            state = self._executor.call(lambda: self._open_on_sta(request))
        except BaseException as open_error:
            self._log_lifecycle(
                "open",
                started_at,
                request_id=request.request_id,
                window_id=request.session.window_id,
                source_id=request.source_id,
                state=None,
                error=open_error,
            )
            raise
        self._log_lifecycle(
            "open",
            started_at,
            request_id=request.request_id,
            window_id=request.session.window_id,
            source_id=request.source_id,
            state=state,
        )
        return state

    def command(self, request: PptCommandRequest) -> PptState:
        """串行执行控制指令并返回执行后的状态。"""
        started_at = time.perf_counter()
        try:
            state, source_id = self._executor.call(
                lambda: self._command_on_sta(request)
            )
        except BaseException as command_error:
            self._log_lifecycle(
                "command",
                started_at,
                request_id=request.request_id,
                window_id=request.session.window_id,
                source_id=0,
                state=None,
                error=command_error,
            )
            raise
        self._log_lifecycle(
            "command",
            started_at,
            request_id=request.request_id,
            window_id=request.session.window_id,
            source_id=source_id,
            state=state,
        )
        return state

    def get_state(self, session: PptSessionKey) -> PptState:
        """读取属于调用方的会话状态。"""
        return self._executor.call(
            lambda: self._get_state_on_sta(session),
            low_priority=True,
        )

    def close(self, session: PptSessionKey) -> None:
        """关闭匹配 owner_token 的会话；旧 owner 的迟到关闭为安全空操作。"""
        started_at = time.perf_counter()
        try:
            state, source_id = self._executor.call(
                lambda: self._close_on_sta(session)
            )
        except BaseException as close_error:
            self._log_lifecycle(
                "close",
                started_at,
                request_id="",
                window_id=session.window_id,
                source_id=0,
                state=None,
                error=close_error,
            )
            raise
        self._log_lifecycle(
            "close",
            started_at,
            request_id="",
            window_id=session.window_id,
            source_id=source_id,
            state=state,
        )

    def preheat(self, request: PptPreheatRequest) -> None:
        """以低优先级执行应用级或文件级预热。"""
        started_at = time.perf_counter()
        try:
            self._executor.call(
                lambda: self._backend.preheat(request),
                low_priority=True,
            )
        except BaseException as preheat_error:
            self._log_lifecycle(
                "preheat",
                started_at,
                request_id=request.request_id,
                window_id=0,
                source_id=request.source_id,
                state=None,
                error=preheat_error,
            )
            raise
        self._log_lifecycle(
            "preheat",
            started_at,
            request_id=request.request_id,
            window_id=0,
            source_id=request.source_id,
            state=None,
        )

    def export_show(self, request: PptShowExportRequest) -> PptExportResult:
        """以低优先级导出 `.ppsx`/`.pps` 放映缓存。"""
        return self._executor.call(
            lambda: self._backend.export_show(request),
            low_priority=True,
        )

    def export_slides(self, request: PptSlideExportRequest) -> PptExportResult:
        """以低优先级把各页导出为 PNG 文件。"""
        return self._executor.call(
            lambda: self._backend.export_slides(request),
            low_priority=True,
        )

    def health(self) -> BrokerHealth:
        """返回无需触碰 COM 的轻量健康快照。"""
        return BrokerHealth(
            ready=not self._closed,
            generation=self._generation,
            pid=os.getpid(),
        )

    def shutdown(self) -> None:
        """幂等关闭全部会话、后端和 STA。"""
        with self._shutdown_lock:
            if self._closed:
                return
            self._closed = True
            self._executor.shutdown(final_callback=self._shutdown_on_sta)

    def _open_on_sta(self, request: PptOpenRequest) -> PptState:
        current = self._sessions.get(request.session.window_id)
        if current is not None:
            self._backend.hide(current.handle)
        try:
            new_handle = self._backend.open(request)
        except BaseException:
            if current is not None:
                self._backend.show(current.handle)
            raise
        try:
            state = self._state_with_generation(
                self._backend.get_state(new_handle)
            )
            if current is not None:
                self._backend.close(current.handle)
        except BaseException:
            try:
                self._backend.close(new_handle)
            except Exception as cleanup_error:
                logger.warning(
                    "清理未采用的 PPT 新会话失败：%s",
                    cleanup_error,
                )
            if current is not None:
                try:
                    self._backend.show(current.handle)
                except Exception as restore_error:
                    logger.warning("恢复 PPT 旧会话失败：%s", restore_error)
            raise
        self._sessions[request.session.window_id] = _RegisteredSession(
            request.session,
            new_handle,
            request.source_id,
            state,
        )
        return state

    def _command_on_sta(self, request: PptCommandRequest) -> tuple[PptState, int]:
        registered = self._owned_session(request.session)
        self._backend.command(registered.handle, request)
        state = self._state_with_generation(
            self._backend.get_state(registered.handle)
        )
        registered.last_state = state
        return state, registered.source_id

    def _get_state_on_sta(self, session: PptSessionKey) -> PptState:
        registered = self._owned_session(session)
        state = self._state_with_generation(
            self._backend.get_state(registered.handle)
        )
        registered.last_state = state
        return state

    def _close_on_sta(self, session: PptSessionKey) -> tuple[PptState | None, int]:
        registered = self._sessions.get(session.window_id)
        if registered is None or registered.key != session:
            return None, 0
        try:
            self._backend.close(registered.handle)
        finally:
            self._sessions.pop(session.window_id, None)
        return registered.last_state, registered.source_id

    def _owned_session(self, key: PptSessionKey) -> _RegisteredSession:
        registered = self._sessions.get(key.window_id)
        if registered is None or registered.key != key:
            raise PptSessionNotFoundError(
                f"窗口 {key.window_id} 没有属于 owner={key.owner_token!r} 的 PPT 会话"
            )
        return registered

    def _shutdown_on_sta(self) -> None:
        for registered in list(self._sessions.values()):
            try:
                self._backend.close(registered.handle)
            except Exception as close_error:
                logger.warning("关闭 PPT Broker 会话失败：%s", close_error)
        self._sessions.clear()
        self._backend.shutdown()

    def _state_with_generation(self, state: PptState) -> PptState:
        return replace(state, generation=self._generation)

    def _log_lifecycle(
        self,
        event: str,
        started_at: float,
        *,
        request_id: str,
        window_id: int,
        source_id: int,
        state: PptState | None,
        error: BaseException | None = None,
    ) -> None:
        snapshot = state or PptState(powerpoint_pid=self._backend_powerpoint_pid())
        result = "failed" if error is not None else "success"
        logger.info(
            "ppt_broker_lifecycle event=%s request_id=%s window_id=%d "
            "source_id=%d broker_generation=%s broker_pid=%d "
            "powerpoint_pid=%d hwnd=%d parent_hwnd=%d elapsed_ms=%.3f "
            "result=%s error_type=%s error=%s",
            event,
            request_id or "-",
            window_id,
            source_id,
            self._generation,
            os.getpid(),
            snapshot.powerpoint_pid,
            snapshot.slideshow_hwnd,
            snapshot.parent_hwnd,
            (time.perf_counter() - started_at) * 1000.0,
            result,
            type(error).__name__ if error is not None else "-",
            str(error) if error is not None else "-",
        )

    def _backend_powerpoint_pid(self) -> int:
        try:
            process_id = getattr(self._backend, "powerpoint_pid", 0)
            if callable(process_id):
                process_id = process_id()
            return max(0, int(process_id))
        except (TypeError, ValueError, OverflowError):
            return 0


__all__ = ["PptBackend", "PptBrokerEngine"]
