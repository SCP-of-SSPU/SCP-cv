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

from pytest import MonkeyPatch

from scp_cv.player.adapters import ppt
from scp_cv.player.adapters.ppt import PptSourceAdapter
from scp_cv.player.adapters.ppt_constants import (
    PP_SLIDE_SHOW_RUNNING,
    PP_SLIDE_SHOW_WINDOW,
)
from scp_cv.player.adapters.ppt_media import candidate_media_shape_ids
from scp_cv.player.adapters.ppt_window import configure_windowed_slideshow
from scp_cv.player.preheat_types import PreheatedPptApplication


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
        self.ShowPresenterView = True
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
        self.WindowState = 0
        self.quit_called = False

    def Quit(self) -> None:
        self.quit_called = True


class _PresentationsOpenStub:
    """记录 Presentations.Open 调用参数。"""

    def __init__(self) -> None:
        """
        初始化调用记录。
        :return: None
        """
        self.keyword_calls: list[dict[str, object]] = []

    def Open(self, _file_path: str, **kwargs: object) -> object:
        """
        模拟 PowerPoint Presentations.Open。
        :param _file_path: PPT 文件路径
        :param kwargs: 打开参数
        :return: 演示文稿替身
        """
        self.keyword_calls.append(kwargs)
        return _PresentationStub()


class _PptAppWithPresentationsStub:
    """带 Presentations 集合的 PPT 应用替身。"""

    def __init__(self) -> None:
        """
        初始化 PPT 应用替身。
        :return: None
        """
        self.Presentations = _PresentationsOpenStub()


class _ReturnedPptPoolStub:
    """记录 PowerPoint 应用归还预热池。"""

    def __init__(self) -> None:
        """
        初始化归还记录。
        :return: None
        """
        self.returned_items: list[object] = []

    def return_ppt_application(self, item: object) -> None:
        """
        记录归还的预热项。
        :param item: 预热项
        :return: None
        """
        self.returned_items.append(item)


class _Win32ComClientStub:
    """可控的 win32com.client 替身。"""

    def __init__(self) -> None:
        """
        初始化调用记录。
        :return: None
        """
        self.calls: list[str] = []
        self.failures: dict[str, int] = {"PowerPoint.Application": 3}
        self.app = object()

    def DispatchEx(self, prog_id: str) -> object:
        """
        记录 ProgID，并让第一个 PowerPoint ProgID 失败以验证候选顺序。
        :param prog_id: COM ProgID
        :return: 应用替身
        """
        self.calls.append(prog_id)
        remaining_failures = self.failures.get(prog_id, 0)
        if remaining_failures > 0:
            self.failures[prog_id] = remaining_failures - 1
            raise RuntimeError("PowerPoint unavailable")
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
    """模拟支持动画点击级导航的 PowerPoint 放映视图。"""

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
    """模拟可读取动画点击计数的 PowerPoint 放映视图。"""

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


class _ExitTrackingSlideShowView:
    """模拟可记录退出调用的放映视图。"""

    def __init__(self, current_position: int = 1) -> None:
        """
        初始化放映视图替身。
        :param current_position: 当前页码
        :return: None
        """
        self.current_position = current_position
        self.exit_called = False

    @property
    def CurrentShowPosition(self) -> int:
        """
        返回当前页码。
        :return: 当前页码
        """
        return self.current_position

    def Exit(self) -> None:
        """
        记录退出放映调用。
        :return: None
        """
        self.exit_called = True


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


