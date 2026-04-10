#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
播放会话管理服务，负责统一播放区域的状态维护与内容切换。
@Project : SCP-cv
@File : playback.py
@Author : Qintsg
@Date : 2026-04-10
'''
from __future__ import annotations

import logging

from scp_cv.apps.playback.models import (
    PlaybackContentKind,
    PlaybackMode,
    PlaybackSession,
    PlaybackState,
)
from scp_cv.apps.streams.models import StreamSource
from scp_cv.services.display import (
    DisplayTarget,
    SplicedDisplayTarget,
    build_left_right_splice_target,
    list_display_targets,
)

logger = logging.getLogger(__name__)


class PlaybackError(Exception):
    """播放会话操作过程中的业务异常。"""


def get_or_create_session() -> PlaybackSession:
    """
    获取当前唯一的播放会话，若不存在则创建。
    系统只维护一个 PlaybackSession 实例。
    :return: 当前播放会话实例
    """
    session = PlaybackSession.objects.first()
    if session is None:
        session = PlaybackSession.objects.create()
        logger.info("创建新的播放会话 id=%d", session.pk)
    return session


def get_session_snapshot() -> dict[str, object]:
    """
    获取当前播放会话的完整状态快照，用于页面渲染和 SSE 推送。
    :return: 包含会话所有状态字段的字典
    """
    session = get_or_create_session()

    # 关联流信息
    stream_name = "无"
    if session.stream_source is not None:
        stream_name = session.stream_source.name

    return {
        "session_id": session.pk,
        "content_kind": session.content_kind,
        "content_kind_label": session.get_content_kind_display(),
        "stream_name": stream_name,
        "playback_state": session.playback_state,
        "playback_state_label": session.get_playback_state_display(),
        "display_mode": session.display_mode,
        "display_mode_label": session.get_display_mode_display(),
        "target_display_label": session.target_display_label or "未选择",
        "spliced_display_label": session.spliced_display_label or "无",
        "is_spliced": session.is_spliced,
        "last_updated_at": session.last_updated_at.isoformat() if session.last_updated_at else "",
    }


def open_stream_source(stream_id: int) -> PlaybackSession:
    """
    打开指定 SRT 流到播放区域。
    :param stream_id: StreamSource 主键
    :return: 更新后的播放会话
    """
    try:
        stream = StreamSource.objects.get(pk=stream_id)
    except StreamSource.DoesNotExist as not_found:
        raise PlaybackError(f"流 id={stream_id} 不存在") from not_found

    session = get_or_create_session()
    _stop_current_content(session)

    session.content_kind = PlaybackContentKind.STREAM
    session.stream_source = stream
    session.playback_state = PlaybackState.PLAYING
    session.save()

    logger.info("打开 SRT 流「%s」（%s）", stream.name, stream.stream_identifier)
    return session


def stop_current_content() -> PlaybackSession:
    """
    停止当前播放的内容并重置会话状态。
    :return: 更新后的播放会话
    """
    session = get_or_create_session()
    _stop_current_content(session)
    session.save()
    logger.info("停止当前播放内容")
    return session


def _stop_current_content(session: PlaybackSession) -> None:
    """
    内部方法：重置会话字段。
    :param session: 播放会话实例（调用方负责 save）
    """
    session.content_kind = PlaybackContentKind.NONE
    session.stream_source = None
    session.playback_state = PlaybackState.IDLE


def select_display_target(
    display_mode: str,
    target_display_name: str = "",
) -> PlaybackSession:
    """
    选择显示目标：单屏或左右拼接模式。
    :param display_mode: 'single' 或 'left_right_splice'
    :param target_display_name: 目标显示器名称（单屏模式下必填）
    :return: 更新后的播放会话
    """
    session = get_or_create_session()

    display_targets = list_display_targets()

    if display_mode == PlaybackMode.SINGLE:
        # 单屏模式：验证目标显示器存在
        if target_display_name:
            matched_display = next(
                (dt for dt in display_targets if dt.name == target_display_name),
                None,
            )
            if matched_display is None:
                raise PlaybackError(f"显示器「{target_display_name}」不存在")
            session.target_display_label = matched_display.name
        elif display_targets:
            # 默认选择主显示器
            primary_display = next((dt for dt in display_targets if dt.is_primary), display_targets[0])
            session.target_display_label = primary_display.name

        session.display_mode = PlaybackMode.SINGLE
        session.is_spliced = False
        session.spliced_display_label = ""

    elif display_mode == PlaybackMode.LEFT_RIGHT_SPLICE:
        # 拼接模式：至少需要两台显示器
        splice_target = build_left_right_splice_target(display_targets)
        if splice_target is None:
            raise PlaybackError("检测到的显示器不足两台，无法进行左右拼接")

        session.display_mode = PlaybackMode.LEFT_RIGHT_SPLICE
        session.is_spliced = True
        session.target_display_label = splice_target.left.name
        session.spliced_display_label = f"{splice_target.left.name} + {splice_target.right.name}"

    else:
        raise PlaybackError(f"未知的显示模式：{display_mode}")

    session.save()
    logger.info("显示目标切换为 %s（%s）", session.get_display_mode_display(), session.target_display_label)
    return session
