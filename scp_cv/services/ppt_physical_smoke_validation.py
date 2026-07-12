#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PowerPoint 四窗口物理冒烟的输入和运行环境校验。
@Project : SCP-cv
@File : ppt_physical_smoke_validation.py
@Author : Qintsg
@Date : 2026-07-11
'''
from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path

from scp_cv.player.ppt_broker import BrokerHealth, PptBroker, PptState
from scp_cv.player.ppt_broker.window_titles import (
    looks_like_slideshow_title,
    normalize_window_title,
)

PPT_SMOKE_WINDOW_IDS: tuple[int, ...] = (1, 2, 3, 4)
DEFAULT_PPT_SMOKE_ITERATIONS = 3


class PptPhysicalSmokeError(RuntimeError):
    """并发 PPT 物理冒烟的配置或环境错误。"""


def normalize_ppt_paths(
    ppt_path: str | Path | Mapping[int, str | Path],
) -> dict[int, Path]:
    """把单一路径或完整窗口映射归一成窗口 1-4 的绝对路径。"""
    if not isinstance(ppt_path, Mapping):
        normalized = _normalize_ppt_path(ppt_path)
        return {window_id: normalized for window_id in PPT_SMOKE_WINDOW_IDS}
    if set(ppt_path) != set(PPT_SMOKE_WINDOW_IDS):
        raise PptPhysicalSmokeError(
            "PPT 路径映射必须完整覆盖窗口 1-4："
            f"actual={sorted(ppt_path)}"
        )
    return {
        window_id: _normalize_ppt_path(ppt_path[window_id])
        for window_id in PPT_SMOKE_WINDOW_IDS
    }


def shared_ppt_path(ppt_paths: Mapping[int, Path]) -> str:
    """旧结果字段仅在四窗共用同一路径时保留值。"""
    unique_paths = {str(path) for path in ppt_paths.values()}
    return next(iter(unique_paths)) if len(unique_paths) == 1 else ""


def normalize_parent_hwnds(parent_hwnds: Mapping[int, int]) -> dict[int, int]:
    """验证四个非零且唯一的父 HWND。"""
    try:
        normalized = {
            int(window_id): int(hwnd)
            for window_id, hwnd in parent_hwnds.items()
        }
    except (TypeError, ValueError) as parse_error:
        raise PptPhysicalSmokeError(
            "父 HWND 映射必须使用整数窗口 ID 和 HWND"
        ) from parse_error
    expected = set(PPT_SMOKE_WINDOW_IDS)
    if set(normalized) != expected:
        raise PptPhysicalSmokeError(
            "必须提供窗口 1-4 的四个父 HWND："
            f"expected={sorted(expected)}, actual={sorted(normalized)}"
        )
    invalid = [window_id for window_id, hwnd in normalized.items() if hwnd <= 0]
    if invalid:
        raise PptPhysicalSmokeError(f"父 HWND 必须大于 0：windows={sorted(invalid)}")
    if len(set(normalized.values())) != len(PPT_SMOKE_WINDOW_IDS):
        raise PptPhysicalSmokeError("窗口 1-4 必须使用四个不同的父 HWND")
    return normalized


def normalize_source_ids(source_ids: Mapping[int, int] | None) -> dict[int, int]:
    """归一可选 source id；旧路径调用没有 ID 时使用 0。"""
    if source_ids is None:
        return {window_id: 0 for window_id in PPT_SMOKE_WINDOW_IDS}
    try:
        normalized = {
            int(window_id): int(source_id)
            for window_id, source_id in source_ids.items()
        }
    except (TypeError, ValueError) as parse_error:
        raise PptPhysicalSmokeError("PPT source id 映射必须使用整数") from parse_error
    if set(normalized) != set(PPT_SMOKE_WINDOW_IDS):
        raise PptPhysicalSmokeError("PPT source id 映射必须完整覆盖窗口 1-4")
    invalid = [window_id for window_id, source_id in normalized.items() if source_id <= 0]
    if invalid:
        raise PptPhysicalSmokeError(
            f"PPT source id 必须大于 0：windows={sorted(invalid)}"
        )
    return normalized


def normalize_iterations(iterations: int) -> int:
    """约束现场冒烟轮数。"""
    try:
        normalized = int(iterations)
    except (TypeError, ValueError) as parse_error:
        raise PptPhysicalSmokeError("PPT 冒烟重复轮数必须是整数") from parse_error
    if normalized <= 0 or normalized > 10:
        raise PptPhysicalSmokeError("PPT 冒烟重复轮数必须在 1-10 之间")
    return normalized


def read_broker_health(broker: PptBroker) -> BrokerHealth:
    """读取并验证 Broker health。"""
    try:
        health = broker.health()
    except Exception as health_error:
        raise PptPhysicalSmokeError(
            "无法连接 PowerPoint Broker；请先启动 runall 或 manage.py run_ppt_broker。"
            f"原始错误：{health_error}"
        ) from health_error
    if not health.ready:
        raise PptPhysicalSmokeError("PowerPoint Broker 未就绪")
    return health


def read_parent_hwnd(slideshow_hwnd: int) -> int:
    """通过 Win32 读取放映窗口的真实父 HWND。"""
    try:
        import win32gui
    except ImportError as import_error:
        raise PptPhysicalSmokeError(
            "无法加载 pywin32，不能校验 PowerPoint 放映窗口父 HWND"
        ) from import_error
    return int(win32gui.GetParent(slideshow_hwnd) or 0)


def read_window_exists(slideshow_hwnd: int) -> bool:
    """确认旧 HWND 仍有效且仍具有 PowerPoint 放映窗口身份。"""
    try:
        import win32gui
    except ImportError as import_error:
        raise PptPhysicalSmokeError(
            "无法加载 pywin32，不能校验最终关闭后的 PowerPoint 放映 HWND"
        ) from import_error
    if not bool(win32gui.IsWindow(slideshow_hwnd)):
        return False
    title = normalize_window_title(str(win32gui.GetWindowText(slideshow_hwnd)))
    return looks_like_slideshow_title(title)


def validate_parent_chain(
    window_id: int,
    slideshow_hwnd: int,
    expected_player_parent: int,
    parent_hwnd_reader: Callable[[int], int],
) -> int:
    """接受直接父子或 PowerPoint→Broker 宿主→Player 的严格两级父链。"""
    try:
        direct_parent = int(parent_hwnd_reader(slideshow_hwnd) or 0)
        if direct_parent == expected_player_parent:
            return expected_player_parent
        outer_parent = (
            int(parent_hwnd_reader(direct_parent) or 0)
            if direct_parent > 0
            else 0
        )
    except Exception as parent_error:
        raise PptPhysicalSmokeError(
            f"无法读取窗口 {window_id} 放映 HWND={slideshow_hwnd} 的实际父窗口："
            f"{parent_error}"
        ) from parent_error
    if outer_parent != expected_player_parent:
        raise PptPhysicalSmokeError(
            "PPT 会话 Win32 父 HWND 链不匹配："
            f"window={window_id}, slideshow={slideshow_hwnd}, "
            f"direct_parent={direct_parent}, outer_parent={outer_parent}, "
            f"expected_player_parent={expected_player_parent}"
        )
    return expected_player_parent


def validate_session_identity(
    window_id: int,
    state: PptState,
    baseline: PptState,
    expected_parent: int,
    parent_hwnd_reader: Callable[[int], int],
    *,
    check_slide: bool,
) -> None:
    """确认读取到的仍是原会话，且 Win32 嵌入关系没有漂移。"""
    if state.slideshow_hwnd != baseline.slideshow_hwnd:
        raise PptPhysicalSmokeError(
            "PPT 会话 HWND 意外变化："
            f"window={window_id}, expected={baseline.slideshow_hwnd}, "
            f"actual={state.slideshow_hwnd}"
        )
    if state.parent_hwnd != expected_parent:
        raise PptPhysicalSmokeError(
            "PPT 会话父 HWND 意外变化："
            f"window={window_id}, expected={expected_parent}, actual={state.parent_hwnd}"
        )
    validate_parent_chain(
        window_id,
        state.slideshow_hwnd,
        expected_parent,
        parent_hwnd_reader,
    )
    if check_slide and state.current_slide != baseline.current_slide:
        raise PptPhysicalSmokeError(
            "PPT 会话页码受到其他窗口关闭影响："
            f"window={window_id}, expected={baseline.current_slide}, "
            f"actual={state.current_slide}"
        )


def _normalize_ppt_path(ppt_path: str | Path) -> Path:
    path = Path(ppt_path).expanduser().resolve()
    if not path.is_file():
        raise PptPhysicalSmokeError(f"PPT 冒烟文件不存在：{path}")
    return path


__all__ = [
    "DEFAULT_PPT_SMOKE_ITERATIONS",
    "PPT_SMOKE_WINDOW_IDS",
    "PptPhysicalSmokeError",
    "normalize_iterations",
    "normalize_parent_hwnds",
    "normalize_ppt_paths",
    "normalize_source_ids",
    "read_broker_health",
    "read_parent_hwnd",
    "read_window_exists",
    "shared_ppt_path",
    "validate_parent_chain",
    "validate_session_identity",
]
