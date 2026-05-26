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
    BigScreenMode,
    MediaSource,
    PlaybackCommand,
    PlaybackMode,
    PlaybackSession,
    PlaybackState,
    RuntimeState,
    SourceType,
)
from scp_cv.services.display import (
    build_left_right_splice_target,
    list_display_targets,
)
from scp_cv.services.playback_sessions import (
    VALID_WINDOW_IDS as VALID_WINDOW_IDS,
    PlaybackError as PlaybackError,
    get_all_sessions as get_all_sessions,
    get_all_sessions_snapshot as get_all_sessions_snapshot,
    get_or_create_session as get_or_create_session,
    get_session_snapshot as get_session_snapshot,
)
from scp_cv.services.playback_window_controls import (
    is_muted_by_runtime as _is_muted_by_runtime,
    runtime_muted_windows as _runtime_muted_windows,
    set_window_mute as set_window_mute,
    set_window_volume as set_window_volume,
    toggle_loop_playback as toggle_loop_playback,
)
from scp_cv.ppt_backend import DEFAULT_PPT_BACKEND, normalize_ppt_backend
from scp_cv.services.video_wall import VideoWallError, apply_big_screen_mode as apply_video_wall_mode

logger = logging.getLogger(__name__)

RESET_ALL_WINDOWS_ARG = "reset_all_windows"


def reset_all_sessions_to_idle() -> list[PlaybackSession]:
    """
    将所有播放窗口重置为待机状态，并请求播放器重建窗口。
    :return: 重置后的会话列表
    """
    reset_sessions: list[PlaybackSession] = []
    for window_id in sorted(VALID_WINDOW_IDS):
        session = get_or_create_session(window_id)
        _reset_playback_fields(session)
        session.save()
        reset_sessions.append(session)
    apply_runtime_audio_policy()
    _request_player_windows_rebuild()
    logger.info("已将所有窗口重置为待机状态，并请求播放器重建窗口")
    return reset_sessions


def request_all_windows_close() -> list[PlaybackSession]:
    """
    向所有窗口下发关闭指令，并同步将会话状态重置为待机。
    :return: 更新后的会话列表
    """
    reset_sessions: list[PlaybackSession] = []
    for window_id in sorted(VALID_WINDOW_IDS):
        session = get_or_create_session(window_id)
        cleanup_args = {
            "cleanup_source_id": session.media_source_id,
        } if session.media_source is not None and session.media_source.is_temporary else {}
        _reset_playback_fields(session)
        session.pending_command = PlaybackCommand.CLOSE
        session.command_args = cleanup_args
        session.save()
        reset_sessions.append(session)
    apply_runtime_audio_policy()
    logger.info("已向所有窗口下发关闭指令并重置待机状态")
    return reset_sessions


def get_runtime_snapshot() -> dict[str, object]:
    """
    获取全局运行状态快照。
    :return: 大屏模式、系统音量和固定静音策略
    """
    runtime = RuntimeState.get_instance()
    return {
        "big_screen_mode": runtime.big_screen_mode,
        "volume_level": runtime.volume_level,
        "muted_windows": _runtime_muted_windows(runtime.big_screen_mode),
    }


def set_big_screen_mode(big_screen_mode: str) -> dict[str, object]:
    """
    设置大屏模式，并同步窗口静音策略。
    :param big_screen_mode: single 或 double
    :return: 更新后的运行状态快照
    :raises PlaybackError: 模式无效时
    """
    if big_screen_mode not in {BigScreenMode.SINGLE, BigScreenMode.DOUBLE}:
        raise PlaybackError(f"无效的大屏模式：{big_screen_mode}")

    runtime = RuntimeState.get_instance()
    previous_mode = runtime.big_screen_mode
    runtime.big_screen_mode = big_screen_mode
    try:
        apply_video_wall_mode(big_screen_mode)
    except VideoWallError as video_wall_error:
        runtime.big_screen_mode = previous_mode
        raise PlaybackError(str(video_wall_error)) from video_wall_error
    runtime.save(update_fields=["big_screen_mode", "updated_at"])
    apply_runtime_audio_policy()
    logger.info("大屏模式切换为 %s", big_screen_mode)
    return get_runtime_snapshot()


