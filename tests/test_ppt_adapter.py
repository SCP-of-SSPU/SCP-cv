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
from scp_cv.player.adapters.ppt_constants import PP_SLIDE_SHOW_WINDOW
from scp_cv.player.adapters.ppt_media import candidate_media_shape_ids
from scp_cv.player.adapters.ppt_window import configure_windowed_slideshow


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
