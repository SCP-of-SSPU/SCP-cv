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


class _PresentationStub:
    def __init__(self) -> None:
        self.Saved = False
        self.close_called = False

    def Close(self) -> None:
        self.close_called = True


class _PptAppStub:
    def __init__(self) -> None:
        self.DisplayAlerts = 2
        self.quit_called = False

    def Quit(self) -> None:
        self.quit_called = True


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


def test_mark_presentation_clean_sets_saved_flag() -> None:
    """关闭前应将演示文稿标记为已保存，避免 PowerPoint 请求保存。"""
    adapter = PptSourceAdapter()
    presentation = _PresentationStub()
    adapter._presentation = presentation

    adapter._mark_presentation_clean()

    assert presentation.Saved is True


def test_close_com_resources_quits_owned_powerpoint_app() -> None:
    """适配器自建的 PowerPoint 进程应在关闭时退出。"""
    adapter = PptSourceAdapter()
    presentation = _PresentationStub()
    ppt_app = _PptAppStub()
    adapter._presentation = presentation
    adapter._ppt_app = ppt_app
    adapter._owns_ppt_app = True

    adapter._close_com_resources()

    assert presentation.close_called is True
    assert ppt_app.quit_called is True
    assert adapter._ppt_app is None
    assert adapter._owns_ppt_app is False


def test_close_com_resources_keeps_external_powerpoint_app_running() -> None:
    """外部 PowerPoint 进程不应被适配器误退出。"""
    adapter = PptSourceAdapter()
    presentation = _PresentationStub()
    ppt_app = _PptAppStub()
    adapter._presentation = presentation
    adapter._ppt_app = ppt_app
    adapter._owns_ppt_app = False

    adapter._close_com_resources()

    assert presentation.close_called is True
    assert ppt_app.quit_called is False
    assert adapter._ppt_app is None
    assert adapter._owns_ppt_app is False
