#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
gRPC 播放控制 mixin：播放/暂停/停止、导航、状态查询、循环、窗口 ID 显示。
@Project : SCP-cv
@File : playback.py
@Author : Qintsg
@Date : 2026-04-29
'''
from __future__ import annotations

import grpc
from django.conf import settings

from scp_cv.grpc_generated.scp_cv.v1 import control_pb2
from scp_cv.services.playback import (
    PlaybackError,
    control_playback,
    get_all_sessions_snapshot,
    get_session_snapshot,
    navigate_content,
    stop_current_content,
    toggle_loop_playback,
)

from .helpers import (
    _DEFAULT_WINDOW_ID,
    _NAVIGATE_ACTION_MAP,
    _PLAYBACK_ACTION_MAP,
    _error_reply,
    _extract_window_id,
    _publish_playback_state_event,
    _snapshot_to_proto,
    _success_reply,
)


class PlaybackControlMixin:
    """播放控制、导航与状态查询相关的 gRPC 方法。"""

    def ControlPlayback(
        self,
        request: control_pb2.ControlPlaybackRequest,
        context: grpc.ServicerContext,
    ) -> control_pb2.OperationReply:
        """
        发送播放控制命令（play / pause / stop）到指定窗口。
        :param request: ControlPlaybackRequest（window_id, action）
        :param context: gRPC 服务上下文
        :return: OperationReply
        """
        window_id = _extract_window_id(request)
        action = _PLAYBACK_ACTION_MAP.get(request.action)
        if action is None:
            return _error_reply("无效的播放控制动作")

        try:
            control_playback(window_id, action)
            _publish_playback_state_event()
            return _success_reply(message=f"窗口 {window_id} 已发送 {action} 指令")
        except PlaybackError as playback_err:
            return _error_reply(str(playback_err))

    def NavigateContent(
        self,
        request: control_pb2.NavigateContentRequest,
        context: grpc.ServicerContext,
    ) -> control_pb2.OperationReply:
        """
        发送内容导航指令（翻页 / 跳转位置）到指定窗口。
        :param request: NavigateContentRequest（window_id, action, target_index, position_ms）
        :param context: gRPC 服务上下文
        :return: OperationReply
        """
        window_id = _extract_window_id(request)
        action = _NAVIGATE_ACTION_MAP.get(request.action)
        if action is None:
            return _error_reply("无效的导航动作")

        try:
            navigate_content(
                window_id=window_id,
                action=action,
                target_index=request.target_index,
                position_ms=request.position_ms,
            )
            _publish_playback_state_event()
            return _success_reply(message=f"窗口 {window_id} 已发送 {action} 指令")
        except PlaybackError as playback_err:
            return _error_reply(str(playback_err))

    def GetRuntimeStatus(
        self,
        request: control_pb2.WindowRequest,
        context: grpc.ServicerContext,
    ) -> control_pb2.RuntimeStatusReply:
        """
        返回指定窗口播放会话的运行时状态摘要。
        :param request: WindowRequest（window_id）
        :param context: gRPC 服务上下文
        :return: RuntimeStatusReply
        """
        window_id = _extract_window_id(request)
        snapshot = get_session_snapshot(window_id)
        grpc_host: str = getattr(settings, "GRPC_HOST", "127.0.0.1")
        grpc_port: int = getattr(settings, "GRPC_PORT", 50051)
        is_debug: bool = getattr(settings, "DEBUG", False)

        return control_pb2.RuntimeStatusReply(
            source_type=str(snapshot["source_type"]),
            source_name=str(snapshot["source_name"]),
            playback_state=str(snapshot["playback_state"]),
            display_mode=str(snapshot["display_mode"]),
            grpc_endpoint=f"{_client_visible_grpc_host(grpc_host)}:{grpc_port}",
            debug_mode=is_debug,
        )

    def GetPlaybackState(
        self,
        request: control_pb2.WindowRequest,
        context: grpc.ServicerContext,
    ) -> control_pb2.PlaybackStateReply:
        """
        返回指定窗口的详细播放状态（含 PPT 页码和视频进度）。
        :param request: WindowRequest（window_id）
        :param context: gRPC 服务上下文
        :return: PlaybackStateReply
        """
        window_id = _extract_window_id(request)
        snapshot = get_session_snapshot(window_id)
        return control_pb2.PlaybackStateReply(
            playback_state=str(snapshot["playback_state"]),
            source_type=str(snapshot["source_type"]),
            source_name=str(snapshot["source_name"]),
            source_uri=str(snapshot["source_uri"]),
            current_slide=int(snapshot["current_slide"]),
            total_slides=int(snapshot["total_slides"]),
            position_ms=int(snapshot["position_ms"]),
            duration_ms=int(snapshot["duration_ms"]),
            display_mode=str(snapshot["display_mode"]),
            target_display=str(snapshot["target_display_label"]),
            is_spliced=bool(snapshot["is_spliced"]),
            loop_enabled=bool(snapshot["loop_enabled"]),
        )

    def StopCurrentContent(
        self,
        request: control_pb2.EmptyRequest,
        context: grpc.ServicerContext,
    ) -> control_pb2.OperationReply:
        """
        停止窗口 1 当前播放的内容（兼容旧接口，内部调用 close_source）。
        :param request: EmptyRequest
        :param context: gRPC 服务上下文
        :return: OperationReply
        """
        try:
            stop_current_content(_DEFAULT_WINDOW_ID)
            _publish_playback_state_event()
            return _success_reply(message="播放已停止")
        except PlaybackError as playback_err:
            return _error_reply(str(playback_err))

    def ToggleLoop(
        self,
        request: control_pb2.ToggleLoopRequest,
        context: grpc.ServicerContext,
    ) -> control_pb2.OperationReply:
        """
        切换指定窗口的循环播放模式。
        :param request: ToggleLoopRequest（window_id, enabled）
        :param context: gRPC 服务上下文
        :return: OperationReply
        """
        window_id = _extract_window_id(request)
        try:
            toggle_loop_playback(window_id, request.enabled)
            state_label = "开启" if request.enabled else "关闭"
            _publish_playback_state_event()
            return _success_reply(
                message=f"窗口 {window_id} 循环播放已{state_label}",
            )
        except PlaybackError as playback_err:
            return _error_reply(str(playback_err))

    def ShowWindowIds(
        self,
        request: control_pb2.EmptyRequest,
        context: grpc.ServicerContext,
    ) -> control_pb2.OperationReply:
        """
        触发所有窗口显示 5 秒窗口 ID 叠加标识。
        向每个窗口写入 SHOW_ID 指令。
        :param request: EmptyRequest
        :param context: gRPC 服务上下文
        :return: OperationReply
        """
        from scp_cv.apps.playback.models import PlaybackCommand as PBCmd
        from scp_cv.services.playback import VALID_WINDOW_IDS, get_or_create_session

        for wid in VALID_WINDOW_IDS:
            session = get_or_create_session(wid)
            session.pending_command = PBCmd.SHOW_ID
            session.command_args = {}
            session.save(update_fields=["pending_command", "command_args"])
        _publish_playback_state_event()
        return _success_reply(message="窗口 ID 显示指令已下发")

    def GetAllSessionSnapshots(
        self,
        request: control_pb2.EmptyRequest,
        context: grpc.ServicerContext,
    ) -> control_pb2.AllSessionSnapshotsReply:
        """
        获取所有窗口的播放会话快照列表。
        :param request: EmptyRequest
        :param context: gRPC 服务上下文
        :return: AllSessionSnapshotsReply
        """
        all_snapshots = get_all_sessions_snapshot()
        session_protos = [_snapshot_to_proto(s) for s in all_snapshots]
        return control_pb2.AllSessionSnapshotsReply(
            success=True,
            sessions=session_protos,
        )


def _client_visible_grpc_host(configured_host: str) -> str:
    """
    将监听地址转换为客户端可直接连接的展示地址。
    :param configured_host: settings.GRPC_HOST 中的监听主机
    :return: 可用于客户端连接的主机名
    """
    normalized_host = configured_host.strip() or "127.0.0.1"
    if normalized_host in {"0.0.0.0", "::"}:
        return "127.0.0.1"
    return normalized_host
