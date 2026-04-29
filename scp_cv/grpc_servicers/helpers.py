#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
gRPC 服务层公共工具：proto 字段提取、响应构建、类型转换与事件发布。
@Project : SCP-cv
@File : helpers.py
@Author : Qintsg
@Date : 2026-04-29
'''
from __future__ import annotations

import json
import logging
from typing import Any

from scp_cv.grpc_generated.scp_cv.v1 import control_pb2

logger = logging.getLogger(__name__)

# 当 proto 请求中未携带 window_id（int32 默认值 0）时，回退到窗口 1
_DEFAULT_WINDOW_ID: int = 1

# gRPC 状态流的 DB 快照检测间隔。播放器进程通过 DB 回写状态，
# Django 进程无法收到进程内事件时仍需用轻量轮询补齐推送。
_STATE_WATCH_POLL_SECONDS: float = 0.2

# ── Proto Action → PlaybackCommand 映射 ──
_PLAYBACK_ACTION_MAP: dict[int, str] = {
    control_pb2.ACTION_PLAY: "play",
    control_pb2.ACTION_PAUSE: "pause",
    control_pb2.ACTION_STOP: "stop",
}

_NAVIGATE_ACTION_MAP: dict[int, str] = {
    control_pb2.NAV_NEXT: "next",
    control_pb2.NAV_PREV: "prev",
    control_pb2.NAV_GOTO: "goto",
    control_pb2.NAV_SEEK: "seek",
}


def _extract_window_id(request: object) -> int:
    """
    从 proto 请求中提取 window_id，未设置时回退到默认窗口。
    proto3 的 int32 默认值为 0，此处将 0 视为"未指定"并回退。
    :param request: protobuf 请求对象
    :return: 有效的窗口编号（1-4）
    """
    raw_window_id = getattr(request, "window_id", 0)
    return raw_window_id if raw_window_id > 0 else _DEFAULT_WINDOW_ID


def _success_reply(message: str = "操作成功", detail: str = "") -> control_pb2.OperationReply:
    """
    构建成功的 OperationReply。
    :param message: 简要描述
    :param detail: 补充信息
    :return: OperationReply protobuf 实例
    """
    return control_pb2.OperationReply(success=True, message=message, detail=detail)


def _error_reply(message: str, detail: str = "") -> control_pb2.OperationReply:
    """
    构建失败的 OperationReply。
    :param message: 错误描述
    :param detail: 补充信息
    :return: OperationReply protobuf 实例
    """
    return control_pb2.OperationReply(success=False, message=message, detail=detail)


def _snapshot_to_proto(snapshot: dict[str, Any]) -> control_pb2.SessionSnapshot:
    """
    将服务层返回的会话快照字典转换为 proto SessionSnapshot 消息。
    :param snapshot: get_session_snapshot() 返回的字典
    :return: proto SessionSnapshot 实例
    """
    return control_pb2.SessionSnapshot(
        window_id=int(snapshot["window_id"]),
        session_id=int(snapshot["session_id"]),
        source_name=str(snapshot["source_name"]),
        source_type=str(snapshot["source_type"]),
        source_type_label=str(snapshot["source_type_label"]),
        source_uri=str(snapshot["source_uri"]),
        playback_state=str(snapshot["playback_state"]),
        playback_state_label=str(snapshot["playback_state_label"]),
        display_mode=str(snapshot["display_mode"]),
        display_mode_label=str(snapshot["display_mode_label"]),
        target_display_label=str(snapshot["target_display_label"]),
        spliced_display_label=str(snapshot["spliced_display_label"]),
        is_spliced=bool(snapshot["is_spliced"]),
        current_slide=int(snapshot["current_slide"]),
        total_slides=int(snapshot["total_slides"]),
        position_ms=int(snapshot["position_ms"]),
        duration_ms=int(snapshot["duration_ms"]),
        pending_command=str(snapshot["pending_command"]),
        last_updated_at=str(snapshot["last_updated_at"]),
        loop_enabled=bool(snapshot["loop_enabled"]),
    )


def _source_to_proto(source_dict: dict[str, Any]) -> control_pb2.SourceItem:
    """
    将服务层返回的媒体源字典转换为 proto SourceItem 消息。
    :param source_dict: list_media_sources() 返回的字典元素
    :return: proto SourceItem 实例
    """
    return control_pb2.SourceItem(
        id=int(source_dict["id"]),
        source_type=str(source_dict["source_type"]),
        name=str(source_dict["name"]),
        uri=str(source_dict["uri"]),
        is_available=bool(source_dict["is_available"]),
        stream_identifier=str(source_dict.get("stream_identifier", "") or ""),
        created_at=str(source_dict.get("created_at", "")),
    )


def _session_snapshot_signature(snapshots: list[dict[str, Any]]) -> str:
    """
    构建会话快照签名，用于 gRPC 状态流去重。
    :param snapshots: get_all_sessions_snapshot() 返回的快照列表
    :return: 稳定 JSON 字符串签名
    """
    return json.dumps(snapshots, ensure_ascii=False, sort_keys=True, default=str)


def _publish_playback_state_event() -> None:
    """
    发布播放状态变更事件，唤醒 SSE 与 gRPC 流式订阅者。
    事件载荷保持为全量窗口快照，便于客户端一次性同步 UI。
    """
    from scp_cv.services.playback import get_all_sessions_snapshot
    from scp_cv.services.sse import publish_event

    publish_event("playback_state", {
        "sessions": get_all_sessions_snapshot(),
    })


def _scenario_dict_to_proto(scenario_dict: dict[str, Any]) -> control_pb2.ScenarioItem:
    """
    将服务层返回的预案字典转换为 proto ScenarioItem 消息。
    :param scenario_dict: list_scenarios() / _scenario_to_dict() 返回的字典
    :return: proto ScenarioItem 实例
    """
    return control_pb2.ScenarioItem(
        id=int(scenario_dict["id"]),
        name=str(scenario_dict["name"]),
        description=str(scenario_dict.get("description", "")),
        window1=control_pb2.ScenarioWindowSlot(
            source_id=int(scenario_dict.get("window1_source_id") or 0),
            autoplay=bool(scenario_dict.get("window1_autoplay", True)),
            resume=bool(scenario_dict.get("window1_resume", True)),
            source_name=str(scenario_dict.get("window1_source_name", "")),
        ),
        window2=control_pb2.ScenarioWindowSlot(
            source_id=int(scenario_dict.get("window2_source_id") or 0),
            autoplay=bool(scenario_dict.get("window2_autoplay", True)),
            resume=bool(scenario_dict.get("window2_resume", True)),
            source_name=str(scenario_dict.get("window2_source_name", "")),
        ),
        created_at=str(scenario_dict.get("created_at", "")),
        updated_at=str(scenario_dict.get("updated_at", "")),
    )