def test_start_slideshow_raises_when_hwnd_is_missing(monkeypatch: MonkeyPatch) -> None:
    """启动放映时应只改页码范围，避免额外改写文稿级放映设置。"""
    adapter = PptSourceAdapter()
    presentation = _PresentationWithSettingsStub()
    adapter._presentation = presentation
    adapter._total_slides = 5
    find_calls: list[dict[str, object]] = []

    def fake_find_slideshow_hwnd(*_args: object, **kwargs: object) -> int:
        """
        记录 HWND 查找参数，避免单元测试依赖真实 Win32 桌面。
        :param _args: 位置参数
        :param kwargs: 关键字参数
        :return: 固定返回未找到
        """
        find_calls.append(kwargs)
        return 0

    monkeypatch.setattr(ppt, "find_slideshow_hwnd", fake_find_slideshow_hwnd)
    monkeypatch.setattr(ppt, "snapshot_slideshow_hwnds", lambda *_args, **_kwargs: {101})

    try:
        adapter._start_slideshow(start_slide=3)
    except RuntimeError as missing_hwnd_error:
        assert "放映窗口句柄" in str(missing_hwnd_error)
    else:
        raise AssertionError("missing HWND must raise")

    assert presentation.SlideShowSettings.StartingSlide == 3
    assert presentation.SlideShowSettings.EndingSlide == 5
    assert presentation.SlideShowSettings.ShowType == PP_SLIDE_SHOW_WINDOW
    assert presentation.SlideShowSettings.run_called is True
    assert presentation.Saved is True
    assert adapter._slideshow_view is None
    assert adapter._slideshow_window is None
    assert find_calls[0]["timeout_seconds"] == ppt._SLIDESHOW_HWND_TIMEOUT_SECONDS
    assert find_calls[0]["allow_existing_when_unique"] is False


def test_start_slideshow_embeds_window_into_pyside_container(monkeypatch: MonkeyPatch) -> None:
    """找到放映 HWND 后应嵌入 PySide 视频容器。"""
    adapter = PptSourceAdapter()
    presentation = _PresentationWithSettingsStub()
    calls: list[object] = []
    adapter._presentation = presentation
    adapter._total_slides = 5
    adapter._window_handle = 2001

    monkeypatch.setattr(ppt, "find_slideshow_hwnd", lambda *_args, **_kwargs: 909)
    monkeypatch.setattr(ppt, "embed_slideshow_window", lambda *args: calls.append(args) or (1920, 1080))

    adapter._start_slideshow(start_slide=2)

    assert adapter._ppt_hwnd == 909
    assert calls == [(909, 2001, adapter._embed_owner_token)]


def test_open_presentation_for_slideshow_uses_editable_untitled_copy() -> None:
    """PowerPoint 应以只读方式打开演示文稿，避免文件锁冲突。"""
    adapter = PptSourceAdapter()
    ppt_app = _PptAppWithPresentationsStub()
    adapter._ppt_app = ppt_app

    presentation = adapter._open_presentation_for_slideshow("demo.pptx")

    assert isinstance(presentation, _PresentationStub)
    assert ppt_app.Presentations.keyword_calls == [
        {"ReadOnly": True, "Untitled": False, "WithWindow": False},
    ]


def test_stop_closes_embedded_slideshow_window(
    monkeypatch: MonkeyPatch,
) -> None:
    """停止 PPT 时应退出 COM 放映并关闭嵌入式放映 HWND。"""
    from scp_cv.player.adapters import ppt_navigation

    adapter = PptSourceAdapter()
    slideshow_view = _ExitTrackingSlideShowView(current_position=3)
    adapter._slideshow_view = slideshow_view
    adapter._presentation = _PresentationStub()
    adapter._ppt_hwnd = 909
    adapter._total_slides = 5
    close_calls: list[tuple[int, int]] = []
    monkeypatch.setattr(
        ppt_navigation,
        "close_embedded_slideshow_window",
        lambda hwnd, owner_token=0: close_calls.append((hwnd, owner_token)),
    )

    adapter.stop()

    assert slideshow_view.exit_called is True
    assert close_calls == [(909, adapter._embed_owner_token)]
    assert adapter._ppt_hwnd == 0
    assert adapter._slideshow_view is None
    assert adapter._last_slide_index == 3


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
    assert settings.ShowPresenterView is False


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


