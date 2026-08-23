#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PowerPoint 跨进程独占槽位测试。
@Project : SCP-cv
@File : test_powerpoint_slot.py
@Author : Qintsg
@Date : 2026-08-23
'''
from __future__ import annotations

import threading
import uuid
from pathlib import Path

import pytest

from scp_cv.player.powerpoint_slot import PowerPointSlot, PowerPointSlotTimeout


def test_powerpoint_slot_rejects_concurrent_owner(tmp_path: Path) -> None:
    """
    一个执行线程持有全局槽位时，另一个执行线程必须在超时后失败。

    :param tmp_path: POSIX 回退实现使用的临时锁目录
    :return: None
    """
    slot_name = f"SCP-cv-test-{uuid.uuid4().hex}"
    lock_path = tmp_path / "powerpoint.lock"
    owner_slot = PowerPointSlot(slot_name, lock_path=lock_path)
    contender_slot = PowerPointSlot(slot_name, lock_path=lock_path)
    acquired = threading.Event()
    release_owner = threading.Event()

    def hold_slot() -> None:
        """在独立线程持有槽位，直到主线程完成竞争测试。"""
        owner_slot.acquire(timeout_seconds=1.0)
        acquired.set()
        release_owner.wait(timeout=2.0)
        owner_slot.release()

    owner_thread = threading.Thread(target=hold_slot, daemon=True)
    owner_thread.start()
    assert acquired.wait(timeout=1.0)

    try:
        with pytest.raises(PowerPointSlotTimeout):
            contender_slot.acquire(timeout_seconds=0.05)
    finally:
        release_owner.set()
        owner_thread.join(timeout=2.0)

    assert not owner_thread.is_alive()


def test_powerpoint_slot_is_not_reentrant_on_same_thread(tmp_path: Path) -> None:
    """
    同一 COM worker 线程中的第二个适配器也不能重复取得同名槽位。

    :param tmp_path: POSIX 回退实现使用的临时锁目录
    :return: None
    """
    slot_name = f"SCP-cv-test-{uuid.uuid4().hex}"
    lock_path = tmp_path / "powerpoint.lock"
    owner_slot = PowerPointSlot(slot_name, lock_path=lock_path)
    contender_slot = PowerPointSlot(slot_name, lock_path=lock_path)
    owner_slot.acquire(timeout_seconds=1.0)

    try:
        with pytest.raises(PowerPointSlotTimeout):
            contender_slot.acquire(timeout_seconds=0.01)
    finally:
        owner_slot.release()
