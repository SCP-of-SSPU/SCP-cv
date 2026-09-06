#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PowerPoint 进程识别辅助函数。
@Project : SCP-cv
@File : ppt_process.py
@Author : Qintsg
@Date : 2026-05-28
'''
from __future__ import annotations

import logging
import threading
from collections.abc import Iterable

logger = logging.getLogger(__name__)

# 由本系统拉起的 PowerPoint 进程 ID，播放器退出时用于残留进程兜底清理。
_SPAWNED_PPT_PROCESS_IDS: set[int] = set()
_SPAWNED_PPT_PROCESS_LOCK = threading.Lock()


def read_ppt_app_process_id(
    ppt_app: object | None,
    active_com_prog_id: str,
    existing_process_ids: set[int] | None = None,
) -> int:
    """
    从 PowerPoint 应用主窗口读取进程 ID。

    :param ppt_app: PowerPoint Application COM 对象
    :param active_com_prog_id: 当前成功连接的 COM ProgID
    :param existing_process_ids: 创建 COM 前已有的候选进程 ID
    :returns: 进程 ID；读取失败返回 0
    """
    if ppt_app is None:
        return 0
    app_hwnd = _read_app_hwnd(ppt_app)
    if app_hwnd:
        process_id = _process_id_from_hwnd(app_hwnd)
        if process_id:
            return process_id
    new_process_ids = snapshot_candidate_process_ids(active_com_prog_id) - (existing_process_ids or set())
    if len(new_process_ids) == 1:
        return next(iter(new_process_ids))
    return 0


def snapshot_candidate_process_ids(active_com_prog_id: str) -> set[int]:
    """
    获取当前 PowerPoint 后端候选进程 ID。

    :param active_com_prog_id: 当前 COM ProgID
    :returns: 进程 ID 集合
    """
    process_names = candidate_process_names(active_com_prog_id)
    return _snapshot_process_ids(process_names)


def snapshot_candidate_process_ids_for_prog_ids(
    com_prog_ids: Iterable[str],
    active_com_prog_id: str = "",
) -> set[int]:
    """
    按当前 COM 候选 ProgID 获取 PowerPoint 后端候选进程 ID。

    :param com_prog_ids: 当前适配器可尝试的 COM ProgID 集合
    :param active_com_prog_id: 已确认可用的 COM ProgID；为空时回退到候选集合
    :returns: 进程 ID 集合
    """
    process_names: set[str] = set()
    process_names.update(candidate_process_names(active_com_prog_id))
    for prog_id in com_prog_ids:
        process_names.update(candidate_process_names(prog_id))
    return _snapshot_process_ids(process_names)


def _snapshot_process_ids(process_names: set[str]) -> set[int]:
    """
    按进程名读取当前系统中的候选进程 ID。

    :param process_names: 小写进程名集合
    :returns: 进程 ID 集合
    """
    if not process_names:
        return set()
    try:
        import psutil
    except Exception:
        return set()
    process_ids: set[int] = set()
    for process in psutil.process_iter(["name"]):
        process_name = str(process.info.get("name") or "").lower()
        if process_name in process_names:
            process_ids.add(int(process.pid))
    return process_ids


def candidate_process_names(active_com_prog_id: str) -> set[str]:
    """
    根据当前 COM ProgID 推断 PowerPoint 进程名。

    :param active_com_prog_id: 当前 COM ProgID
    :returns: 小写进程名集合
    """
    lowered_prog_id = active_com_prog_id.lower()
    if "powerpoint" in lowered_prog_id:
        return {"powerpnt.exe"}
    return set()


def read_ppt_app_hwnd(ppt_app: object) -> int:
    """
    读取 PowerPoint Application 主窗口 HWND。

    :param ppt_app: PowerPoint Application COM 对象
    :returns: HWND；读取失败返回 0
    """
    if ppt_app is None:
        return 0
    return _read_app_hwnd(ppt_app)


def record_spawned_ppt_process(process_id: int) -> None:
    """
    记录由本系统拉起的 PowerPoint 进程。

    :param process_id: PowerPoint 进程 ID
    :returns: None
    """
    if process_id <= 0:
        return
    with _SPAWNED_PPT_PROCESS_LOCK:
        _SPAWNED_PPT_PROCESS_IDS.add(int(process_id))


def forget_spawned_ppt_process(process_id: int) -> None:
    """
    移除已记录的 PowerPoint 进程。

    :param process_id: PowerPoint 进程 ID
    :returns: None
    """
    with _SPAWNED_PPT_PROCESS_LOCK:
        _SPAWNED_PPT_PROCESS_IDS.discard(int(process_id))


def spawned_ppt_process_ids() -> set[int]:
    """
    获取当前记录的本系统拉起的 PowerPoint 进程 ID 快照。

    :returns: 进程 ID 集合副本
    """
    with _SPAWNED_PPT_PROCESS_LOCK:
        return set(_SPAWNED_PPT_PROCESS_IDS)


def terminate_spawned_ppt_processes(grace_seconds: float = 3.0) -> list[int]:
    """
    清理本系统拉起后仍残留的 PowerPoint 进程。
    带可见顶层窗口的进程视为已被用户接管，跳过清理。

    :param grace_seconds: terminate 后等待进程退出的秒数
    :returns: 实际被终止的进程 ID 列表
    """
    try:
        import psutil
    except Exception:
        return []

    terminated: list[int] = []
    for process_id in spawned_ppt_process_ids():
        try:
            process = psutil.Process(process_id)
            process_name = str(process.name() or "").lower()
        except Exception:
            forget_spawned_ppt_process(process_id)
            continue
        if process_name != "powerpnt.exe":
            forget_spawned_ppt_process(process_id)
            continue
        if _has_visible_top_level_window(process_id):
            logger.info("PowerPoint 进程 %d 存在可见窗口，跳过残留清理", process_id)
            continue
        try:
            process.terminate()
            process.wait(timeout=max(0.5, grace_seconds))
        except Exception:
            try:
                process.kill()
            except Exception:
                logger.warning("无法终止残留 PowerPoint 进程：%d", process_id)
                continue
        terminated.append(process_id)
        forget_spawned_ppt_process(process_id)
        logger.info("已清理残留 PowerPoint 进程：%d", process_id)
    return terminated


def _has_visible_top_level_window(process_id: int) -> bool:
    """
    判断进程是否拥有可见顶层窗口。

    :param process_id: 目标进程 ID
    :returns: True 表示存在可见窗口；Win32 不可用时按 True 处理以保守跳过清理
    """
    try:
        import win32gui
        import win32process
    except Exception:
        return True

    found_visible = {"value": False}

    def enum_callback(hwnd: int, _extra: object) -> bool:
        try:
            if not win32gui.IsWindowVisible(hwnd):
                return True
            _, window_pid = win32process.GetWindowThreadProcessId(hwnd)
            if int(window_pid) == int(process_id):
                found_visible["value"] = True
                return False
        except Exception:
            return True
        return True

    try:
        win32gui.EnumWindows(enum_callback, None)
    except Exception:
        # EnumWindows 在回调返回 False 终止枚举时会抛错，忽略即可
        pass
    return found_visible["value"]


def _read_app_hwnd(ppt_app: object) -> int:
    """
    读取 Office Application 主窗口 HWND。

    :param ppt_app: PowerPoint Application COM 对象
    :returns: HWND；读取失败返回 0
    """
    for attr_name in ("HWND", "Hwnd", "hwnd"):
        try:
            app_hwnd = int(getattr(ppt_app, attr_name) or 0)
        except Exception:
            app_hwnd = 0
        if app_hwnd:
            return app_hwnd
    return 0


def _process_id_from_hwnd(app_hwnd: int) -> int:
    """
    通过 HWND 读取进程 ID。

    :param app_hwnd: 应用主窗口 HWND
    :returns: 进程 ID；读取失败返回 0
    """
    try:
        import win32process

        _, process_id = win32process.GetWindowThreadProcessId(app_hwnd)
    except Exception:
        return 0
    return int(process_id or 0)


__all__ = [
    "candidate_process_names",
    "forget_spawned_ppt_process",
    "read_ppt_app_hwnd",
    "read_ppt_app_process_id",
    "record_spawned_ppt_process",
    "snapshot_candidate_process_ids",
    "snapshot_candidate_process_ids_for_prog_ids",
    "spawned_ppt_process_ids",
    "terminate_spawned_ppt_processes",
]
