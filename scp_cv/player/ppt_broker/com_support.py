#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PowerPoint Broker 的 COM 创建、进程归属与瞬时错误识别辅助。
@Project : SCP-cv
@File : com_support.py
@Author : Qintsg
@Date : 2026-07-11
'''
from __future__ import annotations

import logging
import math
import zlib
from collections.abc import Mapping
from pathlib import Path

from scp_cv.player.ppt_broker.window_handles import normalize_hwnd
from scp_cv.ppt_com import POWERPOINT_COM_PROG_IDS

logger = logging.getLogger(__name__)
_TRANSIENT_HRESULTS = frozenset({0x80010001, 0x8001010A})
_RELEASED_OBJECT_HRESULTS = frozenset({0x80010108, 0x800401FD, 0x80048010})


def dispatch_powerpoint() -> object:
    """创建唯一的 Microsoft PowerPoint Application。"""
    import win32com.client

    last_error: BaseException | None = None
    for prog_id in POWERPOINT_COM_PROG_IDS:
        try:
            return win32com.client.DispatchEx(prog_id)
        except Exception as dispatch_error:
            last_error = dispatch_error
    raise RuntimeError(
        "未找到 Microsoft PowerPoint COM 自动化对象；请安装桌面版 Microsoft PowerPoint，"
        "并在当前 Windows 用户下完成首次启动。"
    ) from last_error


def read_powerpoint_process_id(application: object) -> int:
    """通过 PowerPoint Application HWND 读取所属进程。"""
    try:
        import win32process

        hwnd_value = getattr(application, "HWND", 0)
        if callable(hwnd_value):
            hwnd_value = hwnd_value()
        hwnd = normalize_hwnd(hwnd_value)
        _, process_id = win32process.GetWindowThreadProcessId(hwnd)
        return int(process_id)
    except Exception:
        return 0


def snapshot_powerpoint_process_ids() -> set[int] | None:
    """读取 DispatchEx 前已有的 POWERPNT.EXE PID；失败时从严返回 None。"""
    processes = snapshot_powerpoint_processes()
    return None if processes is None else set(processes)


def snapshot_powerpoint_processes() -> dict[int, float] | None:
    """读取 POWERPNT.EXE 的 PID 与创建时间；任一读取失败时从严返回 None。"""
    try:
        import psutil

        processes: dict[int, float] = {}
        for process_info in psutil.process_iter(["pid", "name", "create_time"]):
            if (
                str(process_info.info.get("name") or "").casefold()
                != "powerpnt.exe"
            ):
                continue
            process_id = int(process_info.info["pid"])
            created_at = float(
                process_info.info.get("create_time")
                or process_info.create_time()
            )
            processes[process_id] = created_at
        return processes
    except Exception as snapshot_error:
        logger.warning(
            "读取 PowerPoint PID/创建时间失败，将禁止 Broker 退出 Application：%s",
            snapshot_error,
        )
        return None


def process_has_top_level_windows(process_id: int) -> bool | None:
    """确认目标 PID 是否仍拥有任意顶层窗口；枚举失败时返回 None。"""
    try:
        import win32gui
        import win32process

        found = False

        def collect(hwnd: int, _extra: object) -> bool:
            nonlocal found
            if found or not bool(win32gui.IsWindow(hwnd)):
                return True
            _, window_process_id = win32process.GetWindowThreadProcessId(hwnd)
            if int(window_process_id) == int(process_id):
                found = True
            return True

        win32gui.EnumWindows(collect, None)
        return found
    except Exception as window_error:
        logger.warning(
            "无法确认 PowerPoint PID=%d 是否仍有外部窗口，将保留该进程：%s",
            process_id,
            window_error,
        )
        return None


def terminate_powerpoint_process(process_id: int, expected_created_at: float) -> bool:
    """仅在 PID、进程名和创建时间精确匹配时终止 POWERPNT.EXE。"""
    if process_id <= 0 or expected_created_at <= 0:
        return False
    try:
        import psutil

        process = psutil.Process(process_id)
        actual_name = str(process.name() or "").casefold()
        actual_created_at = float(process.create_time())
        if actual_name != "powerpnt.exe" or not math.isclose(
            actual_created_at,
            expected_created_at,
            rel_tol=0.0,
            abs_tol=0.01,
        ):
            logger.warning(
                "拒绝终止身份不匹配的 PowerPoint 进程：pid=%d, "
                "expected_created_at=%.6f, actual_name=%s, actual_created_at=%.6f",
                process_id,
                expected_created_at,
                actual_name,
                actual_created_at,
            )
            return False
        process.kill()
        process.wait(timeout=5.0)
        return True
    except Exception as terminate_error:
        logger.warning(
            "精确终止 Broker 自有 PowerPoint 进程失败：pid=%d, created_at=%.6f, error=%s",
            process_id,
            expected_created_at,
            terminate_error,
        )
        return False


def resolve_powerpoint_process_identity(
    process_id: int,
    before: Mapping[int, float] | set[int] | None,
    after: Mapping[int, float] | set[int] | None,
) -> tuple[int, float]:
    """优先采用 HWND PID，否则只接受 DispatchEx 前后唯一新增进程。"""
    normalized_pid = max(0, int(process_id))
    if normalized_pid > 0:
        return normalized_pid, _snapshot_creation_time(after, normalized_pid)
    if before is None or after is None:
        return 0, 0.0

    new_process_ids = sorted(set(after) - set(before))
    if len(new_process_ids) > 1:
        candidates = ", ".join(
            f"pid={candidate_pid}, created_at="
            f"{_snapshot_creation_time(after, candidate_pid):.6f}"
            for candidate_pid in new_process_ids
        )
        raise RuntimeError(
            "DispatchEx 后出现多个新增 PowerPoint 进程，拒绝猜测 Application 归属："
            f"{candidates}"
        )
    if not new_process_ids:
        return 0, 0.0
    selected_pid = new_process_ids[0]
    return selected_pid, _snapshot_creation_time(after, selected_pid)


def _snapshot_creation_time(
    snapshot: Mapping[int, float] | set[int] | None,
    process_id: int,
) -> float:
    if not isinstance(snapshot, Mapping):
        return 0.0
    return max(0.0, float(snapshot.get(process_id, 0.0) or 0.0))


def owner_token(owner: str) -> int:
    """把跨进程字符串 owner 转成可写入 Win32 Property 的非零整数。"""
    return zlib.crc32(owner.encode("utf-8")) or 1


def same_path(first_path: str, second_path: str) -> bool:
    """按 Windows 大小写语义判断两个文件路径是否指向同一目标。"""
    first = str(Path(first_path).resolve(strict=False)).casefold()
    second = str(Path(second_path).resolve(strict=False)).casefold()
    return first == second


def is_transient_com_error(error: BaseException) -> bool:
    """只识别 RPC_E_CALL_REJECTED / RPC_E_SERVERCALL_RETRYLATER。"""
    current_error: BaseException | None = error
    visited: set[int] = set()
    while current_error is not None and id(current_error) not in visited:
        visited.add(id(current_error))
        candidates: list[object] = [getattr(current_error, "hresult", None)]
        candidates.extend(getattr(current_error, "args", ()))
        for candidate in _flatten_error_candidates(candidates):
            try:
                hresult = int(candidate) & 0xFFFFFFFF
            except (TypeError, ValueError, OverflowError):
                continue
            if hresult in _TRANSIENT_HRESULTS:
                return True
        current_error = current_error.__cause__ or current_error.__context__
    return False


def is_released_com_object_error(error: BaseException) -> bool:
    """识别 RPC_E_DISCONNECTED / CO_E_OBJNOTCONNECTED。"""
    current_error: BaseException | None = error
    visited: set[int] = set()
    while current_error is not None and id(current_error) not in visited:
        visited.add(id(current_error))
        candidates: list[object] = [getattr(current_error, "hresult", None)]
        candidates.extend(getattr(current_error, "args", ()))
        for candidate in _flatten_error_candidates(candidates):
            try:
                hresult = int(candidate) & 0xFFFFFFFF
            except (TypeError, ValueError, OverflowError):
                continue
            if hresult in _RELEASED_OBJECT_HRESULTS:
                return True
        current_error = current_error.__cause__ or current_error.__context__
    return False


def com_error_hresult(error: BaseException) -> int | None:
    """从 COM 异常及其异常链提取首个 HRESULT，并归一为无符号值。"""
    current_error: BaseException | None = error
    visited: set[int] = set()
    while current_error is not None and id(current_error) not in visited:
        visited.add(id(current_error))
        candidates: list[object] = [getattr(current_error, "hresult", None)]
        candidates.extend(getattr(current_error, "args", ()))
        for candidate in _flatten_error_candidates(candidates):
            try:
                return int(candidate) & 0xFFFFFFFF
            except (TypeError, ValueError, OverflowError):
                continue
        current_error = current_error.__cause__ or current_error.__context__
    return None


def _flatten_error_candidates(values: object) -> list[object]:
    """展开 pywintypes.com_error 的嵌套 excepinfo，保留 HRESULT 标量。"""
    flattened: list[object] = []

    def collect(value: object) -> None:
        if isinstance(value, (tuple, list)):
            for nested_value in value:
                collect(nested_value)
            return
        flattened.append(value)

    collect(values)
    return flattened


__all__ = [
    "com_error_hresult",
    "dispatch_powerpoint",
    "is_released_com_object_error",
    "is_transient_com_error",
    "owner_token",
    "read_powerpoint_process_id",
    "process_has_top_level_windows",
    "resolve_powerpoint_process_identity",
    "same_path",
    "snapshot_powerpoint_process_ids",
    "snapshot_powerpoint_processes",
    "terminate_powerpoint_process",
]
