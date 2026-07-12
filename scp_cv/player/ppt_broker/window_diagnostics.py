#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PowerPoint Broker 的 Win32 顶层窗口诊断枚举。
@Project : SCP-cv
@File : window_diagnostics.py
@Author : Qintsg
@Date : 2026-07-11
'''
from __future__ import annotations


def describe_process_windows(
    win32gui: object,
    win32process: object,
    process_id: int,
) -> list[str]:
    """枚举目标 PID 的顶层窗口原始信息，供严格认领失败时排查。"""
    diagnostics: list[str] = []

    def collect(hwnd: int, _extra: object) -> bool:
        try:
            _, window_process_id = win32process.GetWindowThreadProcessId(  # type: ignore[attr-defined]
                hwnd
            )
            if int(window_process_id) != int(process_id):
                return True
            diagnostics.append(
                f"HWND={int(hwnd)}, visible="
                f"{bool(win32gui.IsWindowVisible(hwnd))}, "  # type: ignore[attr-defined]
                f"class={str(win32gui.GetClassName(hwnd))!r}, "  # type: ignore[attr-defined]
                f"title={str(win32gui.GetWindowText(hwnd))!r}"  # type: ignore[attr-defined]
            )
        except Exception:
            return True
        return len(diagnostics) < 32

    try:
        win32gui.EnumWindows(collect, None)  # type: ignore[attr-defined]
    except Exception as diagnostic_error:
        return [f"枚举失败：{diagnostic_error}"]
    return diagnostics


__all__ = ["describe_process_windows"]
