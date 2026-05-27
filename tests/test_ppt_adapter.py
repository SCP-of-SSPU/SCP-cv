#!/user/bin/env python
# -*- coding: UTF-8 -*-
"""
PPT 播放适配器单元测试，覆盖 PowerPoint COM 状态读取容错。
@Project : SCP-cv
@File : test_ppt_adapter.py
@Author : Qintsg
@Date : 2026-04-30
"""

from __future__ import annotations

from scp_cv.player.adapters.ppt import PptSourceAdapter
from scp_cv.player.adapters.ppt_constants import (
    PP_SLIDE_SHOW_RUNNING,
    PP_SLIDE_SHOW_WINDOW,
)
from scp_cv.player.adapters.ppt_media import candidate_media_shape_ids
from scp_cv.player.adapters.ppt_wps import WpsPptSourceAdapter
from scp_cv.player.adapters.ppt_window import configure_windowed_slideshow
from scp_cv.ppt_com import WPS_COM_PROG_IDS


class _PresentationStub:
    def __init__(self) -> None:
        self.Saved = False
        self.close_called = False
        self.close_args: tuple[object, ...] = ()

    def Close(self, *args: object) -> None:
        self.close_called = True
        self.close_args = args


class _SlideShowSettingsStub:
    def __init__(self) -> None:
        self.ShowType = 0
        self.StartingSlide = 0
        self.EndingSlide = 0
        self.run_called = False

    def Run(self) -> object:
        self.run_called = True
        return type("_SlideShowWindowStub", (), {"HWND": 0, "View": object()})()


class _PresentationWithSettingsStub(_PresentationStub):
    def __init__(self) -> None:
        super().__init__()
        self.SlideShowSettings = _SlideShowSettingsStub()
        self.Slides = type("_SlidesStub", (), {"Count": 5})()


class _PptAppStub:
    def __init__(self) -> None:
        self.DisplayAlerts = 2
        self.quit_called = False

    def Quit(self) -> None:
        self.quit_called = True


class _Win32ComClientStub:
    """可控的 win32com.client 替身。"""

    def __init__(self) -> None:
        """
        初始化调用记录。
        :return: None
        """
        self.calls: list[str] = []
        self.app = object()

    def DispatchEx(self, prog_id: str) -> object:
        """
        记录 ProgID，并让第一个 WPS ProgID 失败以验证候选顺序。
        :param prog_id: COM ProgID
        :return: 应用替身
        """
        self.calls.append(prog_id)
        if prog_id == WPS_COM_PROG_IDS[0]:
            raise RuntimeError("KWPP unavailable")
        return self.app


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


class _ClickCapableSlideShowView:
    """模拟支持动画点击级导航的 PowerPoint/WPS 放映视图。"""

    def __init__(self, current_position: int = 1) -> None:
        """
        初始化放映视图替身。
        :param current_position: 当前页码
        :return: None
        """
        self.current_position = current_position
        self.next_click_called = False
        self.previous_click_called = False
        self.next_called = False
        self.previous_called = False

    @property
    def State(self) -> int:
        """
        返回放映中状态。
        :return: PowerPoint 放映中常量
        """
        return PP_SLIDE_SHOW_RUNNING

    @property
    def CurrentShowPosition(self) -> int:
        """
        返回当前页码。
        :return: 当前页码
        """
        return self.current_position

    def GotoNextClick(self) -> None:
        """
        记录下一动画点击调用。
        :return: None
        """
        self.next_click_called = True

    def GotoPreClick(self) -> None:
        """
        记录上一动画点击调用。
        :return: None
        """
        self.previous_click_called = True

    def Next(self) -> None:
        """
        记录页级下一页调用。
        :return: None
        """
        self.next_called = True
        self.current_position += 1

    def Previous(self) -> None:
        """
        记录页级上一页调用。
        :return: None
        """
        self.previous_called = True
        self.current_position -= 1


