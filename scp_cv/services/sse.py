#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
SSE (Server-Sent Events) 状态推送服务。
基于 Django StreamingHttpResponse 实现轻量级的实时状态推送。
@Project : SCP-cv
@File : sse.py
@Author : Qintsg
@Date : 2026-04-10
'''
from __future__ import annotations

import json
import logging
import threading
import time
from collections.abc import Generator

logger = logging.getLogger(__name__)

# 全局事件总线：存储最新的状态数据和订阅者通知机制
_event_lock = threading.Lock()
_event_condition = threading.Condition(_event_lock)
_latest_event_data: dict[str, object] = {}
_event_sequence: int = 0

# 播放器独立进程只会写数据库，Web 进程需要轮询补齐实时进度推送。
_STATE_POLL_SECONDS: float = 0.2
_HEARTBEAT_SECONDS: float = 30.0


def publish_event(event_type: str, payload: dict[str, object]) -> None:
    """
    发布一个 SSE 事件，通知所有订阅者。
    :param event_type: 事件类型标识，如 'playback_state', 'resource_updated'
    :param payload: 事件数据载荷
    """
    global _event_sequence

    with _event_condition:
        _event_sequence += 1
        _latest_event_data[event_type] = {
            "sequence": _event_sequence,
            "type": event_type,
            "data": payload,
            "timestamp": time.time(),
        }
        # 唤醒所有等待的订阅者
        _event_condition.notify_all()

    logger.debug("发布 SSE 事件 [%s] seq=%d", event_type, _event_sequence)


def event_stream(last_sequence: int = 0) -> Generator[str, None, None]:
    """
    生成 SSE 事件流，用于 StreamingHttpResponse。
    客户端断开连接时生成器将被垃圾回收。
    :param last_sequence: 客户端已知的最后序列号，避免重复推送
    :return: SSE 格式的文本流生成器
    """
    current_sequence = last_sequence
    current_state_signature = ""
    last_heartbeat_at = time.time()

    # 先推送事件总线中当前客户端尚未消费的事件。
    with _event_lock:
        pending_messages, current_sequence = _collect_pending_messages_locked(
            current_sequence,
        )
    for pending_message in pending_messages:
        yield pending_message

    # 持续等待并推送新事件
    while True:
        with _event_condition:
            # 等待事件唤醒；超时后检查播放器进程写入数据库的状态变化。
            _event_condition.wait(timeout=_STATE_POLL_SECONDS)

            # 只在锁内复制消息，实际 yield 放到锁外，避免阻塞发布者。
            pending_messages, current_sequence = _collect_pending_messages_locked(
                current_sequence,
            )

        if pending_messages:
            for pending_message in pending_messages:
                yield pending_message
            last_heartbeat_at = time.time()
        else:
            polled_message, current_state_signature = _build_polled_state_message(
                current_state_signature,
            )
            if polled_message:
                yield polled_message
                last_heartbeat_at = time.time()
                continue
            now = time.time()
            if now - last_heartbeat_at >= _HEARTBEAT_SECONDS:
                yield ": heartbeat\n\n"
                last_heartbeat_at = now


def _collect_pending_messages_locked(current_sequence: int) -> tuple[list[str], int]:
    """
    收集当前锁保护下的新事件消息。
    :param current_sequence: 客户端已收到的最大序列号
    :return: 待发送消息列表与更新后的最大序列号
    """
    pending_messages: list[str] = []
    next_sequence = current_sequence
    for event_record in _latest_event_data.values():
        record_sequence = int(event_record.get("sequence", 0))
        if record_sequence > current_sequence:
            pending_messages.append(_format_sse_message(event_record))
            next_sequence = max(next_sequence, record_sequence)
    return pending_messages, next_sequence


def _format_sse_message(event_record: dict[str, object]) -> str:
    """
    将事件记录格式化为 SSE 协议文本。
    :param event_record: 事件记录字典
    :return: SSE 格式的文本
    """
    event_type = str(event_record.get("type", "message"))
    event_data = event_record.get("data", {})
    event_id = str(event_record.get("sequence", ""))

    lines: list[str] = []
    if event_id:
        lines.append(f"id: {event_id}")
    lines.append(f"event: {event_type}")
    lines.append(f"data: {json.dumps(event_data, ensure_ascii=False, default=str)}")
    lines.append("")  # 空行结束事件
    lines.append("")

    return "\n".join(lines)


def _build_polled_state_message(current_signature: str) -> tuple[str, str]:
    """
    从数据库读取播放快照并在变化时构造 SSE 消息。
    :param current_signature: 上一次已推送的快照签名
    :return: (SSE 消息或空字符串, 最新签名)
    """
    try:
        from scp_cv.services.playback import get_all_sessions_snapshot
        sessions = get_all_sessions_snapshot()
    except Exception as snapshot_error:
        logger.debug("轮询播放状态失败：%s", snapshot_error)
        return "", current_signature

    next_signature = json.dumps(sessions, ensure_ascii=False, sort_keys=True, default=str)
    if next_signature == current_signature:
        return "", current_signature
    event_record = {
        "sequence": "",
        "type": "playback_state",
        "data": {"sessions": sessions},
    }
    return _format_sse_message(event_record), next_signature


def get_current_sequence() -> int:
    """
    获取当前事件序列号。
    :return: 最新的事件序列号
    """
    with _event_lock:
        return _event_sequence
