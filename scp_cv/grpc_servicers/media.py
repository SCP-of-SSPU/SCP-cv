#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
gRPC 媒体源管理 mixin：打开/关闭源、列表、添加/删除源。
@Project : SCP-cv
@File : media.py
@Author : Qintsg
@Date : 2026-04-29
'''
from __future__ import annotations

import grpc

from scp_cv.grpc_generated.scp_cv.v1 import control_pb2
from scp_cv.services.media import (
    MediaError,
    add_local_path,
    add_web_url,
    delete_media_source,
    list_media_sources,
)
from scp_cv.services.playback import (
    PlaybackError,
    close_source,
    open_source,
)

from .helpers import (
    _error_reply,
    _extract_window_id,
    _publish_playback_state_event,
    _source_to_proto,
    _success_reply,
)


class MediaSourceServicerMixin:
    """媒体源管理相关的 gRPC 方法。"""

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
            _publish_playback_state_event()
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
            _publish_playback_state_event()
            return _success_reply(message=f"窗口 {window_id} 源已关闭")
        except PlaybackError as playback_err:
            return _error_reply(str(playback_err))

    def ListSources(
        self,
        request: control_pb2.ListSourcesRequest,
        context: grpc.ServicerContext,
    ) -> control_pb2.ListSourcesReply:
        """
        列出所有可用媒体源。可按 source_type 过滤。
        :param request: ListSourcesRequest（source_type）
        :param context: gRPC 服务上下文
        :return: ListSourcesReply
        """
        filter_type = request.source_type.strip() if request.source_type else None
        source_dicts = list_media_sources(source_type=filter_type)
        source_items = [_source_to_proto(s) for s in source_dicts]
        return control_pb2.ListSourcesReply(success=True, sources=source_items)

    def AddLocalPathSource(
        self,
        request: control_pb2.AddLocalPathSourceRequest,
        context: grpc.ServicerContext,
    ) -> control_pb2.SourceReply:
        """
        通过本地文件路径注册媒体源。
        :param request: AddLocalPathSourceRequest（path, name, source_type）
        :param context: gRPC 服务上下文
        :return: SourceReply
        """
        local_path = request.path.strip()
        if not local_path:
            return control_pb2.SourceReply(success=False, message="path 不能为空")

        display_name = request.name.strip() or None
        source_type = request.source_type.strip() or None

        try:
            media_source = add_local_path(
                local_path, display_name=display_name, source_type=source_type,
            )
            source_item = control_pb2.SourceItem(
                id=media_source.pk,
                source_type=media_source.source_type,
                name=media_source.name,
                uri=media_source.uri,
                is_available=media_source.is_available,
                stream_identifier=media_source.stream_identifier or "",
                created_at=(
                    media_source.created_at.isoformat()
                    if media_source.created_at else ""
                ),
            )
            return control_pb2.SourceReply(
                success=True, message="添加成功", source=source_item,
            )
        except MediaError as media_err:
            return control_pb2.SourceReply(success=False, message=str(media_err))

    def AddWebUrlSource(
        self,
        request: control_pb2.AddWebUrlSourceRequest,
        context: grpc.ServicerContext,
    ) -> control_pb2.SourceReply:
        """
        通过 URL 添加网页类型媒体源。
        :param request: AddWebUrlSourceRequest（url, name）
        :param context: gRPC 服务上下文
        :return: SourceReply
        """
        web_url = request.url.strip()
        if not web_url:
            return control_pb2.SourceReply(success=False, message="url 不能为空")

        display_name = request.name.strip() or None

        try:
            media_source = add_web_url(web_url, display_name=display_name)
            source_item = control_pb2.SourceItem(
                id=media_source.pk,
                source_type=media_source.source_type,
                name=media_source.name,
                uri=media_source.uri,
                is_available=media_source.is_available,
                stream_identifier=media_source.stream_identifier or "",
                created_at=(
                    media_source.created_at.isoformat()
                    if media_source.created_at else ""
                ),
            )
            return control_pb2.SourceReply(
                success=True, message="添加成功", source=source_item,
            )
        except MediaError as media_err:
            return control_pb2.SourceReply(success=False, message=str(media_err))

    def DeleteSource(
        self,
        request: control_pb2.DeleteSourceRequest,
        context: grpc.ServicerContext,
    ) -> control_pb2.OperationReply:
        """
        删除指定媒体源。
        :param request: DeleteSourceRequest（media_source_id）
        :param context: gRPC 服务上下文
        :return: OperationReply
        """
        if request.media_source_id <= 0:
            return _error_reply("media_source_id 必须大于 0")

        try:
            delete_media_source(int(request.media_source_id))
            return _success_reply(message="媒体源已删除")
        except MediaError as media_err:
            return _error_reply(str(media_err))
