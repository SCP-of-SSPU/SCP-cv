#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PPT/WPS 进程识别辅助函数。
@Project : SCP-cv
@File : ppt_process.py
@Author : Qintsg
@Date : 2026-05-28
'''
from __future__ import annotations


def read_ppt_app_process_id(
    ppt_app: object | None,
    active_com_prog_id: str,
    existing_process_ids: set[int] | None = None,
) -> int:
    """
    从 PPT/WPS 应用主窗口读取进程 ID。

    :param ppt_app: PPT/WPS Application COM 对象
    :param active_com_prog_id: 当前成功连接的 COM ProgID
    :param existing_process_ids: 创建 COM 前已有的候选进程 ID
    :returns: 进程 ID；读取失败返回 0
    """
    if ppt_app is None:
        return 0
    app_hwnd = _read_app_hwnd(ppt_app)
    if not app_hwnd:
        return 0
    process_id = _process_id_from_hwnd(app_hwnd)
    if process_id:
        return process_id
    new_process_ids = snapshot_candidate_process_ids(active_com_prog_id) - (existing_process_ids or set())
    if len(new_process_ids) == 1:
        return next(iter(new_process_ids))
    return 0


def snapshot_candidate_process_ids(active_com_prog_id: str) -> set[int]:
    """
    获取当前 PPT/WPS 后端候选进程 ID。

    :param active_com_prog_id: 当前 COM ProgID
    :returns: 进程 ID 集合
    """
    process_names = candidate_process_names(active_com_prog_id)
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
    根据当前 COM ProgID 推断 PPT/WPS 进程名。

    :param active_com_prog_id: 当前 COM ProgID
    :returns: 小写进程名集合
    """
    lowered_prog_id = active_com_prog_id.lower()
    if "powerpoint" in lowered_prog_id:
        return {"powerpnt.exe"}
    if "wpp" in lowered_prog_id or "kwpp" in lowered_prog_id:
        return {"wpp.exe", "wps.exe"}
    return set()


def _read_app_hwnd(ppt_app: object) -> int:
    """
    读取 Office Application 主窗口 HWND。

    :param ppt_app: PPT/WPS Application COM 对象
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
    "read_ppt_app_process_id",
    "snapshot_candidate_process_ids",
]
