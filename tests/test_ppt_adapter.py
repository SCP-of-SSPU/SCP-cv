#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PPT 播放适配器单元测试，覆盖 PowerPoint COM 状态读取容错。
@Project : SCP-cv
@File : test_ppt_adapter.py
@Author : Qintsg
@Date : 2026-04-30
'''
from __future__ import annotations

from scp_cv.player.adapters.ppt import PptSourceAdapter


class _StateFailingSlideShowView:
    """模拟 State 不可读但页码和翻页仍可用的 PowerPoint 放映视图。"""

    def __init__(self, current_position: int = 2) -> None:
        """
        初始化测试替身。
        :param current_position: 当前页码
        :return: None
        """
        self.current_position = current_position
        self.next_called = False

    @property
    def State(self) -> int:
        """
        模拟部分 PowerPoint 版本读取 State 抛出 COM 异常。
        :return: 不返回，固定抛出 RuntimeError
        """
        raise RuntimeError("State unavailable")

    @property
    def CurrentShowPosition(self) -> int:
        """
        返回当前页码。
        :return: 当前页码
        """
        return self.current_position

    def Next(self) -> None:
        """
        记录翻页调用并推进页码。
        :return: None
        """
        self.next_called = True
        self.current_position += 1


def test_get_state_keeps_playing_when_state_unreadable_but_position_available() -> None:
    """State 不可读但页码可读时，应保持 playing 而不是误报 stopped。"""
    adapter = PptSourceAdapter()
    adapter._slideshow_view = _StateFailingSlideShowView(current_position=2)
    adapter._presentation = object()
    adapter._total_slides = 5

    adapter_state = adapter.get_state()

    assert adapter_state.playback_state == "playing"
    assert adapter_state.current_slide == 2
    assert adapter._slideshow_view is not None


def test_next_item_allows_navigation_when_state_unreadable_but_position_available() -> None:
    """State 不可读不应阻断下一页指令，避免前端显示 stopped 后无法翻页。"""
    slideshow_view = _StateFailingSlideShowView(current_position=2)
    adapter = PptSourceAdapter()
    adapter._slideshow_view = slideshow_view
    adapter._total_slides = 5

    adapter.next_item()

    assert slideshow_view.next_called is True
    assert adapter._last_slide_index == 3
