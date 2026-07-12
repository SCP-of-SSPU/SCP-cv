#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PowerPoint Broker 四窗口并发物理冒烟服务。
@Project : SCP-cv
@File : ppt_physical_smoke.py
@Author : Qintsg
@Date : 2026-07-11
'''
from __future__ import annotations

import uuid
from collections.abc import Callable, Mapping
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from scp_cv.player.ppt_broker import (
    PptBroker,
    PptCommand,
    PptCommandRequest,
    PptOpenRequest,
    PptSessionKey,
    PptState,
)
from scp_cv.services.ppt_physical_smoke_validation import (
    DEFAULT_PPT_SMOKE_ITERATIONS,
    PPT_SMOKE_WINDOW_IDS,
    PptPhysicalSmokeError,
    normalize_iterations as _normalize_iterations,
    normalize_parent_hwnds as _normalize_parent_hwnds,
    normalize_ppt_paths as _normalize_ppt_paths,
    normalize_source_ids as _normalize_source_ids,
    read_broker_health as _read_broker_health,
    read_parent_hwnd as _read_parent_hwnd,
    read_window_exists as _read_window_exists,
    shared_ppt_path as _shared_ppt_path,
    validate_parent_chain as _validate_parent_chain,
    validate_session_identity as _validate_session_identity,
)


def run_ppt_concurrency_smoke_test(
    broker: PptBroker,
    ppt_path: str | Path | Mapping[int, str | Path],
    parent_hwnds: Mapping[int, int],
    *,
    iterations: int = DEFAULT_PPT_SMOKE_ITERATIONS,
    parent_hwnd_reader: Callable[[int], int] | None = None,
    window_exists_reader: Callable[[int], bool] | None = None,
    source_ids: Mapping[int, int] | None = None,
) -> dict[str, object]:
    """
    并发打开四个 Broker 会话并校验放映 HWND 和父窗口。
    :param broker: 已连接的 PowerPoint Broker
    :param ppt_path: 四窗共用的 PPT 路径，或窗口 1-4 到 PPT 路径的映射
    :param parent_hwnds: 窗口 1-4 对应的宿主 HWND
    :param iterations: 重复轮数，现场默认 3 轮
    :param parent_hwnd_reader: 按放映 HWND 读取实际父 HWND 的可替换 seam
    :param window_exists_reader: 按放映 HWND 判断窗口是否仍有效的可替换 seam
    :param source_ids: 可选的窗口 1-4 到媒体源 ID 映射，用于请求和诊断
    :return: 结构化冒烟结果
    :raises PptPhysicalSmokeError: 文件、窗口或 Broker 环境不可用时
    """
    normalized_paths = _normalize_ppt_paths(ppt_path)
    normalized_parents = _normalize_parent_hwnds(parent_hwnds)
    normalized_source_ids = _normalize_source_ids(source_ids)
    normalized_iterations = _normalize_iterations(iterations)
    read_parent = parent_hwnd_reader or _read_parent_hwnd
    read_window_exists = window_exists_reader or _read_window_exists
    health = _read_broker_health(broker)
    run_token = uuid.uuid4().hex
    rounds: list[dict[str, object]] = []

    for iteration in range(1, normalized_iterations + 1):
        sessions = {
            window_id: PptSessionKey(
                window_id=window_id,
                owner_token=f"physical-smoke-{run_token}-{iteration}-{window_id}",
            )
            for window_id in PPT_SMOKE_WINDOW_IDS
        }
        round_result: dict[str, object]
        try:
            states = _open_all_windows(
                broker,
                normalized_paths,
                normalized_parents,
                normalized_source_ids,
                sessions,
                iteration,
            )
            actual_parents = _validate_open_states(
                states,
                normalized_parents,
                read_parent,
            )
            navigation_slides = _verify_navigation_isolation(
                broker,
                sessions,
                states,
                normalized_parents,
                read_parent,
                iteration,
            )
            closed_window_id = PPT_SMOKE_WINDOW_IDS[
                (iteration - 1) % len(PPT_SMOKE_WINDOW_IDS)
            ]
            surviving_slideshow_hwnds = _verify_close_isolation(
                broker,
                sessions,
                states,
                normalized_parents,
                read_parent,
                closed_window_id,
            )
            reopened_state, final_slides = _reopen_and_validate_all_windows(
                broker,
                normalized_paths[closed_window_id],
                normalized_source_ids[closed_window_id],
                sessions,
                states,
                normalized_parents,
                read_parent,
                navigation_slides,
                closed_window_id,
                iteration,
            )
            round_result = {
                "iteration": iteration,
                "status": "ok",
                "slideshow_hwnds": {
                    window_id: states[window_id].slideshow_hwnd
                    for window_id in PPT_SMOKE_WINDOW_IDS
                },
                "parent_hwnds": actual_parents,
                "navigation_slides": navigation_slides,
                "closed_window_id": closed_window_id,
                "surviving_slideshow_hwnds": surviving_slideshow_hwnds,
                "reopened_slideshow_hwnd": reopened_state.slideshow_hwnd,
                "reopened_parent_hwnd": reopened_state.parent_hwnd,
                "final_slides": final_slides,
                "error_message": "",
            }
        except Exception as round_error:
            round_result = {
                "iteration": iteration,
                "status": "failed",
                "slideshow_hwnds": {},
                "parent_hwnds": {},
                "navigation_slides": {},
                "closed_window_id": 0,
                "surviving_slideshow_hwnds": {},
                "reopened_slideshow_hwnd": 0,
                "reopened_parent_hwnd": 0,
                "final_slides": {},
                "error_message": str(round_error),
            }
        finally:
            cleanup_errors = _close_sessions(
                broker,
                sessions,
                read_window_exists,
            )
        round_result["cleanup_errors"] = cleanup_errors
        if cleanup_errors:
            cleanup_message = "清理 PPT Broker 会话失败：" + "; ".join(cleanup_errors)
            round_result["status"] = "failed"
            existing_error = str(round_result.get("error_message", ""))
            round_result["error_message"] = "; ".join(
                message for message in (existing_error, cleanup_message) if message
            )
        rounds.append(round_result)
        if round_result["status"] != "ok":
            break

    completed = sum(1 for item in rounds if item["status"] == "ok")
    return {
        "success": completed == normalized_iterations,
        "ppt_path": _shared_ppt_path(normalized_paths),
        "ppt_paths": {
            window_id: str(normalized_paths[window_id])
            for window_id in PPT_SMOKE_WINDOW_IDS
        },
        "source_ids": normalized_source_ids,
        "windows": list(PPT_SMOKE_WINDOW_IDS),
        "iterations_requested": normalized_iterations,
        "iterations_completed": completed,
        "broker": {
            "pid": health.pid,
            "generation": health.generation,
        },
        "rounds": rounds,
    }


def _open_all_windows(
    broker: PptBroker,
    ppt_paths: Mapping[int, Path],
    parent_hwnds: Mapping[int, int],
    source_ids: Mapping[int, int],
    sessions: Mapping[int, PptSessionKey],
    iteration: int,
) -> dict[int, PptState]:
    """从四个调用线程同时向 Broker 提交打开请求。"""
    requests = {
        window_id: PptOpenRequest(
            session=sessions[window_id],
            uri=str(ppt_paths[window_id]),
            parent_hwnd=parent_hwnds[window_id],
            autoplay=True,
            start_slide=1,
            source_id=source_ids[window_id],
            request_id=f"physical-smoke-open-{iteration}-{window_id}",
        )
        for window_id in PPT_SMOKE_WINDOW_IDS
    }
    states: dict[int, PptState] = {}
    failures: dict[int, str] = {}
    with ThreadPoolExecutor(
        max_workers=len(PPT_SMOKE_WINDOW_IDS),
        thread_name_prefix="ppt-physical-smoke-open",
    ) as executor:
        futures = {
            executor.submit(broker.open, request): window_id
            for window_id, request in requests.items()
        }
        for future in as_completed(futures):
            window_id = futures[future]
            try:
                states[window_id] = future.result()
            except Exception as open_error:
                failures[window_id] = str(open_error)
    if failures:
        diagnostics = "; ".join(
            f"窗口 {window_id}: {message}"
            for window_id, message in sorted(failures.items())
        )
        raise PptPhysicalSmokeError(f"并发打开 PowerPoint 放映失败：{diagnostics}")
    return states


def _validate_open_states(
    states: Mapping[int, PptState],
    expected_parents: Mapping[int, int],
    parent_hwnd_reader: Callable[[int], int],
) -> dict[int, int]:
    """验证四个唯一放映 HWND 及其实际父窗口。"""
    slideshow_hwnds = [states[window_id].slideshow_hwnd for window_id in PPT_SMOKE_WINDOW_IDS]
    invalid_windows = [
        window_id
        for window_id in PPT_SMOKE_WINDOW_IDS
        if states[window_id].slideshow_hwnd <= 0
    ]
    if invalid_windows:
        raise PptPhysicalSmokeError(
            f"Broker 未返回有效放映 HWND：windows={invalid_windows}"
        )
    if len(set(slideshow_hwnds)) != len(PPT_SMOKE_WINDOW_IDS):
        raise PptPhysicalSmokeError(
            f"四窗口放映 HWND 不唯一：hwnds={slideshow_hwnds}"
        )

    actual_parents: dict[int, int] = {}
    for window_id in PPT_SMOKE_WINDOW_IDS:
        state = states[window_id]
        expected_parent = expected_parents[window_id]
        if state.error_message:
            raise PptPhysicalSmokeError(
                f"窗口 {window_id} 打开后上报错误：{state.error_message}"
            )
        if state.current_slide != 1:
            raise PptPhysicalSmokeError(
                "PPT 打开后未停留在第 1 页："
                f"window={window_id}, actual_slide={state.current_slide}"
            )
        if state.parent_hwnd != expected_parent:
            raise PptPhysicalSmokeError(
                "Broker 状态中的父 HWND 不匹配："
                f"window={window_id}, expected={expected_parent}, actual={state.parent_hwnd}"
            )
        actual_parents[window_id] = _validate_parent_chain(
            window_id,
            state.slideshow_hwnd,
            expected_parent,
            parent_hwnd_reader,
        )
    return actual_parents


def _verify_navigation_isolation(
    broker: PptBroker,
    sessions: Mapping[int, PptSessionKey],
    opened_states: Mapping[int, PptState],
    expected_parents: Mapping[int, int],
    parent_hwnd_reader: Callable[[int], int],
    iteration: int,
) -> dict[int, int]:
    """逐窗跳到第 2 页，并在每一步确认其他窗口页码未变化。"""
    expected_slides = {window_id: 1 for window_id in PPT_SMOKE_WINDOW_IDS}
    for window_id in PPT_SMOKE_WINDOW_IDS:
        target_slide = window_id + 1
        if opened_states[window_id].total_slides < target_slide:
            raise PptPhysicalSmokeError(
                "并发 PPT 物理冒烟文件页数不足以执行不同页码跳转："
                f"window={window_id}, required_slide={target_slide}, "
                f"total_slides={opened_states[window_id].total_slides}"
            )
        expected_slides[window_id] = target_slide
        broker.command(
            PptCommandRequest(
                session=sessions[window_id],
                command=PptCommand.GOTO,
                slide_index=target_slide,
                request_id=f"physical-smoke-goto-{iteration}-{window_id}",
            )
        )
        snapshots = {
            candidate_id: broker.get_state(sessions[candidate_id])
            for candidate_id in PPT_SMOKE_WINDOW_IDS
        }
        for candidate_id, snapshot in snapshots.items():
            expected_slide = expected_slides[candidate_id]
            if snapshot.current_slide != expected_slide:
                raise PptPhysicalSmokeError(
                    "PPT 独立翻页隔离失败："
                    f"command_window={window_id}, observed_window={candidate_id}, "
                    f"expected_slide={expected_slide}, actual_slide={snapshot.current_slide}"
                )
            _validate_session_identity(
                candidate_id,
                snapshot,
                opened_states[candidate_id],
                expected_parents[candidate_id],
                parent_hwnd_reader,
                check_slide=False,
            )
    return expected_slides


def _verify_close_isolation(
    broker: PptBroker,
    sessions: Mapping[int, PptSessionKey],
    opened_states: Mapping[int, PptState],
    expected_parents: Mapping[int, int],
    parent_hwnd_reader: Callable[[int], int],
    closed_window_id: int,
) -> dict[int, int]:
    """关闭一个会话，并确认其余三个 HWND、页码和父窗口保持不变。"""
    remaining_window_ids = [
        window_id
        for window_id in PPT_SMOKE_WINDOW_IDS
        if window_id != closed_window_id
    ]
    before_close = {
        window_id: broker.get_state(sessions[window_id])
        for window_id in remaining_window_ids
    }
    broker.close(sessions[closed_window_id])
    survivors: dict[int, int] = {}
    for window_id in remaining_window_ids:
        after_close = broker.get_state(sessions[window_id])
        _validate_session_identity(
            window_id,
            after_close,
            before_close[window_id],
            expected_parents[window_id],
            parent_hwnd_reader,
            check_slide=True,
        )
        expected_slide = window_id + 1
        if after_close.current_slide != expected_slide:
            raise PptPhysicalSmokeError(
                "关闭单个 PPT 后其他窗口页码改变："
                f"closed_window={closed_window_id}, observed_window={window_id}, "
                f"expected_slide={expected_slide}, actual_slide={after_close.current_slide}"
            )
        survivors[window_id] = after_close.slideshow_hwnd
    return survivors


def _reopen_and_validate_all_windows(
    broker: PptBroker,
    ppt_path: Path,
    source_id: int,
    sessions: Mapping[int, PptSessionKey],
    opened_states: Mapping[int, PptState],
    expected_parents: Mapping[int, int],
    parent_hwnd_reader: Callable[[int], int],
    expected_slides: Mapping[int, int],
    closed_window_id: int,
    iteration: int,
) -> tuple[PptState, dict[int, int]]:
    """重开被关闭会话，并再次校验四个活动会话互不串扰。"""
    reopened = broker.open(
        PptOpenRequest(
            session=sessions[closed_window_id],
            uri=str(ppt_path),
            parent_hwnd=expected_parents[closed_window_id],
            autoplay=True,
            start_slide=expected_slides[closed_window_id],
            source_id=source_id,
            request_id=f"physical-smoke-reopen-{iteration}-{closed_window_id}",
        )
    )
    snapshots = {
        window_id: broker.get_state(sessions[window_id])
        for window_id in PPT_SMOKE_WINDOW_IDS
    }
    active_hwnds = [state.slideshow_hwnd for state in snapshots.values()]
    if any(hwnd <= 0 for hwnd in active_hwnds) or len(set(active_hwnds)) != len(active_hwnds):
        raise PptPhysicalSmokeError(
            "重开单个 PPT 后四窗口放映 HWND 无效或不唯一："
            f"hwnds={active_hwnds}"
        )
    for window_id, snapshot in snapshots.items():
        baseline = reopened if window_id == closed_window_id else opened_states[window_id]
        _validate_session_identity(
            window_id,
            snapshot,
            baseline,
            expected_parents[window_id],
            parent_hwnd_reader,
            check_slide=False,
        )
        expected_slide = expected_slides[window_id]
        if snapshot.current_slide != expected_slide:
            raise PptPhysicalSmokeError(
                "重开单个 PPT 后窗口页码改变："
                f"reopened_window={closed_window_id}, observed_window={window_id}, "
                f"expected_slide={expected_slide}, actual_slide={snapshot.current_slide}"
            )
    return reopened, {
        window_id: snapshots[window_id].current_slide
        for window_id in PPT_SMOKE_WINDOW_IDS
    }


def _close_sessions(
    broker: PptBroker,
    sessions: Mapping[int, PptSessionKey],
    window_exists_reader: Callable[[int], bool],
) -> list[str]:
    """幂等关闭本轮全部 owner 会话，并返回带窗口号的清理错误。"""
    errors: list[str] = []
    active_hwnds: dict[int, int] = {}
    for window_id, session in sessions.items():
        try:
            state = broker.get_state(session)
        except Exception:
            continue
        if state.slideshow_hwnd > 0:
            active_hwnds[window_id] = state.slideshow_hwnd
    with ThreadPoolExecutor(
        max_workers=len(PPT_SMOKE_WINDOW_IDS),
        thread_name_prefix="ppt-physical-smoke-close",
    ) as executor:
        futures = {
            executor.submit(broker.close, session): window_id
            for window_id, session in sessions.items()
        }
        for future in as_completed(futures):
            window_id = futures[future]
            try:
                future.result()
            except Exception as close_error:
                errors.append(f"窗口 {window_id}: {close_error}")
    for window_id, session in sessions.items():
        try:
            state = broker.get_state(session)
        except Exception:
            continue
        errors.append(
            "窗口 "
            f"{window_id}: 最终关闭后 Broker 会话仍存在，"
            f"slideshow_hwnd={state.slideshow_hwnd}"
        )
    for window_id, slideshow_hwnd in active_hwnds.items():
        try:
            still_exists = window_exists_reader(slideshow_hwnd)
        except Exception as probe_error:
            errors.append(
                f"窗口 {window_id}: 无法校验最终关闭后的放映 "
                f"HWND={slideshow_hwnd}: {probe_error}"
            )
            continue
        if still_exists:
            errors.append(
                f"窗口 {window_id}: 最终关闭后放映 HWND 仍存在，"
                f"hwnd={slideshow_hwnd}"
            )
    errors.sort()
    return errors


__all__ = [
    "DEFAULT_PPT_SMOKE_ITERATIONS",
    "PPT_SMOKE_WINDOW_IDS",
    "PptPhysicalSmokeError",
    "run_ppt_concurrency_smoke_test",
]
