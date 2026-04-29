#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
gRPC 显示器管理 mixin：列出/切换显示目标与拼接配置。
@Project : SCP-cv
@File : display.py
@Author : Qintsg
@Date : 2026-04-29
'''
from __future__ import annotations

import grpc

from scp_cv.grpc_generated.scp_cv.v1 import control_pb2
from scp_cv.services.display import (
    build_left_right_splice_target,
    list_display_targets,
)
from scp_cv.services.playback import (
    PlaybackError,
    select_display_target,
)

from .helpers import (
    _error_reply,
    _extract_window_id,
    _publish_playback_state_event,
    _success_reply,
)


class DisplayMixin:
    """显示器目标管理相关的 gRPC 方法。"""

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
            _publish_playback_state_event()
            return _success_reply(
                message=f"窗口 {window_id} 显示目标已切换",
                detail=f"{session.get_display_mode_display()} — {session.target_display_label}",
            )
        except PlaybackError as playback_err:
            return _error_reply(str(playback_err))
