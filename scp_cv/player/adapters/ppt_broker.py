#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PowerPoint Broker 的播放器 SourceAdapter。
@Project : SCP-cv
@File : ppt_broker.py
@Author : Qintsg
@Date : 2026-07-11
'''
from __future__ import annotations

import threading
import uuid
from collections.abc import Callable
from concurrent.futures import CancelledError

from scp_cv.player.adapters.base import AdapterState, SourceAdapter
from scp_cv.player.ppt_broker import (
    PptBroker,
    PptCommand,
    PptCommandRequest,
    PptOpenRequest,
    PptSessionKey,
    PptState,
)


class PptBrokerSourceAdapter(SourceAdapter):
    """把 SourceAdapter 的窗口语义映射到唯一 PowerPoint Broker。"""

    def __init__(
        self,
        *,
        broker: PptBroker,
        window_id: int,
        owner_prefix: str,
        adapter_name: str = "ppt",
    ) -> None:
        super().__init__(adapter_name=adapter_name)
        if broker is None:
            raise ValueError(
                "PPT 播放器未连接 PowerPoint Broker；"
                "请通过 runall 启动，或先运行 manage.py run_ppt_broker。"
            )
        if window_id <= 0:
            raise ValueError("PPT Broker Adapter window_id 必须大于 0")
        if not owner_prefix.strip():
            raise ValueError("PPT Broker Adapter owner_prefix 不能为空")
        self._broker = broker
        self._session = PptSessionKey(
            window_id=window_id,
            owner_token=f"{owner_prefix}:{uuid.uuid4().hex}",
        )
        self._source_id = 0
        self._state_lock = threading.Lock()
        self._cached_state = AdapterState()
        self._lifecycle_lock = threading.Lock()
        self._broker_lifecycle_lock = threading.Lock()
        self._lifecycle_generation = 0

    def set_preheat_context(
        self,
        source_id: int,
        preheat_enabled: bool,
        preheat_pool: object | None,
    ) -> None:
        """保存源标识；PPT 预热由 Broker 统一管理。"""
        del preheat_enabled, preheat_pool
        self._source_id = max(0, int(source_id))

    def open(self, uri: str, window_handle: int, autoplay: bool = True) -> None:
        """通过 Broker 打开并嵌入 PowerPoint 放映。"""
        request = PptOpenRequest(
            session=self._session,
            uri=uri,
            parent_hwnd=int(window_handle),
            autoplay=autoplay,
            source_id=self._source_id,
            request_id=uuid.uuid4().hex,
        )
        lifecycle_generation = self._register_open()
        self._open_registered(request, lifecycle_generation)

    def open_async(
        self,
        uri: str,
        window_handle: int,
        autoplay: bool = True,
        start_slide: int = 0,
        on_finished: Callable[[BaseException | None], None] | None = None,
    ) -> None:
        """在客户端后台线程等待 Broker 打开，完成后回调控制器。"""
        request = PptOpenRequest(
            session=self._session,
            uri=uri,
            parent_hwnd=int(window_handle),
            autoplay=autoplay,
            start_slide=max(1, int(start_slide or 1)),
            source_id=self._source_id,
            request_id=uuid.uuid4().hex,
        )
        lifecycle_generation = self._register_open()

        def run_open() -> None:
            error: BaseException | None = None
            try:
                self._open_registered(request, lifecycle_generation)
            except BaseException as open_error:
                error = open_error
            if on_finished is not None:
                on_finished(error)

        threading.Thread(
            target=run_open,
            daemon=True,
            name=f"ppt-broker-open-{self._session.window_id}",
        ).start()

    def close(self) -> None:
        """幂等关闭仅属于本 Adapter token 的 Broker 会话。"""
        lifecycle_generation = self._register_close()
        try:
            with self._broker_lifecycle_lock:
                if self._is_current_lifecycle(lifecycle_generation):
                    self._broker.close(self._session)
        finally:
            with self._lifecycle_lock:
                if lifecycle_generation == self._lifecycle_generation:
                    self._clear_state()

    def play(self) -> None:
        self._execute(PptCommand.PLAY)

    def pause(self) -> None:
        self._execute(PptCommand.PAUSE)

    def stop(self) -> None:
        self._execute(PptCommand.STOP)

    def next_item(self) -> None:
        self._execute(PptCommand.NEXT)

    def prev_item(self) -> None:
        self._execute(PptCommand.PREVIOUS)

    def goto_item(self, index: int) -> None:
        self._execute(PptCommand.GOTO, slide_index=int(index))

    def control_media(
        self,
        media_id: str,
        action: str,
        media_index: int = 0,
    ) -> None:
        self._execute(
            PptCommand.CONTROL_MEDIA,
            media_id=media_id,
            media_action=action,
            media_index=int(media_index),
        )

    def set_volume(self, volume: int) -> None:
        del volume

    def set_mute(self, muted: bool) -> None:
        del muted

    def resize_output(self, width: int, height: int) -> None:
        """通知 Broker 按 Player 父容器的实时客户区同步 HWND。"""
        del width, height
        if self.is_open:
            self._execute(PptCommand.RESIZE)

    def detach_for_fast_switch(self) -> None:
        """Broker 的事务式 open 负责隐藏旧放映。"""

    def restore_after_failed_switch(self) -> None:
        """Broker 的事务式 open 负责恢复旧放映。"""

    def get_state(self) -> AdapterState:
        if not self.is_open:
            with self._state_lock:
                return self._cached_state
        state = self._broker.get_state(self._session)
        self._store_state(state)
        with self._state_lock:
            return self._cached_state

    def _execute(
        self,
        command: PptCommand,
        *,
        slide_index: int = 0,
        media_id: str = "",
        media_action: str = "",
        media_index: int = 0,
    ) -> None:
        state = self._broker.command(
            PptCommandRequest(
                session=self._session,
                command=command,
                slide_index=slide_index,
                media_id=media_id,
                media_action=media_action,
                media_index=media_index,
                request_id=uuid.uuid4().hex,
            )
        )
        self._store_state(state)

    def _store_state(self, state: PptState) -> None:
        snapshot = AdapterState(
            playback_state=state.playback_state,
            current_slide=state.current_slide,
            total_slides=state.total_slides,
            error_message=state.error_message,
        )
        with self._state_lock:
            self._cached_state = snapshot

    def _register_open(self) -> int:
        """登记新的打开意图，并使更早的打开结果失效。"""
        with self._lifecycle_lock:
            self._lifecycle_generation += 1
            return self._lifecycle_generation

    def _register_close(self) -> int:
        """登记关闭意图，使所有已经登记但尚未完成的打开失效。"""
        with self._lifecycle_lock:
            self._lifecycle_generation += 1
            return self._lifecycle_generation

    def _open_registered(
        self,
        request: PptOpenRequest,
        lifecycle_generation: int,
    ) -> None:
        """按登记顺序打开；失效结果在返回前从 Broker 回收。"""
        with self._broker_lifecycle_lock:
            if not self._is_current_lifecycle(lifecycle_generation):
                raise self._cancelled_open_error()

            state = self._broker.open(request)
            with self._lifecycle_lock:
                if lifecycle_generation == self._lifecycle_generation:
                    self._store_state(state)
                    self._mark_open()
                    return

            try:
                self._broker.close(self._session)
            finally:
                self._clear_state()
            raise self._cancelled_open_error()

    def _is_current_lifecycle(self, lifecycle_generation: int) -> bool:
        """判断操作是否仍代表调用方最后登记的生命周期意图。"""
        with self._lifecycle_lock:
            return lifecycle_generation == self._lifecycle_generation

    def _clear_state(self) -> None:
        """把本地快照恢复为空闲，且不触碰 Broker。"""
        self._mark_closed()
        with self._state_lock:
            self._cached_state = AdapterState()

    @staticmethod
    def _cancelled_open_error() -> CancelledError:
        """构造可由异步回调识别的打开取消错误。"""
        return CancelledError("PPT 异步打开已被后续关闭或替换操作取消")


__all__ = ["PptBrokerSourceAdapter"]