def apply_runtime_audio_policy() -> None:
    """
    根据大屏模式应用固定静音策略。
    约束：窗口 3/4 始终静音；single 下窗口 2 静音；double 下窗口 1/2 不静音。
    """
    runtime = RuntimeState.get_instance()
    muted_windows = set(_runtime_muted_windows(runtime.big_screen_mode))
    for window_id in sorted(VALID_WINDOW_IDS):
        session = get_or_create_session(window_id)
        muted = window_id in muted_windows
        session.is_muted = muted
        session.pending_command = PlaybackCommand.SET_MUTE
        session.command_args = {"muted": muted}
        session.save(update_fields=["is_muted", "pending_command", "command_args"])


def open_source(
    window_id: int,
    media_source_id: int,
    autoplay: bool = True,
    ppt_backend: Optional[str] = None,
    target_slide: int = 0,
) -> PlaybackSession:
    """
    打开指定媒体源到指定窗口。
    :param window_id: 目标窗口编号（1-4）
    :param media_source_id: MediaSource 主键
    :param autoplay: 是否自动开始播放
    :param ppt_backend: PPT 源本次打开使用的播放器；空值时使用媒体源默认播放器
    :param target_slide: PPT 打开后自动跳转的页码（从 1 开始）
    :return: 更新后的播放会话
    :raises PlaybackError: 源不存在时
    """
    try:
        source = MediaSource.objects.get(pk=media_source_id)
    except MediaSource.DoesNotExist as not_found:
        raise PlaybackError(f"媒体源 id={media_source_id} 不存在") from not_found

    session = get_or_create_session(window_id)
    previous_source_id = session.media_source_id
    previous_source_is_temporary = bool(
        session.media_source
        and session.media_source.is_temporary
        and previous_source_id != source.pk
    )
    resolved_ppt_backend = _resolve_ppt_backend(source, ppt_backend)
    # 先关闭当前内容
    _reset_playback_fields(session)

    session.media_source = source
    session.playback_state = PlaybackState.LOADING
    session.is_muted = _is_muted_by_runtime(window_id)
    session.ppt_backend = resolved_ppt_backend
    session.pending_command = PlaybackCommand.OPEN
    session.command_args = {
        "source_id": source.pk,
        "source_type": source.source_type,
        "uri": source.uri,
        "autoplay": autoplay,
        "volume": session.volume,
        "muted": session.is_muted,
        "preheat_enabled": bool(getattr(source, "keep_alive", True)),
    }
    if source.source_type == SourceType.PPT:
        session.command_args["ppt_backend"] = resolved_ppt_backend
        if target_slide > 0:
            session.command_args["target_slide"] = int(target_slide)
    if previous_source_is_temporary:
        session.command_args["cleanup_source_id"] = previous_source_id
    session.save()
    logger.info(
        "窗口 %d 打开媒体源「%s」（%s: %s，ppt_backend=%s）",
        window_id, source.name, source.source_type, source.uri, resolved_ppt_backend,
    )
    return session


def switch_ppt_backend(window_id: int, ppt_backend: str) -> PlaybackSession:
    """
    临时切换当前窗口 PPT 放映播放器，并保持原源与页码重启。
    :param window_id: 窗口编号（1-4）
    :param ppt_backend: 目标 PPT 播放器后端
    :return: 更新后的播放会话
    :raises PlaybackError: 当前窗口未打开 PPT 或后端无效时
    """
    session = get_or_create_session(window_id)
    if session.media_source is None:
        raise PlaybackError(f"窗口 {window_id} 当前没有打开的媒体源")
    if session.media_source.source_type != SourceType.PPT:
        raise PlaybackError("当前窗口未打开 PPT 源")
    try:
        normalized_backend = normalize_ppt_backend(ppt_backend)
    except ValueError as backend_error:
        raise PlaybackError(str(backend_error)) from backend_error
    target_slide = max(1, int(session.current_slide or 1))
    previous_volume = session.volume
    previous_muted = session.is_muted
    logger.info(
        "窗口 %d 临时切换 PPT 播放器为 %s，并回到第 %d 页",
        window_id, normalized_backend, target_slide,
    )
    switched_session = open_source(
        window_id,
        int(session.media_source_id),
        autoplay=True,
        ppt_backend=normalized_backend,
        target_slide=target_slide,
    )
    switched_session.volume = previous_volume
    switched_session.is_muted = previous_muted
    switched_session.command_args["volume"] = previous_volume
    switched_session.command_args["muted"] = previous_muted
    switched_session.save(update_fields=["volume", "is_muted", "command_args", "last_updated_at"])
    return switched_session


