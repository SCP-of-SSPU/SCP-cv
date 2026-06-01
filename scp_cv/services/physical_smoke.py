#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
本机物理播放冒烟测试服务，真实下发四屏播放、关闭与重置指令。
@Project : SCP-cv
@File : physical_smoke.py
@Author : Qintsg
@Date : 2026-05-30
'''
from __future__ import annotations

import time
from collections.abc import Mapping, Sequence
from math import isfinite

from django.utils import timezone

from scp_cv.apps.playback.models import (
    BackgroundAudioCommand,
    BackgroundAudioState,
    MediaSource,
    PlaybackCommand,
    PlaybackSession,
    PlaybackState,
    SourceType,
)
from scp_cv.ppt_backend import DEFAULT_PPT_BACKEND
from scp_cv.services.background_audio import play_source as play_background_audio_source
from scp_cv.services.background_audio import stop_background_audio
from scp_cv.services.playback import (
    VALID_WINDOW_IDS,
    close_source,
    get_all_sessions_snapshot,
    get_or_create_session,
    open_source,
    reset_all_sessions_to_idle,
)

WINDOW_SOURCE_TYPE_SEQUENCE: tuple[str, ...] = (
    SourceType.IMAGE,
    SourceType.VIDEO,
    SourceType.WEB,
    SourceType.PPT,
    SourceType.SRT_STREAM,
    SourceType.CUSTOM_STREAM,
    SourceType.RTSP_STREAM,
)
SOURCE_TYPE_SEQUENCE: tuple[str, ...] = (
    SourceType.IMAGE,
    SourceType.VIDEO,
    SourceType.AUDIO,
    SourceType.WEB,
    SourceType.PPT,
    SourceType.SRT_STREAM,
    SourceType.CUSTOM_STREAM,
    SourceType.RTSP_STREAM,
)
STREAM_SOURCE_TYPES = {SourceType.SRT_STREAM, SourceType.CUSTOM_STREAM, SourceType.RTSP_STREAM}
DEFAULT_SETTLE_SECONDS = 2.0
DEFAULT_TIMEOUT_SECONDS = 30.0
DEFAULT_PPT_TIMEOUT_SECONDS = 120.0
DEFAULT_STREAM_TIMEOUT_SECONDS = 45.0
DEFAULT_RESET_TIMEOUT_SECONDS = 45.0
DEFAULT_TOTAL_TIMEOUT_SECONDS = 540.0
POLL_INTERVAL_SECONDS = 0.25


class PhysicalSmokeError(Exception):
    """物理冒烟测试配置或执行错误。"""


def run_physical_smoke_test(
    windows: Sequence[int] | None = None,
    source_ids: Mapping[str, int] | None = None,
    settle_seconds: float = DEFAULT_SETTLE_SECONDS,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ppt_timeout_seconds: float = DEFAULT_PPT_TIMEOUT_SECONDS,
    stream_timeout_seconds: float = DEFAULT_STREAM_TIMEOUT_SECONDS,
    total_timeout_seconds: float = DEFAULT_TOTAL_TIMEOUT_SECONDS,
    reset_after: bool = True,
) -> dict[str, object]:
    """
    在本机播放器上按窗口真实播放所有媒体源类型并最终重置窗口。

    :param windows: 要测试的窗口编号；为空时测试 1-4 全部窗口
    :param source_ids: 按媒体源类型显式指定的 source_id 映射
    :param settle_seconds: 每次打开成功后保持播放的秒数
    :param timeout_seconds: 普通媒体源等待播放的超时秒数
    :param ppt_timeout_seconds: PPT 等待播放的超时秒数
    :param stream_timeout_seconds: 流媒体等待播放的超时秒数
    :param total_timeout_seconds: 播放阶段全局总超时秒数，超时后不再打开后续源
    :param reset_after: 是否在测试完成后执行 reset-all
    :return: 结构化测试结果
    :raises PhysicalSmokeError: 窗口或媒体源配置无效时
    """
    selected_windows = _normalize_windows(windows)
    selected_sources = _resolve_sources(source_ids or {})
    normalized_total_timeout = _normalize_total_timeout(total_timeout_seconds)
    started_at = timezone.now()
    started_monotonic = time.monotonic()
    play_deadline = started_monotonic + normalized_total_timeout
    normalized_settle = max(0.0, float(settle_seconds))
    results: list[dict[str, object]] = []

    for window_id in selected_windows:
        for source_type in WINDOW_SOURCE_TYPE_SEQUENCE:
            source = selected_sources[source_type]
            if time.monotonic() >= play_deadline:
                results.append(_deadline_failed_result(window_id, source))
                continue
            timeout = _timeout_for_source(source_type, timeout_seconds, ppt_timeout_seconds, stream_timeout_seconds)
            results.append(_run_single_source(window_id, source, normalized_settle, timeout, play_deadline))

    audio_source = selected_sources[SourceType.AUDIO]
    if time.monotonic() >= play_deadline:
        results.append(_deadline_failed_result(0, audio_source))
    else:
        results.append(_run_background_audio_source(
            audio_source,
            normalized_settle,
            timeout_seconds,
            play_deadline,
        ))

    reset_result = _reset_after_smoke(reset_after, DEFAULT_RESET_TIMEOUT_SECONDS)
    finished_at = timezone.now()
    failed = sum(1 for item in results if item["status"] != "ok")
    success = failed == 0 and reset_result["status"] in {"ok", "skipped"}
    return {
        "success": success,
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "elapsed_seconds": round(time.monotonic() - started_monotonic, 3),
        "total_timeout_seconds": normalized_total_timeout,
        "windows": selected_windows,
        "source_ids": {source_type: source.pk for source_type, source in selected_sources.items()},
        "summary": {
            "total": len(results),
            "passed": len(results) - failed,
            "failed": failed,
        },
        "results": results,
        "reset": reset_result,
        "sessions": get_all_sessions_snapshot(),
    }


def _run_single_source(
    window_id: int,
    source: MediaSource,
    settle_seconds: float,
    timeout_seconds: float,
    play_deadline: float,
) -> dict[str, object]:
    """
    在单个窗口真实打开并关闭一个媒体源。
    :param window_id: 窗口编号
    :param source: 待播放媒体源
    :param settle_seconds: 成功打开后保持播放的秒数
    :param timeout_seconds: 等待播放和关闭的超时秒数
    :param play_deadline: 播放阶段全局截止时间
    :return: 单项测试结果
    """
    open_started = time.monotonic()
    open_ok = False
    open_error = ""
    try:
        open_source(
            window_id,
            source.pk,
            autoplay=True,
            ppt_backend=DEFAULT_PPT_BACKEND if source.source_type == SourceType.PPT else None,
            target_slide=1 if source.source_type == SourceType.PPT else 0,
        )
        open_ok, open_error = _wait_for_open(window_id, source, _remaining_timeout(play_deadline, timeout_seconds))
        if open_ok and settle_seconds > 0:
            time.sleep(_remaining_timeout(play_deadline, settle_seconds))
    except Exception as open_exception:
        open_error = str(open_exception)
    open_elapsed = time.monotonic() - open_started

    close_started = time.monotonic()
    close_ok = False
    close_error = ""
    try:
        close_source(window_id)
        close_ok, close_error = _wait_for_idle(window_id, _remaining_timeout(play_deadline, timeout_seconds))
    except Exception as close_exception:
        close_error = str(close_exception)
    close_elapsed = time.monotonic() - close_started

    error_message = open_error or close_error
    return {
        "window_id": window_id,
        "source_type": source.source_type,
        "source_id": source.pk,
        "source_name": source.name,
        "status": "ok" if open_ok and close_ok else "failed",
        "open_elapsed": round(open_elapsed, 3),
        "close_elapsed": round(close_elapsed, 3),
        "error_message": error_message,
        "open_error": open_error,
        "close_error": close_error,
    }


def _run_background_audio_source(
    source: MediaSource,
    settle_seconds: float,
    timeout_seconds: float,
    play_deadline: float,
) -> dict[str, object]:
    """
    真实播放并停止背景音频源。
    :param source: 音频媒体源
    :param settle_seconds: 成功播放后保持播放的秒数
    :param timeout_seconds: 等待播放和停止的超时秒数
    :param play_deadline: 播放阶段全局截止时间
    :return: 单项测试结果，window_id=0 表示背景音乐通道
    """
    open_started = time.monotonic()
    open_ok = False
    open_error = ""
    try:
        play_background_audio_source(source.pk)
        open_ok, open_error = _wait_for_background_audio_open(
            source,
            _remaining_timeout(play_deadline, timeout_seconds),
        )
        if open_ok and settle_seconds > 0:
            time.sleep(_remaining_timeout(play_deadline, settle_seconds))
    except Exception as open_exception:
        open_error = str(open_exception)
    open_elapsed = time.monotonic() - open_started

    close_started = time.monotonic()
    close_ok = False
    close_error = ""
    try:
        stop_background_audio(clear_source=True)
        close_ok, close_error = _wait_for_background_audio_idle(_remaining_timeout(play_deadline, timeout_seconds))
    except Exception as close_exception:
        close_error = str(close_exception)
    close_elapsed = time.monotonic() - close_started

    error_message = open_error or close_error
    return {
        "window_id": 0,
        "source_type": source.source_type,
        "source_id": source.pk,
        "source_name": source.name,
        "status": "ok" if open_ok and close_ok else "failed",
        "open_elapsed": round(open_elapsed, 3),
        "close_elapsed": round(close_elapsed, 3),
        "error_message": error_message,
        "open_error": open_error,
        "close_error": close_error,
    }


def _deadline_failed_result(window_id: int, source: MediaSource) -> dict[str, object]:
    """
    构造全局超时后跳过后续打开的结果项。
    :param window_id: 窗口编号
    :param source: 被跳过的媒体源
    :return: 失败结果
    """
    error_message = "物理冒烟测试达到全局总超时，已跳过后续媒体源打开"
    return {
        "window_id": window_id,
        "source_type": source.source_type,
        "source_id": source.pk,
        "source_name": source.name,
        "status": "failed",
        "open_elapsed": 0.0,
        "close_elapsed": 0.0,
        "error_message": error_message,
        "open_error": error_message,
        "close_error": "",
    }


def _remaining_timeout(deadline: float, preferred_timeout: float) -> float:
    """
    按全局截止时间裁剪单步等待时间。
    :param deadline: 全局截止 monotonic 时间
    :param preferred_timeout: 单步期望超时
    :return: 实际可等待秒数
    """
    return max(0.1, min(float(preferred_timeout), deadline - time.monotonic()))


def _wait_for_open(window_id: int, source: MediaSource, timeout_seconds: float) -> tuple[bool, str]:
    """
    等待指定窗口真实进入目标媒体源播放态。
    :param window_id: 窗口编号
    :param source: 目标媒体源
    :param timeout_seconds: 超时秒数
    :return: (是否成功, 错误信息)
    """
    deadline = time.monotonic() + max(0.1, float(timeout_seconds))
    while time.monotonic() <= deadline:
        session = get_or_create_session(window_id)
        if session.media_source_id == source.pk and session.playback_state == PlaybackState.ERROR:
            return False, session.error_message or "播放器上报错误"
        if _session_matches_open_source(session, source):
            return True, ""
        time.sleep(POLL_INTERVAL_SECONDS)
    session = get_or_create_session(window_id)
    return False, f"等待 {source.source_type} 源进入播放态超时，当前状态={session.playback_state}"


def _wait_for_idle(window_id: int, timeout_seconds: float) -> tuple[bool, str]:
    """
    等待指定窗口完成关闭并回到空闲态。
    :param window_id: 窗口编号
    :param timeout_seconds: 超时秒数
    :return: (是否成功, 错误信息)
    """
    deadline = time.monotonic() + max(0.1, float(timeout_seconds))
    while time.monotonic() <= deadline:
        session = get_or_create_session(window_id)
        if _session_is_idle(session):
            return True, ""
        time.sleep(POLL_INTERVAL_SECONDS)
    session = get_or_create_session(window_id)
    return False, f"等待窗口 {window_id} 关闭超时，当前状态={session.playback_state}"


def _wait_for_background_audio_open(source: MediaSource, timeout_seconds: float) -> tuple[bool, str]:
    """
    等待背景音频进入播放态。
    :param source: 目标音频源
    :param timeout_seconds: 超时秒数
    :return: (是否成功, 错误信息)
    """
    deadline = time.monotonic() + max(0.1, float(timeout_seconds))
    while time.monotonic() <= deadline:
        state = BackgroundAudioState.get_instance()
        if state.current_source_id == source.pk and state.playback_state == PlaybackState.ERROR:
            return False, state.error_message or "背景音乐播放器上报错误"
        if (
            state.current_source_id == source.pk
            and state.pending_command in {"", BackgroundAudioCommand.NONE}
            and state.playback_state == PlaybackState.PLAYING
        ):
            return True, ""
        time.sleep(POLL_INTERVAL_SECONDS)
    state = BackgroundAudioState.get_instance()
    return False, f"等待背景音乐进入播放态超时，当前状态={state.playback_state}"


def _wait_for_background_audio_idle(timeout_seconds: float) -> tuple[bool, str]:
    """
    等待背景音频停止并清空当前源。
    :param timeout_seconds: 超时秒数
    :return: (是否成功, 错误信息)
    """
    deadline = time.monotonic() + max(0.1, float(timeout_seconds))
    while time.monotonic() <= deadline:
        state = BackgroundAudioState.get_instance()
        if _background_audio_is_idle(state):
            return True, ""
        time.sleep(POLL_INTERVAL_SECONDS)
    state = BackgroundAudioState.get_instance()
    return False, f"等待背景音乐停止超时，当前状态={state.playback_state}"


def _wait_for_all_idle(windows: Sequence[int], timeout_seconds: float) -> tuple[bool, str]:
    """
    等待全部测试窗口完成 reset-all 并回到空闲态。
    :param windows: 窗口编号列表
    :param timeout_seconds: 超时秒数
    :return: (是否成功, 错误信息)
    """
    deadline = time.monotonic() + max(0.1, float(timeout_seconds))
    while time.monotonic() <= deadline:
        sessions = [get_or_create_session(window_id) for window_id in windows]
        if all(_session_is_idle(session) for session in sessions):
            return True, ""
        time.sleep(POLL_INTERVAL_SECONDS)
    return False, "等待 reset-all 完成超时"


def _reset_after_smoke(reset_after: bool, timeout_seconds: float) -> dict[str, object]:
    """
    测试结束后按需执行 reset-all。
    :param reset_after: 是否执行 reset-all
    :param timeout_seconds: 等待 reset-all 完成的超时秒数
    :return: reset 操作结果
    """
    if not reset_after:
        return {"status": "skipped", "elapsed": 0.0, "error_message": ""}
    started = time.monotonic()
    try:
        reset_all_sessions_to_idle()
        ok, error = _wait_for_all_idle(tuple(VALID_WINDOW_IDS), timeout_seconds)
        stop_background_audio(clear_source=True)
        audio_ok, audio_error = _wait_for_background_audio_idle(timeout_seconds)
        ok = ok and audio_ok
        error = error or audio_error
    except Exception as reset_exception:
        ok = False
        error = str(reset_exception)
    return {
        "status": "ok" if ok else "failed",
        "elapsed": round(time.monotonic() - started, 3),
        "error_message": error,
    }


def _session_matches_open_source(session: PlaybackSession, source: MediaSource) -> bool:
    """
    判断会话是否已稳定打开指定媒体源。
    :param session: 播放会话
    :param source: 目标媒体源
    :return: True 表示已进入可观察播放态
    """
    if session.media_source_id != source.pk:
        return False
    if session.pending_command not in {"", PlaybackCommand.NONE}:
        return False
    if session.playback_state != PlaybackState.PLAYING:
        return False
    if source.source_type == SourceType.PPT:
        return session.current_slide >= 1 or session.total_slides > 0
    return True


def _session_is_idle(session: PlaybackSession) -> bool:
    """
    判断会话是否已被播放器确认关闭。
    :param session: 播放会话
    :return: True 表示空闲且无待处理指令
    """
    return (
        session.media_source_id is None
        and session.playback_state == PlaybackState.IDLE
        and session.pending_command in {"", PlaybackCommand.NONE}
    )


def _background_audio_is_idle(state: BackgroundAudioState) -> bool:
    """
    判断背景音频是否已停止且没有待处理指令。
    :param state: 背景音频状态
    :return: True 表示可视为已停止
    """
    return (
        state.current_source_id is None
        and state.playback_state in {PlaybackState.IDLE, PlaybackState.STOPPED}
        and state.pending_command in {"", BackgroundAudioCommand.NONE}
    )


def _normalize_windows(windows: Sequence[int] | None) -> list[int]:
    """
    解析并校验窗口列表。
    :param windows: 原始窗口列表
    :return: 去重后的窗口编号列表
    :raises PhysicalSmokeError: 存在非法窗口时
    """
    if windows is None:
        raw_windows = list(VALID_WINDOW_IDS)
    elif isinstance(windows, (str, bytes)):
        raise PhysicalSmokeError("窗口列表必须是整数数组")
    else:
        raw_windows = list(windows)
    normalized: list[int] = []
    for raw_window in raw_windows:
        try:
            window_id = int(raw_window)
        except (TypeError, ValueError) as parse_error:
            raise PhysicalSmokeError(f"窗口编号无效：{raw_window}") from parse_error
        if window_id not in VALID_WINDOW_IDS:
            raise PhysicalSmokeError(f"窗口编号不在有效范围内：{window_id}")
        if window_id not in normalized:
            normalized.append(window_id)
    if not normalized:
        raise PhysicalSmokeError("至少需要指定一个窗口")
    return normalized


def _normalize_total_timeout(total_timeout_seconds: float) -> float:
    """
    归一化播放阶段全局总超时，避免前端请求超时早于后端执行上限。
    :param total_timeout_seconds: 原始总超时秒数
    :return: 1 秒到默认总超时之间的安全秒数
    :raises PhysicalSmokeError: 总超时不是有限数字时
    """
    try:
        requested_timeout = float(total_timeout_seconds)
    except (TypeError, ValueError) as parse_error:
        raise PhysicalSmokeError("全局总超时必须是有限数字") from parse_error
    if not isfinite(requested_timeout):
        raise PhysicalSmokeError("全局总超时必须是有限数字")
    return min(max(1.0, requested_timeout), DEFAULT_TOTAL_TIMEOUT_SECONDS)


def _resolve_sources(source_ids: Mapping[str, int]) -> dict[str, MediaSource]:
    """
    解析每种媒体源类型对应的测试源。
    :param source_ids: 按 source_type 指定的 source_id
    :return: source_type 到 MediaSource 的映射
    :raises PhysicalSmokeError: 配置了未知类型或缺少某类型媒体源时
    """
    unknown_types = sorted(set(source_ids.keys()) - set(SOURCE_TYPE_SEQUENCE))
    if unknown_types:
        raise PhysicalSmokeError(f"未知媒体源类型：{', '.join(unknown_types)}")

    resolved: dict[str, MediaSource] = {}
    missing: list[str] = []
    for source_type in SOURCE_TYPE_SEQUENCE:
        explicit_source_id = int(source_ids.get(source_type) or 0)
        source = _source_by_id(source_type, explicit_source_id) if explicit_source_id > 0 else _latest_source(source_type)
        if source is None:
            missing.append(source_type)
            continue
        resolved[source_type] = source
    if missing:
        raise PhysicalSmokeError(f"缺少可用于物理冒烟测试的媒体源类型：{', '.join(missing)}")
    return resolved


def _source_by_id(source_type: str, source_id: int) -> MediaSource | None:
    """
    按显式 ID 读取并校验媒体源类型。
    :param source_type: 期望媒体源类型
    :param source_id: 媒体源 ID
    :return: 媒体源或 None
    :raises PhysicalSmokeError: ID 存在但类型不匹配时
    """
    source = MediaSource.objects.filter(pk=source_id).first()
    if source is None:
        raise PhysicalSmokeError(f"媒体源不存在：{source_type}={source_id}")
    if source.source_type != source_type:
        raise PhysicalSmokeError(f"媒体源 {source_id} 类型为 {source.source_type}，不是 {source_type}")
    return source


def _latest_source(source_type: str) -> MediaSource | None:
    """
    自动选择指定类型的测试媒体源，优先选择可用源。
    :param source_type: 媒体源类型
    :return: 媒体源或 None
    """
    source = MediaSource.objects.filter(source_type=source_type, is_available=True).order_by("-created_at").first()
    if source is not None:
        return source
    return MediaSource.objects.filter(source_type=source_type).order_by("-created_at").first()


def _timeout_for_source(
    source_type: str,
    timeout_seconds: float,
    ppt_timeout_seconds: float,
    stream_timeout_seconds: float,
) -> float:
    """
    按媒体源类型选择等待超时。
    :param source_type: 媒体源类型
    :param timeout_seconds: 普通超时
    :param ppt_timeout_seconds: PPT 超时
    :param stream_timeout_seconds: 流媒体超时
    :return: 超时秒数
    """
    if source_type == SourceType.PPT:
        return float(ppt_timeout_seconds)
    if source_type in STREAM_SOURCE_TYPES:
        return float(stream_timeout_seconds)
    return float(timeout_seconds)


__all__ = [
    "PhysicalSmokeError",
    "SOURCE_TYPE_SEQUENCE",
    "run_physical_smoke_test",
]