def test_close_com_resources_quits_owned_powerpoint_app(
    monkeypatch: MonkeyPatch,
) -> None:
    """适配器自建的 PowerPoint 进程应在关闭时退出。"""
    adapter = PptSourceAdapter()
    presentation = _PresentationStub()
    ppt_app = _PptAppStub()
    slideshow_view = _ExitTrackingSlideShowView(current_position=3)
    close_calls: list[tuple[int, int]] = []
    adapter._presentation = presentation
    adapter._ppt_app = ppt_app
    adapter._owns_ppt_app = True
    adapter._slideshow_view = slideshow_view
    adapter._ppt_hwnd = 909

    monkeypatch.setattr(
        ppt,
        "close_embedded_slideshow_window",
        lambda hwnd, owner_token=0: close_calls.append((hwnd, owner_token)),
    )

    adapter._close_com_resources()

    assert slideshow_view.exit_called is True
    assert close_calls == [(909, adapter._embed_owner_token)]
    assert presentation.close_called is True
    assert ppt_app.quit_called is True
    assert adapter._ppt_app is None
    assert adapter._owns_ppt_app is False


def test_detach_for_fast_switch_hides_embedded_slideshow_window(
    monkeypatch: MonkeyPatch,
) -> None:
    """切离 PPT 前应先隐藏嵌入式子窗口，避免旧画面挡住新内容。"""
    adapter = PptSourceAdapter()
    adapter._ppt_hwnd = 909
    hide_calls: list[int] = []
    monkeypatch.setattr(ppt, "hide_embedded_slideshow_window", hide_calls.append)

    adapter.detach_for_fast_switch()

    assert hide_calls == [909]


def test_restore_after_failed_switch_shows_embedded_slideshow_window(
    monkeypatch: MonkeyPatch,
) -> None:
    """新源打开失败后应恢复旧 PPT 嵌入窗口。"""
    adapter = PptSourceAdapter()
    adapter._ppt_hwnd = 909
    adapter._window_handle = 2001
    show_calls: list[tuple[int, int]] = []
    monkeypatch.setattr(
        ppt,
        "show_embedded_slideshow_window",
        lambda *args: show_calls.append(args) or (1920, 1080),
    )

    adapter.restore_after_failed_switch()

    assert show_calls == [(909, 2001)]


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


def test_close_com_resources_retires_owned_app_instead_of_reusing_proxy(
    monkeypatch: MonkeyPatch,
) -> None:
    """启用 PPT 预热时，离场也必须退休当前 Application 代理。"""
    adapter = PptSourceAdapter()
    presentation = _PresentationStub()
    ppt_app = _PptAppStub()
    pool = _ReturnedPptPoolStub()
    adapter._presentation = presentation
    adapter._ppt_app = ppt_app
    adapter._owns_ppt_app = True
    adapter._preheat_enabled = True
    adapter._preheat_pool = pool
    adapter._active_com_prog_id = "PowerPoint.Application"
    adapter._ppt_hwnd = 909
    close_calls: list[tuple[int, int]] = []
    monkeypatch.setattr(
        ppt,
        "close_embedded_slideshow_window",
        lambda hwnd, owner_token=0: close_calls.append((hwnd, owner_token)),
    )

    adapter._close_com_resources()

    assert close_calls == [(909, adapter._embed_owner_token)]
    assert presentation.close_called is True
    assert ppt_app.quit_called is True
    assert pool.returned_items == []


def test_close_com_resources_drops_external_preheated_proxy_without_quitting() -> None:
    """外部 PowerPoint 提供的预热代理应退休，但不得退出用户进程。"""
    adapter = PptSourceAdapter()
    presentation = _PresentationStub()
    ppt_app = _PptAppStub()
    pool = _ReturnedPptPoolStub()
    adapter._presentation = presentation
    adapter._ppt_app = ppt_app
    adapter._preheat_enabled = True
    adapter._preheat_pool = pool
    adapter._preheated_app = PreheatedPptApplication(
        "powerpoint",
        ppt_app,
        "PowerPoint.Application",
        spawned_process=False,
    )

    adapter._close_com_resources()

    assert presentation.close_called is True
    assert ppt_app.quit_called is False
    assert pool.returned_items == []