class _ClickCountingSlideShowView(_ClickCapableSlideShowView):
    """模拟可读取动画点击计数的 PowerPoint/WPS 放映视图。"""

    def __init__(
        self,
        current_position: int,
        click_count: int,
        click_index: int,
    ) -> None:
        """
        初始化可计数的放映视图替身。
        :param current_position: 当前页码
        :param click_count: 当前页总点击数
        :param click_index: 当前点击索引
        :return: None
        """
        super().__init__(current_position=current_position)
        self.click_count = click_count
        self.click_index = click_index

    def GetClickCount(self) -> int:
        """
        返回当前页动画点击总数。
        :return: 当前页动画点击总数
        """
        return self.click_count

    def GetClickIndex(self) -> int:
        """
        返回当前动画点击索引。
        :return: 当前动画点击索引
        """
        return self.click_index


class _ShapeStub:
    """
    PowerPoint shape 替身；只有 media=True 时才暴露 MediaFormat。
    """

    def __init__(self, shape_id: int, media: bool) -> None:
        """
        初始化 shape 替身。
        :param shape_id: PowerPoint shape id
        :param media: 是否模拟可控媒体对象
        :return: None
        """
        self.Id = shape_id
        if media:
            self.MediaFormat = object()


class _ShapesStub:
    """按 1-based 序号返回 shape 的集合替身。"""

    def __init__(self, shapes: list[_ShapeStub]) -> None:
        """
        初始化 shape 集合替身。
        :param shapes: shape 替身列表
        :return: None
        """
        self._shapes = shapes
        self.Count = len(shapes)

    def __call__(self, shape_index: int) -> _ShapeStub:
        """
        返回指定 1-based 序号的 shape。
        :param shape_index: shape 序号
        :return: shape 替身
        """
        return self._shapes[shape_index - 1]


class _SlideStub:
    """当前页替身，包含 Shapes 集合。"""

    def __init__(self, shapes: list[_ShapeStub]) -> None:
        """
        初始化当前页替身。
        :param shapes: shape 替身列表
        :return: None
        """
        self.Shapes = _ShapesStub(shapes)


class _SlidesStub:
    """Slides 集合替身，记录请求页码。"""

    def __init__(self, slide: _SlideStub) -> None:
        """
        初始化 Slides 集合替身。
        :param slide: 当前页替身
        :return: None
        """
        self._slide = slide
        self.requested_positions: list[int] = []

    def __call__(self, slide_position: int) -> _SlideStub:
        """
        返回当前页替身并记录页码。
        :param slide_position: 请求页码
        :return: 当前页替身
        """
        self.requested_positions.append(slide_position)
        return self._slide


class _MediaLookupPresentationStub:
    """媒体 shape 查找用 presentation 替身。"""

    def __init__(self) -> None:
        self.Slides = _SlidesStub(
            _SlideStub(
                [
                    _ShapeStub(shape_id=11, media=True),
                    _ShapeStub(shape_id=12, media=False),
                    _ShapeStub(shape_id=13, media=True),
                ]
            )
        )


class _MediaLookupViewStub:
    """媒体 shape 查找用 slideshow view 替身。"""

    CurrentShowPosition = 4


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


def test_next_item_allows_navigation_when_state_unreadable_but_position_available() -> (
    None
):
    """State 不可读不应阻断下一页指令，避免前端显示 stopped 后无法翻页。"""
    slideshow_view = _StateFailingSlideShowView(current_position=2)
    adapter = PptSourceAdapter()
    adapter._slideshow_view = slideshow_view
    adapter._total_slides = 5

    adapter.next_item()

    assert slideshow_view.next_called is True
    assert adapter._last_slide_index == 3


def test_next_item_prefers_click_navigation_on_last_slide() -> None:
    """最后一页仍应优先下发下一动画点击，避免阻断末页动画。"""
    slideshow_view = _ClickCapableSlideShowView(current_position=5)
    adapter = PptSourceAdapter()
    adapter._slideshow_view = slideshow_view
    adapter._total_slides = 5

    adapter.next_item()

    assert slideshow_view.next_click_called is True
    assert slideshow_view.next_called is False
    assert adapter._last_slide_index == 5


def test_prev_item_prefers_click_navigation_on_first_slide() -> None:
    """第一页仍应优先下发上一动画点击，避免阻断页内动画回退。"""
    slideshow_view = _ClickCapableSlideShowView(current_position=1)
    adapter = PptSourceAdapter()
    adapter._slideshow_view = slideshow_view
    adapter._total_slides = 5

    adapter.prev_item()

    assert slideshow_view.previous_click_called is True
    assert slideshow_view.previous_called is False
    assert adapter._last_slide_index == 1


