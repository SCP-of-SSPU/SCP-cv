#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
gRPC PlaybackControlService 实现，将 proto 定义的 RPC
委托给 Django 服务层执行，并返回 protobuf 响应。
每个 RPC 方法从请求中提取 window_id（proto3 int32 默认为 0），
若未提供则回退到窗口 1，确保与旧版客户端的向后兼容。
@Project : SCP-cv
@File : grpc_servicers.py
@Author : Qintsg
@Date : 2026-04-14
'''
from __future__ import annotations

import logging

import grpc
from django.conf import settings

from scp_cv.grpc_generated.scp_cv.v1 import control_pb2
from scp_cv.grpc_generated.scp_cv.v1 import control_pb2_grpc
from scp_cv.services.display import (
    build_left_right_splice_target,
    list_display_targets,
)
from scp_cv.services.playback import (
    PlaybackError,
    close_source,
    control_playback,
    get_session_snapshot,
    navigate_content,
    open_source,
    select_display_target,
    stop_current_content,
)

logger = logging.getLogger(__name__)

# 当 proto 请求中未携带 window_id（int32 默认值 0）时，回退到窗口 1
_DEFAULT_WINDOW_ID: int = 1

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


class PlaybackControlServicer(control_pb2_grpc.PlaybackControlServiceServicer):
    """PlaybackControlService 的具体实现，委托 Django 服务层处理业务逻辑。"""

    # ------------------------------------------------------------------
    # 源管理
    # ------------------------------------------------------------------
    def OpenSource(
        self,
        request: control_pb2.OpenSourceRequest,
        context: grpc.ServicerContext,
    ) -> control_pb2.OperationReply:
        """
        打开指定媒体源到指定窗口的播放区域。
        :param request: OpenSourceRequest（window_id, media_source_id, autoplay）
        :param context: gRPC 服务上下文
        :return: OperationReply
        """
        window_id = _extract_window_id(request)
        media_source_id = request.media_source_id
        if media_source_id <= 0:
            return _error_reply("media_source_id 必须大于 0")

        try:
            session = open_source(
                window_id=window_id,
                media_source_id=int(media_source_id),
                autoplay=request.autoplay,
            )
            source_name = session.media_source.name if session.media_source else "未知"
            return _success_reply(
                message=f"窗口 {window_id} 源已打开",
                detail=source_name,
            )
        except PlaybackError as playback_err:
            return _error_reply(str(playback_err))

    def CloseSource(
        self,
        request: control_pb2.CloseSourceRequest,
        context: grpc.ServicerContext,
    ) -> control_pb2.OperationReply:
        """
        关闭指定窗口当前播放的源。
        :param request: CloseSourceRequest（window_id）
        :param context: gRPC 服务上下文
        :return: OperationReply
        """
        window_id = _extract_window_id(request)
        try:
            close_source(window_id)
            return _success_reply(message=f"窗口 {window_id} 源已关闭")
        except PlaybackError as playback_err:
            return _error_reply(str(playback_err))

    # ------------------------------------------------------------------
    # 播放控制
    # ------------------------------------------------------------------
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
            return _success_reply(message=f"窗口 {window_id} 已发送 {action} 指令")
        except PlaybackError as playback_err:
            return _error_reply(str(playback_err))

    # ------------------------------------------------------------------
    # 内容导航
    # ------------------------------------------------------------------
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
            return _success_reply(message=f"窗口 {window_id} 已发送 {action} 指令")
        except PlaybackError as playback_err:
            return _error_reply(str(playback_err))

    # ------------------------------------------------------------------
    # 状态查询
    # ------------------------------------------------------------------
    def GetRuntimeStatus(
        self,
        request: control_pb2.EmptyRequest,
        context: grpc.ServicerContext,
    ) -> control_pb2.RuntimeStatusReply:
        """
        返回窗口 1 播放会话的运行时状态摘要。
        多窗口状态查询应通过 HTTP 接口或后续 GetWindowStatus RPC 实现。
        :param request: EmptyRequest
        :param context: gRPC 服务上下文
        :return: RuntimeStatusReply
        """
        # 状态查询使用窗口 1 作为默认（兼容旧客户端）
        snapshot = get_session_snapshot(_DEFAULT_WINDOW_ID)
        grpc_port: int = getattr(settings, "GRPC_PORT", 50051)
        is_debug: bool = getattr(settings, "DEBUG", False)

        return control_pb2.RuntimeStatusReply(
            source_type=str(snapshot["source_type"]),
            source_name=str(snapshot["source_name"]),
            playback_state=str(snapshot["playback_state"]),
            display_mode=str(snapshot["display_mode"]),
            grpc_endpoint=f"0.0.0.0:{grpc_port}",
            debug_mode=is_debug,
        )

    def GetPlaybackState(
        self,
        request: control_pb2.EmptyRequest,
        context: grpc.ServicerContext,
    ) -> control_pb2.PlaybackStateReply:
        """
        返回窗口 1 的详细播放状态（含 PPT 页码和视频进度）。
        多窗口状态查询应通过 HTTP 接口或后续 GetWindowState RPC 实现。
        :param request: EmptyRequest
        :param context: gRPC 服务上下文
        :return: PlaybackStateReply
        """
        # 状态查询使用窗口 1 作为默认（兼容旧客户端）
        snapshot = get_session_snapshot(_DEFAULT_WINDOW_ID)
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
        )

    # ------------------------------------------------------------------
    # 显示器管理
    # ------------------------------------------------------------------
    def ListDisplayTargets(
        self,
        request: control_pb2.EmptyRequest,
        context: grpc.ServicerContext,
    ) -> control_pb2.DisplayTargetsReply:
        """
        列出当前主机可用的显示器和拼接标签。
        :param request: EmptyRequest
        :param context: gRPC 服务上下文
        :return: DisplayTargetsReply
        """
        display_targets = list_display_targets()
        target_items = [
            control_pb2.DisplayTargetItem(
                index=dt.index,
                name=dt.name,
                width=dt.width,
                height=dt.height,
                x=dt.x,
                y=dt.y,
                is_primary=dt.is_primary,
            )
            for dt in display_targets
        ]

        splice_label = ""
        splice_target = build_left_right_splice_target(display_targets)
        if splice_target is not None:
            splice_label = f"{splice_target.left.name} + {splice_target.right.name}"

        return control_pb2.DisplayTargetsReply(
            targets=target_items,
            splice_label=splice_label,
        )

    def SelectDisplayTarget(
        self,
        request: control_pb2.SelectDisplayTargetRequest,
        context: grpc.ServicerContext,
    ) -> control_pb2.OperationReply:
        """
        切换指定窗口的显示目标（单屏或左右拼接模式）。
        :param request: SelectDisplayTargetRequest（window_id, display_mode, target_label）
        :param context: gRPC 服务上下文
        :return: OperationReply
        """
        window_id = _extract_window_id(request)
        display_mode = request.display_mode.strip()
        target_label = request.target_label.strip()

        if not display_mode:
            return _error_reply("display_mode 不能为空")

        try:
            session = select_display_target(
                window_id=window_id,
                display_mode=display_mode,
                target_display_name=target_label,
            )
            return _success_reply(
                message=f"窗口 {window_id} 显示目标已切换",
                detail=f"{session.get_display_mode_display()} — {session.target_display_label}",
            )
        except PlaybackError as playback_err:
            return _error_reply(str(playback_err))

    # ------------------------------------------------------------------
    # 兼容旧接口
    # ------------------------------------------------------------------
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
            return _success_reply(message="播放已停止")
        except PlaybackError as playback_err:
            return _error_reply(str(playback_err))