def reset_ppt_playback() -> list[PlaybackSession]:
    """
    重置所有 PPT 放映后端进程，并让当前 PPT 窗口回到重置前页码。
    :return: 更新后的会话列表
    """
    restart_sessions: list[dict[str, object]] = []
    updated_sessions: list[PlaybackSession] = []
    for window_id in sorted(VALID_WINDOW_IDS):
        session = get_or_create_session(window_id)
        if session.media_source is None or session.media_source.source_type != SourceType.PPT:
            continue
        restart_args = _ppt_restart_args(session)
        restart_sessions.append(restart_args)
        session.playback_state = PlaybackState.LOADING
        session.error_message = ""
        session.pending_command = PlaybackCommand.NONE
        session.command_args = {}
        session.save(update_fields=[
            "playback_state",
            "error_message",
            "pending_command",
            "command_args",
            "last_updated_at",
        ])
        updated_sessions.append(session)

    coordinator_window_id = min(VALID_WINDOW_IDS)
    coordinator = get_or_create_session(coordinator_window_id)
    coordinator.pending_command = PlaybackCommand.RESET_PPT
    coordinator.command_args = {"restart_sessions": restart_sessions}
    coordinator.save(update_fields=["pending_command", "command_args", "last_updated_at"])
    if coordinator not in updated_sessions:
        updated_sessions.append(coordinator)
    logger.info("已请求重置 PPT 放映，待重启窗口数=%d", len(restart_sessions))
    return updated_sessions


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
    if _navigation_is_noop(session, action, target_index):
        return session

    session.pending_command = action
    command_args: dict[str, int] = {}
    if action == PlaybackCommand.GOTO:
        command_args["target_index"] = target_index
    elif action == PlaybackCommand.SEEK:
        command_args["position_ms"] = position_ms
    session.command_args = command_args
    session.save()
    logger.info("窗口 %d 发送导航指令：%s，参数=%s", window_id, action, command_args)
    return session


def control_ppt_media(
    window_id: int,
    media_action: str,
    media_id: str = "",
    media_index: int = 0,
) -> PlaybackSession:
    """
    控制 PPT 当前页中的单个媒体对象。
    :param window_id: 窗口编号（1-4）
    :param media_action: 媒体控制动作（play / pause / stop）
    :param media_id: 前端媒体对象标识
    :param media_index: 当前页媒体序号（从 1 开始）
    :return: 更新后的播放会话
    :raises PlaybackError: 无 PPT 源或动作无效时
    """
    valid_actions = {PlaybackCommand.PLAY, PlaybackCommand.PAUSE, PlaybackCommand.STOP}
    if media_action not in valid_actions:
        raise PlaybackError(f"无效的 PPT 媒体控制动作：{media_action}")
    session = get_or_create_session(window_id)
    if session.media_source is None:
        raise PlaybackError(f"窗口 {window_id} 当前没有打开的媒体源")
    if session.media_source.source_type != SourceType.PPT:
        raise PlaybackError("当前窗口未打开 PPT 源")

    session.pending_command = PlaybackCommand.PPT_MEDIA
    session.command_args = {
        "media_action": media_action,
        "media_id": media_id,
        "media_index": max(0, int(media_index)),
    }
    session.save()
    logger.info("窗口 %d 发送 PPT 媒体控制：%s，参数=%s", window_id, media_action, session.command_args)
    return session


def _resolve_ppt_backend(source: MediaSource, raw_backend: Optional[str]) -> str:
    """
    解析 PPT 源本次放映使用的播放器后端。
    :param source: 媒体源
    :param raw_backend: 本次请求覆盖值
    :return: PPT 后端枚举值
    :raises PlaybackError: 后端值无效时
    """
    if source.source_type != SourceType.PPT:
        return DEFAULT_PPT_BACKEND
    try:
        return normalize_ppt_backend(raw_backend or getattr(source, "ppt_backend", DEFAULT_PPT_BACKEND))
    except ValueError as backend_error:
        raise PlaybackError(str(backend_error)) from backend_error


def _ppt_restart_args(session: PlaybackSession) -> dict[str, object]:
    """
    为 PPT 重启构造播放器 OPEN 指令参数。
    :param session: 当前 PPT 播放会话
    :return: 可直接交给播放器 _handle_open 的参数字典
    """
    source = session.media_source
    if source is None:
        return {}
    return {
        "window_id": session.window_id,
        "source_id": source.pk,
        "source_type": source.source_type,
        "uri": source.uri,
        "autoplay": True,
        "volume": session.volume,
        "muted": session.is_muted,
        "preheat_enabled": bool(getattr(source, "keep_alive", True)),
        "ppt_backend": _resolve_ppt_backend(source, session.ppt_backend),
        "target_slide": max(1, int(session.current_slide or 1)),
    }


