#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PowerPoint Broker COM 后端测试共享替身。
@Project : SCP-cv
@File : ppt_broker_powerpoint_test_support.py
@Author : Qintsg
@Date : 2026-07-12
'''
from __future__ import annotations


class EmptyPowerPoint:
    """没有打开文档的 PowerPoint Application 替身。"""

    def __init__(self) -> None:
        self.Presentations = type("_Presentations", (), {"Count": 0})()
        self.DisplayAlerts = 2
        self.quit_called = False

    def Quit(self) -> None:
        self.quit_called = True


class TransientComError(RuntimeError):
    """模拟 RPC_E_CALL_REJECTED。"""

    hresult = -2_147_418_111


class SentinelPresentation:
    """无窗口、无放映的 Application sentinel 替身。"""

    Saved = False

    def Close(self, *_args: object) -> None:
        return


class AnimatedView:
    """记录首尾页动画点击接口调用的 SlideShowView。"""

    State = 1

    def __init__(self) -> None:
        self.CurrentShowPosition = 1
        self.next_clicks = 0
        self.previous_clicks = 0
        self.goto_slides: list[int] = []

    def GotoNextClick(self) -> None:
        self.next_clicks += 1

    def GotoPreClick(self) -> None:
        self.previous_clicks += 1

    def GotoSlide(self, slide_index: int, *_args: object) -> None:
        self.goto_slides.append(slide_index)
        self.CurrentShowPosition = slide_index

    def Exit(self) -> None:
        self.State = 5


class AnimatedPresentation:
    """带动画视图的 Presentation 替身。"""

    def __init__(self, view: AnimatedView | None = None) -> None:
        self.Saved = False
        self.saved_during_run: bool | None = None
        self.Slides = type("_Slides", (), {"Count": 3})()
        self.view = view or AnimatedView()
        slideshow_window = type("_SlideShowWindow", (), {"View": self.view})()

        class _Settings:
            ShowType = 0
            RangeType = 1
            StartingSlide = 1
            EndingSlide = 3
            ShowPresenterView = True

            def Run(settings_self: object) -> object:
                self.saved_during_run = self.Saved
                self.view.CurrentShowPosition = 1
                return slideshow_window

        self.SlideShowSettings = _Settings()

    def Close(self, *_args: object) -> None:
        return


class AnimatedPresentations:
    """每次 Open 创建独立的动画 Presentation。"""

    Count = 0

    def __init__(self) -> None:
        self.opened: list[AnimatedPresentation] = []

    @staticmethod
    def Add(WithWindow: bool = False) -> SentinelPresentation:
        assert WithWindow is False
        return SentinelPresentation()

    def Open(self, *_args: object, **_kwargs: object) -> AnimatedPresentation:
        presentation = AnimatedPresentation()
        self.opened.append(presentation)
        return presentation


class AnimatedPowerPoint:
    """支持多个动画 Presentation 的 Application 替身。"""

    def __init__(self) -> None:
        self.Presentations = AnimatedPresentations()
        self.DisplayAlerts = 2
        self.quit_called = False

    def Quit(self) -> None:
        self.quit_called = True


class WindowPort:
    """不依赖 Win32 的放映窗口 Adapter。"""

    def __init__(self) -> None:
        self.next_hwnd = 8000
        self.resize_calls: list[tuple[int, int]] = []
        self.expected_presentation_names: list[str] = []

    def snapshot(self, _process_id: int) -> dict[int, object]:
        return {}

    def resolve(
        self,
        _slideshow_window: object,
        _before: dict[int, object],
        _process_id: int,
        _forbidden_hwnds: object,
        expected_presentation_name: str = "",
    ) -> int:
        self.expected_presentation_names.append(expected_presentation_name)
        self.next_hwnd += 1
        return self.next_hwnd

    def embed(self, _hwnd: int, _parent_hwnd: int, _owner_token: int) -> tuple[int, int]:
        return 960, 540

    def hide(self, _hwnd: int) -> None:
        return

    def show(self, _hwnd: int, _parent_hwnd: int) -> None:
        return

    def resize(self, hwnd: int, parent_hwnd: int) -> tuple[int, int]:
        self.resize_calls.append((hwnd, parent_hwnd))
        return 960, 540

    def close(self, _hwnd: int, _owner_token: int) -> None:
        return


__all__ = [
    "AnimatedPowerPoint",
    "AnimatedPresentation",
    "AnimatedPresentations",
    "AnimatedView",
    "EmptyPowerPoint",
    "SentinelPresentation",
    "TransientComError",
    "WindowPort",
]
