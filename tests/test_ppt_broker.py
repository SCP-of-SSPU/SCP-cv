#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PowerPoint Broker 公共接口测试。
@Project : SCP-cv
@File : test_ppt_broker.py
@Author : Qintsg
@Date : 2026-07-11
'''
from __future__ import annotations

from collections.abc import Callable

from scp_cv.player.ppt_broker import (
    InMemoryPptBroker,
    PptBrokerEngine,
    PptCommand,
    PptCommandRequest,
    PptOpenRequest,
    PptSessionKey,
)
from scp_cv.player.ppt_broker.powerpoint import PowerPointComBackend
from scp_cv.player.ppt_broker.windows import SystemWindowPort


class _FakeView:
    """最小 PowerPoint SlideShowView 替身。"""

    State = 1
    CurrentShowPosition = 2

    def Exit(self) -> None:
        self.State = 5

    def GotoSlide(self, slide_index: int, *_args: object) -> None:
        self.CurrentShowPosition = slide_index


class _FakeSlideShowWindow:
    """HWND 以 pywin32 可调用成员形式暴露的替身。"""

    def __init__(self, signed_hwnd: int) -> None:
        self._signed_hwnd = signed_hwnd
        self.View = _FakeView()

    def HWND(self) -> int:
        return self._signed_hwnd


class _FakeSlideShowSettings:
    """记录窗口化放映设置并返回放映窗口。"""

    def __init__(self, slideshow_window: _FakeSlideShowWindow) -> None:
        self._slideshow_window = slideshow_window
        self.ShowType = 0
        self.StartingSlide = 1
        self.EndingSlide = 1
        self.ShowPresenterView = True

    def Run(self) -> _FakeSlideShowWindow:
        self._slideshow_window.View.CurrentShowPosition = self.StartingSlide
        return self._slideshow_window


class _FakePresentation:
    """最小 Presentation 替身。"""

    def __init__(self, slideshow_window: _FakeSlideShowWindow) -> None:
        self.Saved = False
        self.Slides = type("_Slides", (), {"Count": 12})()
        self.SlideShowSettings = _FakeSlideShowSettings(slideshow_window)

    def Close(self, *_args: object) -> None:
        return


class _FakePresentations:
    """返回同一测试 Presentation。"""

    Count = 0

    def __init__(self, presentation: _FakePresentation) -> None:
        self._presentation = presentation

    def Open(self, *_args: object, **_kwargs: object) -> _FakePresentation:
        return self._presentation


class _FakePowerPoint:
    """最小 PowerPoint Application 替身。"""

    def __init__(self, presentation: _FakePresentation) -> None:
        self.Presentations = _FakePresentations(presentation)
        self.DisplayAlerts = 2

    def Quit(self) -> None:
        return


class _FakeWin32Gui:
    """覆盖放映窗口识别、嵌入和校验的 Win32 替身。"""

    def __init__(self, hwnd: int) -> None:
        self.hwnd = hwnd
        self.parents: dict[int, int] = {}
        self.styles: dict[tuple[int, int], int] = {}

    def EnumWindows(
        self,
        callback: Callable[[int, object], bool],
        extra: object,
    ) -> None:
        callback(self.hwnd, extra)

    def IsWindow(self, hwnd: int) -> bool:
        return hwnd == self.hwnd

    def IsWindowVisible(self, hwnd: int) -> bool:
        return hwnd == self.hwnd

    def GetClassName(self, _hwnd: int) -> str:
        return "screenClass"

    def GetWindowText(self, _hwnd: int) -> str:
        return "PowerPoint 幻灯片放映  - 示例"

    def GetParent(self, hwnd: int) -> int:
        return self.parents.get(hwnd, 0)

    def SetParent(self, hwnd: int, parent_hwnd: int) -> None:
        self.parents[hwnd] = parent_hwnd

    def GetWindowLong(self, hwnd: int, index: int) -> int:
        return self.styles.get((hwnd, index), 0x80000000)

    def SetWindowLong(self, hwnd: int, index: int, value: int) -> None:
        self.styles[(hwnd, index)] = value

    def GetClientRect(self, _hwnd: int) -> tuple[int, int, int, int]:
        return 0, 0, 960, 540

    def SetWindowPos(self, *_args: object) -> None:
        return

    def ShowWindow(self, *_args: object) -> None:
        return

    def PostMessage(self, *_args: object) -> None:
        return


class _FakeWin32Process:
    """把候选窗口固定归属到测试 PowerPoint PID。"""

    @staticmethod
    def GetWindowThreadProcessId(_hwnd: int) -> tuple[int, int]:
        return 1, 4242


def test_multiple_windows_keep_independent_slideshow_state() -> None:
    """同一 Broker 中的两个窗口应独立保存页码与放映状态。"""
    broker = InMemoryPptBroker()
    left = PptSessionKey(window_id=1, owner_token="player-left")
    right = PptSessionKey(window_id=2, owner_token="player-right")
    try:
        left_state = broker.open(
            PptOpenRequest(left, "C:/slides/left.pptx", 1001, start_slide=2)
        )
        right_state = broker.open(
            PptOpenRequest(right, "C:/slides/right.pptx", 1002, start_slide=4)
        )

        broker.command(PptCommandRequest(left, PptCommand.NEXT))

        assert left_state.current_slide == 2
        assert right_state.current_slide == 4
        assert broker.get_state(left).current_slide == 3
        assert broker.get_state(right).current_slide == 4
    finally:
        broker.shutdown()


def test_open_accepts_callable_signed_hwnd_and_chinese_slideshow_title() -> None:
    """Broker 应归一负数 HWND，并识别含双空格的中文放映标题。"""
    signed_hwnd = -268_435_455
    normalized_hwnd = signed_hwnd & 0xFFFFFFFF
    slideshow_window = _FakeSlideShowWindow(signed_hwnd)
    presentation = _FakePresentation(slideshow_window)
    fake_gui = _FakeWin32Gui(normalized_hwnd)
    backend = PowerPointComBackend(
        application_factory=lambda: _FakePowerPoint(presentation),
        process_id_reader=lambda _app: 4242,
        window_port=SystemWindowPort(fake_gui, _FakeWin32Process()),
        file_exists=lambda _uri: True,
    )
    broker = PptBrokerEngine(backend)
    session = PptSessionKey(1, "player-one")
    try:
        state = broker.open(
            PptOpenRequest(session, "C:/slides/demo.pptx", 7001, start_slide=2)
        )

        assert state.slideshow_hwnd == normalized_hwnd
        assert state.parent_hwnd == 7001
        assert state.current_slide == 2
        assert fake_gui.GetParent(normalized_hwnd) == 7001
    finally:
        broker.shutdown()


def test_stale_owner_cannot_close_replacement_session() -> None:
    """同一窗口换 owner 后，旧播放器的迟到 close 不得关闭新会话。"""
    broker = InMemoryPptBroker()
    stale = PptSessionKey(1, "old-player")
    current = PptSessionKey(1, "new-player")
    try:
        broker.open(PptOpenRequest(stale, "C:/slides/old.pptx", 1001))
        broker.open(
            PptOpenRequest(current, "C:/slides/new.pptx", 1001, start_slide=7)
        )

        broker.close(stale)

        assert broker.get_state(current).current_slide == 7
        assert broker.get_state(current).playback_state == "playing"
    finally:
        broker.shutdown()