def _navigation_is_noop(session: PlaybackSession, action: str, target_index: int) -> bool:
    """
    校验导航动作，并判断是否应保持当前页不下发指令。
    :param session: 当前播放会话
    :param action: 导航动作
    :param target_index: 目标页码
    :return: True 表示当前操作为边界保持
    """
    source_type = session.media_source.source_type if session.media_source else ""
    if source_type == SourceType.PPT:
        if action == PlaybackCommand.SEEK:
            raise PlaybackError("PPT 源不支持 seek 操作")
        if action == PlaybackCommand.GOTO:
            if target_index < 1:
                raise PlaybackError("PPT 跳页页码必须大于 0")
            if session.total_slides > 0 and target_index > session.total_slides:
                raise PlaybackError(f"PPT 跳页页码超出范围：{target_index}/{session.total_slides}")
    elif action in {PlaybackCommand.NEXT, PlaybackCommand.PREV, PlaybackCommand.GOTO}:
        raise PlaybackError("当前源不是翻页型内容")
    return False


def close_source(window_id: int) -> PlaybackSession:
    """
    关闭指定窗口当前播放的内容并重置会话状态。
    :param window_id: 窗口编号（1-4）
    :return: 更新后的播放会话

    实现要点：
      - 同步把 playback_state 重置为 IDLE 并清空帧/进度字段，避免 UI 因为旧 error/playing 状态
        持续展示「直播流尚未就绪」「播放器异常」等提示，让"关闭显示"在前端立即可感知；
      - 仍然保留 media_source 与 CLOSE 指令，等待 player 端 _handle_close 真正释放 adapter
        与黑屏渲染；player 完成后会再次写入 IDLE，与本次重置幂等。
    """
    session = get_or_create_session(window_id)

    # 先发送 close 指令让播放器执行清理
    if session.media_source is not None:
        cleanup_args = {
            "cleanup_source_id": session.media_source_id,
        } if session.media_source.is_temporary else {}
        session.pending_command = PlaybackCommand.CLOSE
        session.command_args = cleanup_args
        # 同步立即重置可视字段，让前端 SSE 这一帧就拿到 IDLE，不再卡在过期 error。
        session.playback_state = PlaybackState.IDLE
        session.error_message = ""
        session.current_slide = 0
        session.total_slides = 0
        session.ppt_backend = DEFAULT_PPT_BACKEND
        session.position_ms = 0
        session.duration_ms = 0
        session.save()
        logger.info("窗口 %d 发送关闭指令并立即重置 UI 状态", window_id)
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
    error_message: Optional[str] = None,
    current_slide: Optional[int] = None,
    total_slides: Optional[int] = None,
    position_ms: Optional[int] = None,
    duration_ms: Optional[int] = None,
) -> PlaybackSession:
    """
    播放器进程上报指定窗口的播放进度（通过 DB 写入）。
    :param window_id: 窗口编号（1-4）
    :param playback_state: 播放状态
    :param error_message: 播放器适配器返回的具体错误说明
    :param current_slide: 当前页码（PPT）
    :param total_slides: 总页数（PPT）
    :param position_ms: 当前位置毫秒（视频）
    :param duration_ms: 总时长毫秒（视频）
    :return: 更新后的播放会话
    """
    session = get_or_create_session(window_id)
    if playback_state is not None:
        session.playback_state = playback_state
        if playback_state == PlaybackState.ERROR:
            session.error_message = error_message or ""
        else:
            session.error_message = ""
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


def _request_player_windows_rebuild() -> None:
    """
    请求播放器进程在主线程关闭并重建全部窗口。
    :return: None
    """
    coordinator_window_id = min(VALID_WINDOW_IDS)
    session = get_or_create_session(coordinator_window_id)
    session.pending_command = PlaybackCommand.CLOSE
    session.command_args = {RESET_ALL_WINDOWS_ARG: True}
    session.save(update_fields=["pending_command", "command_args", "last_updated_at"])


def _reset_playback_fields(session: PlaybackSession) -> None:
    """
    内部方法：重置会话的播放相关字段。
    :param session: 播放会话实例（调用方负责 save）
    """
    session.media_source = None
    session.playback_state = PlaybackState.IDLE
    session.error_message = ""
    session.current_slide = 0
    session.total_slides = 0
    session.ppt_backend = DEFAULT_PPT_BACKEND
    session.position_ms = 0
    session.duration_ms = 0
    session.loop_enabled = False
    session.volume = 100
    session.is_muted = False
    session.pending_command = PlaybackCommand.NONE
    session.command_args = {}
