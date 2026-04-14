#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
gRPC PlaybackControlService 实现，将 proto 定义的 RPC
委托给 Django 服务层执行，并返回 protobuf 响应。
@Project : SCP-cv
@File : grpc_servicers.py
@Author : Qintsg
@Date : 2026-04-10
'''
from __future__ import annotations

import logging

import grpc
from django.conf import settings

from scp_cv.apps.streams.models import StreamSource
from scp_cv.grpc_generated.scp_cv.v1 import control_pb2
from scp_cv.grpc_generated.scp_cv.v1 import control_pb2_grpc
from scp_cv.services.display import (
    build_left_right_splice_target,
    list_display_targets,
)
from scp_cv.services.playback import (
    PlaybackError,
    get_session_snapshot,
    open_stream_source,
    select_display_target,
    stop_current_content,
)

logger = logging.getLogger(__name__)


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
    # RPC 1: GetRuntimeStatus
    # ------------------------------------------------------------------
    def GetRuntimeStatus(
        self,
        request: control_pb2.RuntimeStatusRequest,
        context: grpc.ServicerContext,
    ) -> control_pb2.RuntimeStatusReply:
        """
        返回当前播放会话的运行时状态摘要。
        :param request: RuntimeStatusRequest（空消息）
        :param context: gRPC 服务上下文
        :return: RuntimeStatusReply
        """
        snapshot = get_session_snapshot()
        grpc_port: int = getattr(settings, "GRPC_PORT", 50051)
        is_debug: bool = getattr(settings, "DEBUG", False)

        return control_pb2.RuntimeStatusReply(
            content_kind=str(snapshot["content_kind"]),
            playback_state=str(snapshot["playback_state"]),
            display_mode=str(snapshot["display_mode"]),
            grpc_endpoint=f"0.0.0.0:{grpc_port}",
            debug_mode=is_debug,
        )

    # ------------------------------------------------------------------
    # RPC 2: ListDisplayTargets
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

        # 拼接标签
        splice_label = ""
        splice_target = build_left_right_splice_target(display_targets)
        if splice_target is not None:
            splice_label = f"{splice_target.left.name} + {splice_target.right.name}"

        return control_pb2.DisplayTargetsReply(
            targets=target_items,
            splice_label=splice_label,
        )

    # ------------------------------------------------------------------
    # RPC 3: OpenStream
    # ------------------------------------------------------------------
    def OpenStream(
        self,
        request: control_pb2.OpenStreamRequest,
        context: grpc.ServicerContext,
    ) -> control_pb2.OperationReply:
        """
        按 stream_identifier 查找并打开 WebRTC 流到播放区域。
        :param request: OpenStreamRequest（stream_identifier）
        :param context: gRPC 服务上下文
        :return: OperationReply
        """
        identifier = request.stream_identifier.strip()
        if not identifier:
            return _error_reply("stream_identifier 不能为空")

        try:
            stream = StreamSource.objects.get(stream_identifier=identifier)
        except StreamSource.DoesNotExist:
            return _error_reply(f"流标识符「{identifier}」未注册")

        try:
            session = open_stream_source(stream.pk)
            return _success_reply(
                message="流已打开",
                detail=f"{stream.name}（{identifier}）",
            )
        except PlaybackError as playback_err:
            return _error_reply(str(playback_err))

    # ------------------------------------------------------------------
    # RPC 4: StopCurrentContent
    # ------------------------------------------------------------------
    def StopCurrentContent(
        self,
        request: control_pb2.EmptyRequest,
        context: grpc.ServicerContext,
    ) -> control_pb2.OperationReply:
        """
        停止当前播放的内容并重置会话状态。
        :param request: EmptyRequest
        :param context: gRPC 服务上下文
        :return: OperationReply
        """
        try:
            stop_current_content()
            return _success_reply(message="播放已停止")
        except PlaybackError as playback_err:
            return _error_reply(str(playback_err))

    # ------------------------------------------------------------------
    # RPC 5: SelectDisplayTarget
    # ------------------------------------------------------------------
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