def test_powerpoint_adapter_uses_powerpoint_com_prog_id_candidates() -> None:
    """PowerPoint 适配器应按 ProgID 候选创建 COM 应用。"""
    adapter = PptSourceAdapter()
    win32com_client = _Win32ComClientStub()
    adapter._com_prog_ids = ("PowerPoint.Application", "PowerPoint.Application.16")

    app = adapter._dispatch_ppt_application(win32com_client)

    assert app is win32com_client.app
    assert win32com_client.calls == [
        "PowerPoint.Application",
        "PowerPoint.Application",
        "PowerPoint.Application",
        "PowerPoint.Application.16",
    ]
    assert adapter._active_com_prog_id == "PowerPoint.Application.16"


def test_powerpoint_operation_retries_transient_failures(monkeypatch: MonkeyPatch) -> None:
    """PowerPoint 冷启动阶段的临时 COM 失败应按固定次数重试。"""
    from scp_cv.player.adapters import ppt_com_session

    adapter = PptSourceAdapter()
    attempts = {"count": 0}
    monkeypatch.setattr(ppt_com_session.time, "sleep", lambda _seconds: None)

    def flaky_operation() -> object:
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise RuntimeError("busy")
        return "ok"

    assert adapter._run_powerpoint_operation("测试操作", flaky_operation) == "ok"
    assert attempts["count"] == 3


class _RecordingComWorkerStub:
    """记录提交任务但不执行的 COM 工作线程替身。"""

    is_current_thread = False

    def __init__(self) -> None:
        """
        初始化提交记录。
        :return: None
        """
        self.submitted: list[str] = []

    def submit(self, description: str, fn: object, on_done: object = None) -> None:
        """
        仅记录任务描述，不执行任务体。
        :param description: 任务描述
        :param fn: 任务体
        :param on_done: 完成回调
        :return: None
        """
        self.submitted.append(description)


def test_close_com_resources_skips_quit_when_other_presentations_open() -> None:
    """PowerPoint 仍有其它演示文稿打开时不得退出应用（单实例进程被共享）。"""
    adapter = PptSourceAdapter()
    presentation = _PresentationStub()
    ppt_app = _PptAppStub()
    ppt_app.Presentations = type("_BusyPresentations", (), {"Count": 2})()
    adapter._presentation = presentation
    adapter._ppt_app = ppt_app
    adapter._owns_ppt_app = True

    adapter._close_com_resources()

    assert presentation.close_called is True
    assert ppt_app.quit_called is False
    assert adapter._ppt_app is None


def test_get_state_returns_cached_snapshot_when_worker_attached() -> None:
    """注入 worker 后 get_state 应即时返回缓存并调度后台刷新。"""
    adapter = PptSourceAdapter()
    worker = _RecordingComWorkerStub()
    adapter.set_com_worker(worker)
    adapter._mark_open()

    state = adapter.get_state()

    assert state.playback_state == "idle"
    assert worker.submitted == ["PowerPoint 刷新状态"]
    # 刷新在途时不应重复调度
    adapter.get_state()
    assert worker.submitted == ["PowerPoint 刷新状态"]


def test_navigation_commands_route_through_worker() -> None:
    """注入 worker 后导航与关闭指令应投递到工作线程而非内联执行 COM。"""
    adapter = PptSourceAdapter()
    worker = _RecordingComWorkerStub()
    adapter.set_com_worker(worker)
    adapter._slideshow_view = _ClickCapableSlideShowView()

    adapter.next_item()
    adapter.pause()
    adapter.close()

    assert worker.submitted == [
        "PowerPoint 下一动画/页",
        "PowerPoint 暂停放映",
        "PowerPoint 关闭",
    ]
    assert adapter.is_open is False


def test_open_async_reports_missing_file_via_callback() -> None:
    """open_async 对不存在文件应通过回调上报 FileNotFoundError 而不抛出。"""
    adapter = PptSourceAdapter()
    outcomes: list[object] = []

    adapter.open_async(
        "Z:/no/such/file.pptx",
        2001,
        on_finished=outcomes.append,
    )

    assert len(outcomes) == 1
    assert isinstance(outcomes[0], FileNotFoundError)
