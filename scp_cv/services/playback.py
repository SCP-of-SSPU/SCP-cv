#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
播放会话管理服务，负责多窗口播放区域的状态维护与内容切换。
适配器架构下，所有源类型通过 MediaSource 统一管理，
播放指令通过 pending_command 字段下发给播放器进程。
每个输出窗口（window_id 1-4）维护独立的 PlaybackSession。
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
)
from scp_cv.services.display import (
    build_left_right_splice_target,
    list_display_targets,
)

logger = logging.getLogger(__name__)

# 有效的窗口编号范围（1-4 对应四个输出显示器）
VALID_WINDOW_IDS = frozenset({1, 2, 3, 4})


class PlaybackError(Exception):
    """播放会话操作过程中的业务异常。"""


def _validate_window_id(window_id: int) -> None:
    """
    校验窗口编号合法性。
    :param window_id: 窗口编号
    :raises PlaybackError: 窗口编号不在 1-4 范围时
    """
    if window_id not in VALID_WINDOW_IDS:
        raise PlaybackError(f"无效的窗口编号：{window_id}，有效范围 1-4")


def get_or_create_session(window_id: int) -> PlaybackSession:
    """
    获取指定窗口的播放会话，若不存在则创建。
    :param window_id: 窗口编号（1-4）
    :return: 对应窗口的播放会话实例
    """
    _validate_window_id(window_id)
    session, created = PlaybackSession.objects.get_or_create(
        window_id=window_id,
        defaults={"playback_state": PlaybackState.IDLE},
    )
    if created:
        logger.info("创建窗口 %d 的播放会话 id=%d", window_id, session.pk)
    return session


def get_all_sessions() -> list[PlaybackSession]:
    """
    获取所有窗口的播放会话列表（按 window_id 排序）。
    :return: 播放会话列表
    """
    return list(PlaybackSession.objects.order_by("window_id"))


def get_session_snapshot(window_id: int) -> dict[str, object]:
    """
    获取指定窗口播放会话的完整状态快照，用于页面渲染和 SSE 推送。
    :param window_id: 窗口编号（1-4）
    :return: 包含会话所有状态字段的字典
    """
    session = get_or_create_session(window_id)

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
        "window_id": session.window_id,
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
        # 循环播放
        "loop_enabled": session.loop_enabled,
    }


def get_all_sessions_snapshot() -> list[dict[str, object]]:
    """
    获取所有窗口（1-4）的状态快照列表。
    :return: 四个窗口的会话快照列表
    """
    return [get_session_snapshot(wid) for wid in sorted(VALID_WINDOW_IDS)]


def open_source(window_id: int, media_source_id: int, autoplay: bool = True) -> PlaybackSession:
    """
    打开指定媒体源到指定窗口。
    :param window_id: 目标窗口编号（1-4）
    :param media_source_id: MediaSource 主键
    :param autoplay: 是否自动开始播放
    :return: 更新后的播放会话
    :raises PlaybackError: 源不存在时
    """
    try:
        source = MediaSource.objects.get(pk=media_source_id)
    except MediaSource.DoesNotExist as not_found:
        raise PlaybackError(f"媒体源 id={media_source_id} 不存在") from not_found

    session = get_or_create_session(window_id)
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
    sync_splice_command(window_id, session)

    logger.info("窗口 %d 打开媒体源「%s」（%s: %s）", window_id, source.name, source.source_type, source.uri)
    return session


def control_playback(window_id: int, action: str) -> PlaybackSession:
    """
    发送播放控制指令（play / pause / stop）到指定窗口。
    :param window_id: 窗口编号（1-4）
    :param action: 控制动作，对应 PlaybackCommand 值
    :return: 更新后的播放会话
    :raises PlaybackError: 无效动作时
    """
    valid_actions = {PlaybackCommand.PLAY, PlaybackCommand.PAUSE, PlaybackCommand.STOP}
    if action not in valid_actions:
        raise PlaybackError(f"无效的播放控制动作：{action}")

    session = get_or_create_session(window_id)
    if session.media_source is None:
        raise PlaybackError(f"窗口 {window_id} 当前没有打开的媒体源")

    session.pending_command = action
    session.command_args = {}
    session.save()
    sync_splice_command(window_id, session)

    logger.info("窗口 %d 发送播放控制指令：%s", window_id, action)
    return session


