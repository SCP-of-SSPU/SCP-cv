#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
gRPC PlaybackControlService 实现，将 proto 定义的 RPC
委托给 Django 服务层执行，并返回 protobuf 响应。
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
        打开指定媒体源到播放区域。
        :param request: OpenSourceRequest（media_source_id, autoplay）
        :param context: gRPC 服务上下文
        :return: OperationReply
        """
        media_source_id = request.media_source_id
        if media_source_id <= 0:
            return _error_reply("media_source_id 必须大于 0")

        try:
            session = open_source(
                media_source_id=int(media_source_id),
                autoplay=request.autoplay,
            )
            source_name = session.media_source.name if session.media_source else "未知"
            return _success_reply(
                message="源已打开",
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
        关闭当前播放的源。
        :param request: CloseSourceRequest
        :param context: gRPC 服务上下文
        :return: OperationReply
        """
        try:
            close_source()
            return _success_reply(message="源已关闭")
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
        发送播放控制命令（play / pause / stop）。
        :param request: ControlPlaybackRequest（action）
        :param context: gRPC 服务上下文
        :return: OperationReply
        """
        action = _PLAYBACK_ACTION_MAP.get(request.action)
        if action is None:
            return _error_reply("无效的播放控制动作")

        try:
            control_playback(action)
            return _success_reply(message=f"已发送 {action} 指令")
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
        发送内容导航指令（翻页 / 跳转位置）。
        :param request: NavigateContentRequest（action, target_index, position_ms）
        :param context: gRPC 服务上下文
        :return: OperationReply
        """
        action = _NAVIGATE_ACTION_MAP.get(request.action)
        if action is None:
            return _error_reply("无效的导航动作")

        try:
            navigate_content(
                action=action,
                target_index=request.target_index,
                position_ms=request.position_ms,
            )
            return _success_reply(message=f"已发送 {action} 指令")
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
        返回当前播放会话的运行时状态摘要。
        :param request: EmptyRequest
        :param context: gRPC 服务上下文
        :return: RuntimeStatusReply
        """
        snapshot = get_session_snapshot()
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
        返回详细的播放状态（含 PPT 页码和视频进度）。
        :param request: EmptyRequest
        :param context: gRPC 服务上下文
        :return: PlaybackStateReply
        """
        snapshot = get_session_snapshot()
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
        切换显示目标（单屏或左右拼接模式）。
        :param request: SelectDisplayTargetRequest（display_mode, target_label）
        :param context: gRPC 服务上下文
        :return: OperationReply
        """
        display_mode = request.display_mode.strip()
        target_label = request.target_label.strip()

        if not display_mode:
            return _error_reply("display_mode 不能为空")

        try:
            session = select_display_target(
                display_mode=display_mode,
                target_display_name=target_label,
            )
            return _success_reply(
                message="显示目标已切换",
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
        停止当前播放的内容（兼容旧接口，内部调用 close_source）。
        :param request: EmptyRequest
        :param context: gRPC 服务上下文
        :return: OperationReply
        """
        try:
            stop_current_content()
            return _success_reply(message="播放已停止")
        except PlaybackError as playback_err:
            return _error_reply(str(playback_err))
