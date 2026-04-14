#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
播放会话管理服务，负责统一播放区域的状态维护与内容切换。
适配器架构下，所有源类型通过 MediaSource 统一管理，
播放指令通过 pending_command 字段下发给播放器进程。
@Project : SCP-cv
@File : playback.py
@Author : Qintsg
@Date : 2026-04-14
'''
from __future__ import annotations

import logging
from typing import Optional

from scp_cv.apps.playback.models import (
    MediaSource,
    PlaybackCommand,
    PlaybackMode,
    PlaybackSession,
    PlaybackState,
    SourceType,
)
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

    # 关联源信息
    source_name = "无"
    source_type = ""
    source_type_label = "无"
    source_uri = ""
    if session.media_source is not None:
        source_name = session.media_source.name
        source_type = session.media_source.source_type
        source_type_label = session.media_source.get_source_type_display()
        source_uri = session.media_source.uri

    return {
        "session_id": session.pk,
        "source_name": source_name,
        "source_type": source_type,
        "source_type_label": source_type_label,
        "source_uri": source_uri,
        "playback_state": session.playback_state,
        "playback_state_label": session.get_playback_state_display(),
        "display_mode": session.display_mode,
        "display_mode_label": session.get_display_mode_display(),
        "target_display_label": session.target_display_label or "未选择",
        "spliced_display_label": session.spliced_display_label or "无",
        "is_spliced": session.is_spliced,
        # PPT 状态
        "current_slide": session.current_slide,
        "total_slides": session.total_slides,
        # 时间线状态
        "position_ms": session.position_ms,
        "duration_ms": session.duration_ms,
        # 指令
        "pending_command": session.pending_command,
        "last_updated_at": session.last_updated_at.isoformat() if session.last_updated_at else "",
    }


def open_source(media_source_id: int, autoplay: bool = True) -> PlaybackSession:
    """
    打开指定媒体源到播放区域。
    :param media_source_id: MediaSource 主键
    :param autoplay: 是否自动开始播放
    :return: 更新后的播放会话
    :raises PlaybackError: 源不存在时
    """
    try:
        source = MediaSource.objects.get(pk=media_source_id)
    except MediaSource.DoesNotExist as not_found:
        raise PlaybackError(f"媒体源 id={media_source_id} 不存在") from not_found

    session = get_or_create_session()
    # 先关闭当前内容
    _reset_playback_fields(session)

    session.media_source = source
    session.playback_state = PlaybackState.LOADING
    session.pending_command = PlaybackCommand.OPEN
    session.command_args = {
        "source_type": source.source_type,
        "uri": source.uri,
        "autoplay": autoplay,
    }
    session.save()

    logger.info("打开媒体源「%s」（%s: %s）", source.name, source.source_type, source.uri)
    return session


def control_playback(action: str) -> PlaybackSession:
    """
    发送播放控制指令（play / pause / stop）。
    :param action: 控制动作，对应 PlaybackCommand 值
    :return: 更新后的播放会话
    :raises PlaybackError: 无效动作时
    """
    valid_actions = {PlaybackCommand.PLAY, PlaybackCommand.PAUSE, PlaybackCommand.STOP}
    if action not in valid_actions:
        raise PlaybackError(f"无效的播放控制动作：{action}")

    session = get_or_create_session()
    if session.media_source is None:
        raise PlaybackError("当前没有打开的媒体源")

    session.pending_command = action
    session.command_args = {}
    session.save()

    logger.info("发送播放控制指令：%s", action)
    return session


def navigate_content(action: str, target_index: int = 0, position_ms: int = 0) -> PlaybackSession:
    """
    发送内容导航指令（翻页 / 跳转位置）。
    :param action: 导航动作（next / prev / goto / seek）
    :param target_index: 目标页码（goto 时使用，从 1 开始）
    :param position_ms: 目标位置毫秒（seek 时使用）
    :return: 更新后的播放会话
    :raises PlaybackError: 无效动作或无源时
    """
    valid_actions = {PlaybackCommand.NEXT, PlaybackCommand.PREV,
                     PlaybackCommand.GOTO, PlaybackCommand.SEEK}
    if action not in valid_actions:
        raise PlaybackError(f"无效的导航动作：{action}")

    session = get_or_create_session()
    if session.media_source is None:
        raise PlaybackError("当前没有打开的媒体源")

    session.pending_command = action
    command_args: dict[str, int] = {}
    if action == PlaybackCommand.GOTO:
        command_args["target_index"] = target_index
    elif action == PlaybackCommand.SEEK:
        command_args["position_ms"] = position_ms
    session.command_args = command_args
    session.save()

    logger.info("发送导航指令：%s，参数=%s", action, command_args)
    return session


def close_source() -> PlaybackSession:
    """
    关闭当前播放的内容并重置会话状态。
    :return: 更新后的播放会话
    """
    session = get_or_create_session()

    # 先发送 close 指令让播放器执行清理
    if session.media_source is not None:
        session.pending_command = PlaybackCommand.CLOSE
        session.command_args = {}
        session.save()
        logger.info("发送关闭指令")
    else:
        # 无源则直接重置
        _reset_playback_fields(session)
        session.save()
        logger.info("无活跃源，直接重置会话")

    return session


def stop_current_content() -> PlaybackSession:
    """
    停止当前播放（兼容旧接口，内部调用 close_source）。
    :return: 更新后的播放会话
    """
    return close_source()


def clear_pending_command() -> PlaybackSession:
    """
    清除已执行的指令（由播放器进程调用）。
    :return: 更新后的播放会话
    """
    session = get_or_create_session()
    session.pending_command = PlaybackCommand.NONE
    session.command_args = {}
    session.save()
    return session


def update_playback_progress(
    playback_state: Optional[str] = None,
    current_slide: Optional[int] = None,
    total_slides: Optional[int] = None,
    position_ms: Optional[int] = None,
    duration_ms: Optional[int] = None,
) -> PlaybackSession:
    """
    播放器进程上报播放进度（通过 DB 写入）。
    :param playback_state: 播放状态
    :param current_slide: 当前页码（PPT）
    :param total_slides: 总页数（PPT）
    :param position_ms: 当前位置毫秒（视频）
    :param duration_ms: 总时长毫秒（视频）
    :return: 更新后的播放会话
    """
    session = get_or_create_session()
    if playback_state is not None:
        session.playback_state = playback_state
    if current_slide is not None:
        session.current_slide = current_slide
    if total_slides is not None:
        session.total_slides = total_slides
    if position_ms is not None:
        session.position_ms = position_ms
    if duration_ms is not None:
        session.duration_ms = duration_ms
    session.save()
    return session


def select_display_target(
    display_mode: str,
    target_display_name: str = "",
) -> PlaybackSession:
    """
    选择显示目标：单屏或左右拼接模式。
    :param display_mode: 'single' 或 'left_right_splice'
    :param target_display_name: 目标显示器名称（单屏模式下必填）
    :return: 更新后的播放会话
    :raises PlaybackError: 显示器不存在或不足时
    """
    session = get_or_create_session()
    display_targets = list_display_targets()

    if display_mode == PlaybackMode.SINGLE:
        if target_display_name:
            matched_display = next(
                (dt for dt in display_targets if dt.name == target_display_name),
                None,
            )
            if matched_display is None:
                raise PlaybackError(f"显示器「{target_display_name}」不存在")
            session.target_display_label = matched_display.name
        elif display_targets:
            primary_display = next(
                (dt for dt in display_targets if dt.is_primary), display_targets[0],
            )
            session.target_display_label = primary_display.name

        session.display_mode = PlaybackMode.SINGLE
        session.is_spliced = False
        session.spliced_display_label = ""

    elif display_mode == PlaybackMode.LEFT_RIGHT_SPLICE:
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


def _reset_playback_fields(session: PlaybackSession) -> None:
    """
    内部方法：重置会话的播放相关字段。
    :param session: 播放会话实例（调用方负责 save）
    """
    session.media_source = None
    session.playback_state = PlaybackState.IDLE
    session.current_slide = 0
    session.total_slides = 0
    session.position_ms = 0
    session.duration_ms = 0
    session.pending_command = PlaybackCommand.NONE
    session.command_args = {}
