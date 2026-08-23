#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PowerPoint 跨进程独占槽位，封装 Windows 命名互斥体与 POSIX 文件锁。
@Project : SCP-cv
@File : powerpoint_slot.py
@Author : Qintsg
@Date : 2026-08-23
'''
from __future__ import annotations

import os
import tempfile
import threading
import time
from pathlib import Path
from typing import BinaryIO


DEFAULT_POWERPOINT_SLOT_NAME = "Local\\SCP-cv-PowerPoint-Slot"
_LOCK_POLL_INTERVAL_SECONDS = 0.01
_LOCAL_LOCKS_GUARD = threading.Lock()
_LOCAL_LOCKS: dict[str, threading.Lock] = {}


class PowerPointSlotTimeout(TimeoutError):
    """等待其它播放器进程释放 PowerPoint 槽位超时。"""


class PowerPointSlot:
    """
    保证同一 Windows 桌面会话中只有一个 PowerPoint 放映持有者。

    Windows 使用命名互斥体，进程异常退出时由操作系统自动释放；其它平台使用
    文件锁作为开发和测试回退。槽位必须由取得它的同一执行线程释放。
    """

    def __init__(
        self,
        name: str = DEFAULT_POWERPOINT_SLOT_NAME,
        *,
        lock_path: Path | None = None,
    ) -> None:
        """
        初始化独占槽位。

        :param name: Windows 命名互斥体名称
        :param lock_path: POSIX 回退锁文件；默认位于系统临时目录
        :return: None
        """
        self._name = name
        safe_name = "".join(character if character.isalnum() else "-" for character in name)
        self._lock_path = lock_path or Path(tempfile.gettempdir()) / f"{safe_name}.lock"
        with _LOCAL_LOCKS_GUARD:
            self._local_lock = _LOCAL_LOCKS.setdefault(name, threading.Lock())
        self._local_lock_held = False
        self._windows_handle: object | None = None
        self._lock_file: BinaryIO | None = None

    def acquire(self, timeout_seconds: float) -> None:
        """
        在限定时间内取得 PowerPoint 独占槽位。

        :param timeout_seconds: 最长等待秒数
        :return: None
        :raises PowerPointSlotTimeout: 槽位在超时前未释放
        :raises RuntimeError: 当前实例已经持有槽位
        """
        if self._windows_handle is not None or self._lock_file is not None:
            raise RuntimeError("当前 PowerPoint 槽位实例已被持有")
        started_at = time.monotonic()
        if not self._local_lock.acquire(timeout=max(0.0, timeout_seconds)):
            raise PowerPointSlotTimeout(
                f"等待当前进程释放 PowerPoint 放映超时（{timeout_seconds:g} 秒）"
            )
        self._local_lock_held = True
        remaining_seconds = max(0.0, timeout_seconds - (time.monotonic() - started_at))
        try:
            if os.name == "nt":
                self._acquire_windows(remaining_seconds)
                return
            self._acquire_posix(remaining_seconds)
        except BaseException:
            self._local_lock_held = False
            self._local_lock.release()
            raise

    def release(self) -> None:
        """
        释放当前实例持有的槽位；未持有时保持幂等。

        :return: None
        """
        try:
            if self._windows_handle is not None:
                import win32api
                import win32event

                handle = self._windows_handle
                self._windows_handle = None
                try:
                    win32event.ReleaseMutex(handle)
                finally:
                    win32api.CloseHandle(handle)
            if self._lock_file is not None:
                import fcntl

                lock_file = self._lock_file
                self._lock_file = None
                try:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
                finally:
                    lock_file.close()
        finally:
            if self._local_lock_held:
                self._local_lock_held = False
                self._local_lock.release()

    def _acquire_windows(self, timeout_seconds: float) -> None:
        """
        使用 Windows 命名互斥体取得槽位。

        :param timeout_seconds: 最长等待秒数
        :return: None
        :raises PowerPointSlotTimeout: 等待超时
        """
        import win32api
        import win32event

        handle = win32event.CreateMutex(None, False, self._name)
        timeout_milliseconds = max(0, int(timeout_seconds * 1000))
        wait_result = win32event.WaitForSingleObject(handle, timeout_milliseconds)
        if wait_result in {win32event.WAIT_OBJECT_0, win32event.WAIT_ABANDONED}:
            self._windows_handle = handle
            return
        win32api.CloseHandle(handle)
        raise PowerPointSlotTimeout(
            f"等待其它窗口释放 PowerPoint 放映超时（{timeout_seconds:g} 秒）"
        )

    def _acquire_posix(self, timeout_seconds: float) -> None:
        """
        使用 POSIX 文件锁取得槽位。

        :param timeout_seconds: 最长等待秒数
        :return: None
        :raises PowerPointSlotTimeout: 等待超时
        """
        import fcntl

        self._lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock_file = self._lock_path.open("a+b")
        deadline = time.monotonic() + max(0.0, timeout_seconds)
        while True:
            try:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                self._lock_file = lock_file
                return
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    lock_file.close()
                    raise PowerPointSlotTimeout(
                        f"等待其它窗口释放 PowerPoint 放映超时（{timeout_seconds:g} 秒）"
                    )
                time.sleep(_LOCK_POLL_INTERVAL_SECONDS)


__all__ = [
    "DEFAULT_POWERPOINT_SLOT_NAME",
    "PowerPointSlot",
    "PowerPointSlotTimeout",
]
