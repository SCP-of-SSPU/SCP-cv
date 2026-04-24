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

    # 先推送一次当前完整状态作为初始化数据
    with _event_lock:
        pending_messages, current_sequence = _collect_pending_messages_locked(
            current_sequence,
        )
    for pending_message in pending_messages:
        yield pending_message

    # 持续等待并推送新事件
    while True:
        with _event_condition:
            # 等待新事件，超时 30 秒发送心跳保活
            _event_condition.wait(timeout=30.0)

            # 只在锁内复制消息，实际 yield 放到锁外，避免阻塞发布者。
            pending_messages, current_sequence = _collect_pending_messages_locked(
                current_sequence,
            )

        if pending_messages:
            for pending_message in pending_messages:
                yield pending_message
        else:
            yield ": heartbeat\n\n"


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


def get_current_sequence() -> int:
    """
    获取当前事件序列号。
    :return: 最新的事件序列号
    """
    with _event_lock:
        return _event_sequence
