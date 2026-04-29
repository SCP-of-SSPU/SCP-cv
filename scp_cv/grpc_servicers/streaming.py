#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
gRPC 服务端流式推送 mixin：WatchPlaybackState 持续推送播放状态变更。
@Project : SCP-cv
@File : streaming.py
@Author : Qintsg
@Date : 2026-04-29
'''
from __future__ import annotations

import time

import grpc

from scp_cv.grpc_generated.scp_cv.v1 import control_pb2
from scp_cv.services.playback import get_all_sessions_snapshot

from .helpers import (
    _STATE_WATCH_POLL_SECONDS,
    _session_snapshot_signature,
    _snapshot_to_proto,
)


class StreamingMixin:
    """服务端流式推送相关的 gRPC 方法。"""

    def WatchPlaybackState(
        self,
        request: control_pb2.EmptyRequest,
        context: grpc.ServicerContext,
    ) -> None:
        """
        服务端流式推送播放状态变更，替代 SSE。
        客户端发起此调用后持续接收状态变化事件，直到断开连接。
        结合事件总线唤醒与 DB 快照对比，兼容播放器独立进程回写状态。
        :param request: EmptyRequest
        :param context: gRPC 服务上下文（客户端取消时 is_active() 返回 False）
        """
        from scp_cv.services.sse import (
            _event_condition,
            _latest_event_data,
        )

        with _event_condition:
            current_sequence = max(
                (
                    int(event_record.get("sequence", 0))
                    for event_record in _latest_event_data.values()
                ),
                default=0,
            )

        # 先推送当前完整状态作为初始帧
        initial_snapshots = get_all_sessions_snapshot()
        current_signature = _session_snapshot_signature(initial_snapshots)
        initial_event = control_pb2.PlaybackStateEvent(
            event_type="initial_state",
            sequence=0,
            sessions=[_snapshot_to_proto(s) for s in initial_snapshots],
            timestamp=time.time(),
        )
        yield initial_event

        # 持续监听新事件
        while context.is_active():
            with _event_condition:
                # 等待事件唤醒；超时后检查播放器进程写入 DB 的状态变化。
                _event_condition.wait(timeout=_STATE_WATCH_POLL_SECONDS)

                pending_events: list[tuple[str, int]] = []
                for event_type, event_record in _latest_event_data.items():
                    record_sequence = int(event_record.get("sequence", 0))
                    if record_sequence > current_sequence:
                        pending_events.append((str(event_type), record_sequence))

            # DB 查询和 yield 都放在条件锁外，保证发布线程不被慢客户端阻塞。
            all_snapshots = get_all_sessions_snapshot()
            next_signature = _session_snapshot_signature(all_snapshots)
            if not pending_events and next_signature == current_signature:
                continue

            event_type = pending_events[-1][0] if pending_events else "playback_state"
            if pending_events:
                current_sequence = max(seq for _event_type, seq in pending_events)

            current_signature = next_signature
            state_event = control_pb2.PlaybackStateEvent(
                event_type=event_type,
                sequence=current_sequence,
                sessions=[
                    _snapshot_to_proto(s) for s in all_snapshots
                ],
                timestamp=time.time(),
            )
            yield state_event