def test_next_item_keeps_last_slide_when_click_count_is_exhausted() -> None:
    """末页无剩余动画点击时不应越界推进导致放映结束。"""
    slideshow_view = _ClickCountingSlideShowView(
        current_position=5,
        click_count=2,
        click_index=2,
    )
    adapter = PptSourceAdapter()
    adapter._slideshow_view = slideshow_view
    adapter._total_slides = 5

    adapter.next_item()

    assert slideshow_view.next_click_called is False
    assert slideshow_view.next_called is False
    assert adapter._last_slide_index == 5


def test_prev_item_keeps_first_slide_when_click_index_is_zero() -> None:
    """首页无已播放动画点击时不应越界回退。"""
    slideshow_view = _ClickCountingSlideShowView(
        current_position=1,
        click_count=2,
        click_index=0,
    )
    adapter = PptSourceAdapter()
    adapter._slideshow_view = slideshow_view
    adapter._total_slides = 5

    adapter.prev_item()

    assert slideshow_view.previous_click_called is False
    assert slideshow_view.previous_called is False
    assert adapter._last_slide_index == 1


def test_mark_presentation_clean_sets_saved_flag() -> None:
    """关闭前应将演示文稿标记为已保存，避免 PowerPoint 请求保存。"""
    adapter = PptSourceAdapter()
    presentation = _PresentationStub()
    adapter._presentation = presentation

    adapter._mark_presentation_clean()

    assert presentation.Saved is True


def test_close_presentation_without_save_prefers_explicit_false() -> None:
    """关闭演示文稿时应显式传递不保存参数。"""
    adapter = PptSourceAdapter()
    presentation = _PresentationStub()
    adapter._presentation = presentation

    adapter._close_presentation_without_save()

    assert presentation.close_called is True
    assert presentation.close_args == (False,)


def test_start_slideshow_only_updates_slide_range() -> None:
    """启动放映时应只改页码范围，避免额外改写文稿级放映设置。"""
    adapter = PptSourceAdapter()
    presentation = _PresentationWithSettingsStub()
    adapter._presentation = presentation
    adapter._total_slides = 5

    adapter._start_slideshow(start_slide=3)

    assert presentation.SlideShowSettings.StartingSlide == 3
    assert presentation.SlideShowSettings.EndingSlide == 5
    assert presentation.SlideShowSettings.ShowType == PP_SLIDE_SHOW_WINDOW
    assert presentation.SlideShowSettings.run_called is True
    assert presentation.Saved is True


def test_configure_windowed_slideshow_sets_window_mode() -> None:
    """
    PPT 放映应使用窗口模式，避免多个全屏放映互相顶替。
    :return: None
    """
    settings = _SlideShowSettingsStub()

    returned_settings = configure_windowed_slideshow(
        settings, start_slide=9, total_slides=5
    )

    assert PP_SLIDE_SHOW_WINDOW == 2
    assert returned_settings is settings
    assert settings.ShowType == PP_SLIDE_SHOW_WINDOW
    assert settings.StartingSlide == 5
    assert settings.EndingSlide == 5


def test_candidate_media_shape_ids_prioritizes_selected_page_media() -> None:
    """
    指定媒体序号时，应优先尝试当前页对应媒体 shape。
    :return: None
    """
    presentation = _MediaLookupPresentationStub()
    slideshow_view = _MediaLookupViewStub()

    shape_ids = candidate_media_shape_ids(
        presentation,
        slideshow_view,
        media_id="999",
        media_index=2,
    )

    assert shape_ids == [11, 999, 11, 13]
    assert presentation.Slides.requested_positions == [4]


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


def test_wps_adapter_uses_wps_com_prog_id_candidates() -> None:
    """WPS 适配器应按 WPS ProgID 候选创建 COM 应用。"""
    adapter = WpsPptSourceAdapter()
    win32com_client = _Win32ComClientStub()

    app = adapter._dispatch_ppt_application(win32com_client)

    assert app is win32com_client.app
    assert win32com_client.calls == list(WPS_COM_PROG_IDS)
    assert adapter._active_com_prog_id == WPS_COM_PROG_IDS[1]
