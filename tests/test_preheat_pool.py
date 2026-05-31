#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
播放器统一预热池测试，覆盖 LibreOffice bridge 生命周期保护。
@Project : SCP-cv
@File : test_preheat_pool.py
@Author : Qintsg
@Date : 2026-05-30
'''
from __future__ import annotations

from pytest import MonkeyPatch

from scp_cv.player import preheat_pool
from scp_cv.player.preheat_pool import PlayerPreheatPool


class _BridgeStub:
    """记录关闭调用的 LibreOffice bridge 替身。"""

    def __init__(self) -> None:
        """
        初始化关闭记录。
        :return: None
        """
        self.closed = False

    def close(self) -> None:
        """
        标记 bridge 已关闭。
        :return: None
        """
        self.closed = True


def test_take_libreoffice_bridge_discards_expired_bridge(monkeypatch: MonkeyPatch) -> None:
    """过期的 LibreOffice 预热 bridge 不应被前台打开复用。"""
    bridge = _BridgeStub()
    pool = object.__new__(PlayerPreheatPool)
    pool._libreoffice_bridge = bridge
    pool._libreoffice_bridge_ready_at = 20.0
    monkeypatch.setattr(preheat_pool.time, "monotonic", lambda: 100.1)

    taken = pool.take_libreoffice_bridge()

    assert taken is None
    assert bridge.closed is True
    assert pool._libreoffice_bridge is None
    assert pool._libreoffice_bridge_ready_at == 0.0


def test_take_libreoffice_bridge_returns_fresh_bridge(monkeypatch: MonkeyPatch) -> None:
    """未过期的 LibreOffice 预热 bridge 仍应被前台打开认领。"""
    bridge = _BridgeStub()
    pool = object.__new__(PlayerPreheatPool)
    pool._libreoffice_bridge = bridge
    pool._libreoffice_bridge_ready_at = 50.0
    monkeypatch.setattr(preheat_pool.time, "monotonic", lambda: 100.0)

    taken = pool.take_libreoffice_bridge()

    assert taken is bridge
    assert bridge.closed is False
    assert pool._libreoffice_bridge is None
    assert pool._libreoffice_bridge_ready_at == 0.0
