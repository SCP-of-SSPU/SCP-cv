#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
媒体源查询与 API 序列化服务。
集中输出前端、REST API 与 gRPC 共享的媒体源字典字段。
@Project : SCP-cv
@File : media_queries.py
@Author : Qintsg
@Date : 2026-05-09
'''
from __future__ import annotations

from typing import Optional

from scp_cv.apps.playback.models import MediaSource
from scp_cv.services.media_previews import source_preview_payload


def list_media_sources(
    source_type: Optional[str] = None,
    folder_id: Optional[int] = None,
) -> list[dict[str, object]]:
    """
    查询所有媒体源列表。
    :param source_type: 可选过滤源类型
    :param folder_id: 可选过滤文件夹 ID（-1 表示根目录）
    :return: 媒体源字典列表
    """
    queryset = MediaSource.objects.prefetch_related("ppt_resources").all()
    if source_type:
        queryset = queryset.filter(source_type=source_type)
    if folder_id is not None:
        if folder_id < 0:
            queryset = queryset.filter(folder__isnull=True)
        else:
            queryset = queryset.filter(folder_id=folder_id)
    return [media_source_payload(source) for source in queryset]


def media_source_payload(source: MediaSource) -> dict[str, object]:
    """
    将 MediaSource 实例序列化为前端/API 共用字段。
    :param source: 媒体源模型实例
    :return: 含基础信息、网页预热兼容字段和预览字段的字典
    """
    keep_alive = bool(getattr(source, "keep_alive", True))
    payload: dict[str, object] = {
        "id": source.pk,
        "source_type": source.source_type,
        "name": source.name,
        "uri": source.uri,
        "is_available": source.is_available,
        "stream_identifier": source.stream_identifier,
        "folder_id": source.folder_id,
        "original_filename": source.original_filename,
        "file_size": source.file_size,
        "mime_type": source.mime_type,
        "is_temporary": source.is_temporary,
        "expires_at": source.expires_at.isoformat() if source.expires_at else None,
        "metadata": source.metadata,
        "keep_alive": keep_alive,
        "preheat_enabled": keep_alive,
        "created_at": source.created_at.isoformat() if source.created_at else "",
    }
    payload.update(source_preview_payload(source))
    return payload
