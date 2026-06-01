#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
LibreOffice PPT 预热 bridge 复用策略测试。
@Project : SCP-cv
@File : test_ppt_libreoffice_preheat_reuse.py
@Author : Qintsg
@Date : 2026-05-30
'''
from __future__ import annotations

from pytest import MonkeyPatch

from scp_cv.player.adapters import ppt_libreoffice
from scp_cv.player.adapters.ppt_libreoffice import LibreOfficePptSourceAdapter


class _UsedBridgeStub:
    """记录释放方式的 LibreOffice bridge 替身。"""

    def __init__(self) -> None:
        """
        初始化调用记录。
        :return: None
        """
        self.closed = False
        self.close_document_called = False

    def close_document(self) -> dict[str, object]:
        """
        记录仅关闭文档的调用。
        :return: 空闲状态
        """
        self.close_document_called = True
        return {"playback_state": "idle"}

    def close(self) -> None:
        """
        记录完整释放 bridge。
        :return: None
        """
        self.closed = True


class _PreheatPoolStub:
    """记录 bridge 是否被归还预热池。"""

    def __init__(self) -> None:
        """
        初始化归还记录。
        :return: None
        """
        self.returned_bridges: list[object] = []

    def return_libreoffice_bridge(self, bridge: object) -> None:
        """
        记录归还的 bridge。
        :param bridge: LibreOffice bridge
        :return: None
        """
        self.returned_bridges.append(bridge)


class _BridgeClientStub:
    """用于 isinstance 命中的 LibreOfficeBridgeClient 替身。"""


class _TakeBridgePoolStub:
    """记录文件级 bridge 认领参数的预热池替身。"""

    def __init__(self, bridge: object) -> None:
        """
        初始化 bridge 替身。
        :param bridge: 待返回的 bridge
        :return: None
        """
        self.bridge = bridge
        self.take_calls: list[tuple[int, str]] = []

    def take_libreoffice_bridge(self, source_id: int = 0, uri: str = "") -> object:
        """
        记录认领参数并返回 bridge。
        :param source_id: 媒体源 ID
        :param uri: PPT 文件路径
        :return: bridge 替身
        """
        self.take_calls.append((source_id, uri))
        return self.bridge


def test_close_discards_used_preheated_bridge_instead_of_returning_it() -> None:
    """前台放映使用过的 bridge 不应归还池中立刻复用。"""
    bridge = _UsedBridgeStub()
    pool = _PreheatPoolStub()
    adapter = LibreOfficePptSourceAdapter()
    adapter._bridge = bridge
    adapter._using_preheated_bridge = True
    adapter._preheat_pool = pool

    adapter.close()

    assert bridge.closed is True
    assert bridge.close_document_called is False
    assert pool.returned_bridges == []


def test_take_preheated_bridge_uses_source_context(monkeypatch: MonkeyPatch) -> None:
    """LibreOffice 适配器应按 source_id+uri 精确认领文件级 bridge。"""
    monkeypatch.setattr(ppt_libreoffice, "LibreOfficeBridgeClient", _BridgeClientStub)
    bridge = _BridgeClientStub()
    pool = _TakeBridgePoolStub(bridge)
    adapter = LibreOfficePptSourceAdapter()

    adapter.set_preheat_context(16, True, pool)
    adapter._file_path = "C:/demo/source.pptx"
    taken = adapter._take_preheated_bridge()

    assert taken is bridge
    assert pool.take_calls == [(16, "C:/demo/source.pptx")]
    assert adapter._using_preheated_bridge is True