def navigate_content(
    window_id: int,
    action: str,
    target_index: int = 0,
    position_ms: int = 0,
) -> PlaybackSession:
    """
    发送内容导航指令（翻页 / 跳转位置）到指定窗口。
    :param window_id: 窗口编号（1-4）
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

    session = get_or_create_session(window_id)
    if session.media_source is None:
        raise PlaybackError(f"窗口 {window_id} 当前没有打开的媒体源")

    session.pending_command = action
    command_args: dict[str, int] = {}
    if action == PlaybackCommand.GOTO:
        command_args["target_index"] = target_index
    elif action == PlaybackCommand.SEEK:
        command_args["position_ms"] = position_ms
    session.command_args = command_args
    session.save()
    sync_splice_command(window_id, session)

    logger.info("窗口 %d 发送导航指令：%s，参数=%s", window_id, action, command_args)
    return session


def close_source(window_id: int) -> PlaybackSession:
    """
    关闭指定窗口当前播放的内容并重置会话状态。
    :param window_id: 窗口编号（1-4）
    :return: 更新后的播放会话
    """
    session = get_or_create_session(window_id)

    # 先发送 close 指令让播放器执行清理
    if session.media_source is not None:
        session.pending_command = PlaybackCommand.CLOSE
        session.command_args = {}
        session.save()
        sync_splice_command(window_id, session)
        logger.info("窗口 %d 发送关闭指令", window_id)
    else:
        # 无源则直接重置
        _reset_playback_fields(session)
        session.save()
        logger.info("窗口 %d 无活跃源，直接重置会话", window_id)

    return session


def stop_current_content(window_id: int) -> PlaybackSession:
    """
    停止指定窗口当前播放（兼容旧接口，内部调用 close_source）。
    :param window_id: 窗口编号（1-4）
    :return: 更新后的播放会话
    """
    return close_source(window_id)


def clear_pending_command(window_id: int) -> PlaybackSession:
    """
    清除指定窗口已执行的指令（由播放器进程调用）。
    :param window_id: 窗口编号（1-4）
    :return: 更新后的播放会话
    """
    session = get_or_create_session(window_id)
    session.pending_command = PlaybackCommand.NONE
    session.command_args = {}
    session.save()
    return session


def update_playback_progress(
    window_id: int,
    playback_state: Optional[str] = None,
    current_slide: Optional[int] = None,
    total_slides: Optional[int] = None,
    position_ms: Optional[int] = None,
    duration_ms: Optional[int] = None,
) -> PlaybackSession:
    """
    播放器进程上报指定窗口的播放进度（通过 DB 写入）。
    :param window_id: 窗口编号（1-4）
    :param playback_state: 播放状态
    :param current_slide: 当前页码（PPT）
    :param total_slides: 总页数（PPT）
    :param position_ms: 当前位置毫秒（视频）
    :param duration_ms: 总时长毫秒（视频）
    :return: 更新后的播放会话
    """
    session = get_or_create_session(window_id)
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
    window_id: int,
    display_mode: str,
    target_display_name: str = "",
) -> PlaybackSession:
    """
    为指定窗口选择显示目标：单屏或左右拼接模式。
    :param window_id: 窗口编号（1-4）
    :param display_mode: 'single' 或 'left_right_splice'
    :param target_display_name: 目标显示器名称（单屏模式下必填）
    :return: 更新后的播放会话
    :raises PlaybackError: 显示器不存在或不足时
    """
    session = get_or_create_session(window_id)
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
    logger.info(
        "窗口 %d 显示目标切换为 %s（%s）",
        window_id, session.get_display_mode_display(), session.target_display_label,
    )
    return session


def set_splice_mode(enabled: bool) -> tuple[PlaybackSession, PlaybackSession]:
    """
    设置窗口1和窗口2的拼接模式。
    启用拼接时，两个窗口播放同一源的左右半画面，控制指令自动同步。
    :param enabled: 是否启用拼接模式
    :return: 窗口1和窗口2的会话元组
    """
    session_1 = get_or_create_session(1)
    session_2 = get_or_create_session(2)

    if enabled:
        session_1.display_mode = PlaybackMode.LEFT_RIGHT_SPLICE
        session_1.is_spliced = True
        session_2.display_mode = PlaybackMode.LEFT_RIGHT_SPLICE
        session_2.is_spliced = True
        logger.info("窗口 1+2 拼接模式已启用")
    else:
        session_1.display_mode = PlaybackMode.SINGLE
        session_1.is_spliced = False
        session_1.spliced_display_label = ""
        session_2.display_mode = PlaybackMode.SINGLE
        session_2.is_spliced = False
        session_2.spliced_display_label = ""
        logger.info("窗口 1+2 拼接模式已关闭")

    session_1.save()
    session_2.save()
    return session_1, session_2


def is_splice_mode_active() -> bool:
    """
    检查窗口1和2是否处于拼接模式。
    :return: 拼接模式是否激活
    """
    session_1 = get_or_create_session(1)
    return session_1.is_spliced


def sync_splice_command(source_window_id: int, target_session: PlaybackSession) -> None:
    """
    拼接模式下，将源窗口的指令同步到另一个窗口。
    当窗口1或2在拼接模式下收到指令时，自动同步到另一方。
    :param source_window_id: 发出指令的窗口编号（1 或 2）
    :param target_session: 作为同步目标的会话实例
    """
    if source_window_id not in {1, 2}:
        return

    peer_window_id = 2 if source_window_id == 1 else 1
    peer_session = get_or_create_session(peer_window_id)

    # 仅当双方都处于拼接模式时才同步
    if not (target_session.is_spliced and peer_session.is_spliced):
        return

    peer_session.pending_command = target_session.pending_command
    peer_session.command_args = target_session.command_args
    # 如果源窗口绑定了新媒体源，peer 也同步绑定
    if target_session.media_source is not None:
        peer_session.media_source = target_session.media_source
    peer_session.save()
    logger.info(
        "拼接同步：窗口 %d → 窗口 %d，指令=%s",
        source_window_id, peer_window_id, target_session.pending_command,
    )


def toggle_loop_playback(window_id: int, enabled: bool) -> PlaybackSession:
    """
    切换指定窗口的循环播放状态，同时下发 SET_LOOP 指令给播放器进程。
    :param window_id: 窗口编号（1-4）
    :param enabled: 是否启用循环播放
    :return: 更新后的播放会话
    :raises PlaybackError: 无活跃源时
    """
    session = get_or_create_session(window_id)
    if session.media_source is None:
        raise PlaybackError(f"窗口 {window_id} 当前没有打开的媒体源")

    session.loop_enabled = enabled
    session.pending_command = PlaybackCommand.SET_LOOP
    session.command_args = {"enabled": enabled}
    session.save()
    sync_splice_command(window_id, session)

    logger.info("窗口 %d 循环播放已%s", window_id, "开启" if enabled else "关闭")
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
    session.loop_enabled = False
    session.pending_command = PlaybackCommand.NONE
    session.command_args = {}
