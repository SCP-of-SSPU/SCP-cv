#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PowerPoint Broker 页面媒体 COM 瞬时重试测试。
@Project : SCP-cv
@File : test_ppt_broker_powerpoint_media.py
@Author : Qintsg
@Date : 2026-07-12
'''
from __future__ import annotations

import pytest

from scp_cv.player.ppt_broker import (
    PptBrokerEngine,
    PptCommand,
    PptCommandRequest,
    PptOpenRequest,
    PptSessionKey,
)
from scp_cv.player.ppt_broker.powerpoint import PowerPointComBackend


class _TransientComError(RuntimeError):
    """模拟 RPC_E_CALL_REJECTED。"""

    hresult = -2_147_418_111


class _SentinelPresentation:
    """无窗口、无放映的 Application sentinel 替身。"""

    Saved = False

    def Close(self, *_args: object) -> None:
        return


class _MediaPlayer:
    """可按动作暂时拒绝控制调用的 PowerPoint Player 替身。"""

    def __init__(self, transient_failures: int = 0) -> None:
        self.transient_failures = transient_failures
        self.action_attempts: dict[str, int] = {
            "play": 0,
            "pause": 0,
            "stop": 0,
        }

    def _run_action(self, action: str) -> None:
        self.action_attempts[action] += 1
        if self.transient_failures > 0:
            self.transient_failures -= 1
            raise _TransientComError("PowerPoint is busy")

    def Play(self) -> None:
        self._run_action("play")

    def Pause(self) -> None:
        self._run_action("pause")

    def Stop(self) -> None:
        self._run_action("stop")


class _MediaPlaybackView:
    """记录当前页读取和 Player 查找的 SlideShowView 替身。"""

    def __init__(
        self,
        player: _MediaPlayer,
        *,
        transient_lookup_failures: int = 0,
        transient_position_failures: int = 0,
        player_missing: bool = False,
    ) -> None:
        self.State = 1
        self._current_show_position = 1
        self.player = player
        self.transient_lookup_failures = transient_lookup_failures
        self.transient_position_failures = transient_position_failures
        self.player_missing = player_missing
        self.position_read_attempts = 0
        self.player_shape_ids: list[int] = []

    @property
    def CurrentShowPosition(self) -> int:
        self.position_read_attempts += 1
        if self.transient_position_failures > 0:
            self.transient_position_failures -= 1
            raise _TransientComError("PowerPoint is busy")
        return self._current_show_position

    @CurrentShowPosition.setter
    def CurrentShowPosition(self, value: int) -> None:
        self._current_show_position = int(value)

    def Player(self, shape_id: int) -> _MediaPlayer:
        self.player_shape_ids.append(shape_id)
        if self.transient_lookup_failures > 0:
            self.transient_lookup_failures -= 1
            raise _TransientComError("PowerPoint is busy")
        if self.player_missing:
            raise LookupError("media shape does not exist")
        return self.player

    def Exit(self) -> None:
        self.State = 5


class _MediaShape:
    """可在 MediaFormat 或 Id 读取时拒绝调用的 Shape 替身。"""

    def __init__(
        self,
        shape_id: int,
        *,
        transient_attribute: str = "",
        transient_failures: int = 0,
        is_media: bool = True,
    ) -> None:
        self._shape_id = shape_id
        self.transient_attribute = transient_attribute
        self.transient_failures = transient_failures
        self.is_media = is_media
        self.media_format_reads = 0
        self.id_reads = 0

    def _raise_transient_if_needed(self, attribute: str) -> None:
        if self.transient_attribute == attribute and self.transient_failures > 0:
            self.transient_failures -= 1
            raise _TransientComError("PowerPoint is busy")

    @property
    def MediaFormat(self) -> object:
        self.media_format_reads += 1
        self._raise_transient_if_needed("media_format")
        if not self.is_media:
            raise AttributeError("shape has no MediaFormat")
        return object()

    @property
    def Id(self) -> int:
        self.id_reads += 1
        self._raise_transient_if_needed("id")
        return self._shape_id


class _ShapeCollection:
    """按 PowerPoint 的 1-based 规则提供 Shape。"""

    def __init__(self, shapes: list[_MediaShape]) -> None:
        self._shapes = shapes
        self.Count = len(shapes)

    def __call__(self, shape_index: int) -> _MediaShape:
        return self._shapes[shape_index - 1]


class _Slide:
    """包含可枚举 Shape 的当前页替身。"""

    def __init__(self, shapes: list[_MediaShape]) -> None:
        self.Shapes = _ShapeCollection(shapes)


class _SlideCollection:
    """可暂时拒绝或确定性拒绝当前页解析的 Slides 替身。"""

    Count = 3

    def __init__(
        self,
        slide: _Slide | None = None,
        *,
        transient_failures: int = 0,
        slide_missing: bool = False,
    ) -> None:
        self.slide = slide
        self.transient_failures = transient_failures
        self.slide_missing = slide_missing
        self.call_attempts = 0

    def __call__(self, _slide_index: int) -> _Slide:
        self.call_attempts += 1
        if self.transient_failures > 0:
            self.transient_failures -= 1
            raise _TransientComError("PowerPoint is busy")
        if self.slide_missing or self.slide is None:
            raise LookupError("current slide does not exist")
        return self.slide


class _Presentation:
    """提供页面媒体测试所需放映入口的 Presentation 替身。"""

    def __init__(
        self,
        view: _MediaPlaybackView,
        slides: _SlideCollection,
    ) -> None:
        self.Name = "演示文稿1"
        self.Saved = False
        self.Slides = slides
        slideshow_window = type("_SlideShowWindow", (), {"View": view})()

        class _Settings:
            ShowType = 0
            RangeType = 1
            StartingSlide = 1
            EndingSlide = 3
            ShowPresenterView = True

            def Run(settings_self: object) -> object:
                return slideshow_window

        self.SlideShowSettings = _Settings()

    def Close(self, *_args: object) -> None:
        return


class _Application:
    """只返回一个指定 Presentation 的 PowerPoint Application 替身。"""

    def __init__(self, presentation: _Presentation) -> None:
        class _Presentations:
            Count = 0

            @staticmethod
            def Add(WithWindow: bool = False) -> _SentinelPresentation:
                assert WithWindow is False
                return _SentinelPresentation()

            def Open(
                presentations_self: object,
                *_args: object,
                **_kwargs: object,
            ) -> _Presentation:
                return presentation

        self.Presentations = _Presentations()
        self.DisplayAlerts = 2

    def Quit(self) -> None:
        return


class _WindowPort:
    """不依赖 Win32 的放映窗口端口。"""

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
        return 8001

    def embed(self, _hwnd: int, _parent_hwnd: int, _owner_token: int) -> tuple[int, int]:
        return 960, 540

    def hide(self, _hwnd: int) -> None:
        return

    def show(self, _hwnd: int, _parent_hwnd: int) -> None:
        return

    def close(self, _hwnd: int, _owner_token: int) -> None:
        return


def _build_broker(
    view: _MediaPlaybackView,
    slides: _SlideCollection | None = None,
) -> tuple[PptBrokerEngine, PptSessionKey]:
    """打开一个使用指定放映视图和 Slides 集合的公开 Broker 会话。"""
    presentation = _Presentation(
        view,
        slides or _SlideCollection(slide_missing=True),
    )
    application = _Application(presentation)
    backend = PowerPointComBackend(
        application_factory=lambda: application,
        process_id_reader=lambda _app: 4242,
        window_port=_WindowPort(),
        file_exists=lambda _uri: True,
        retry_delays=(0.0, 0.0),
    )
    broker = PptBrokerEngine(backend)
    session = PptSessionKey(1, "media-command")
    broker.open(PptOpenRequest(session, "C:/slides/source.pptx", 1001))
    return broker, session


def _media_command(session: PptSessionKey, *, media_id: str = "") -> PptCommandRequest:
    """创建页面媒体播放指令。"""
    return PptCommandRequest(
        session,
        PptCommand.CONTROL_MEDIA,
        media_id=media_id,
        media_action="play",
        media_index=1 if not media_id else 0,
    )


def test_media_command_retries_transient_player_lookup_rejection() -> None:
    """Player(shape_id) 暂时拒绝后应由公开 Broker 指令重试并执行。"""
    player = _MediaPlayer()
    view = _MediaPlaybackView(player, transient_lookup_failures=2)
    broker, session = _build_broker(view)
    try:
        broker.command(_media_command(session, media_id="42"))

        assert view.player_shape_ids == [42, 42, 42]
        assert player.action_attempts["play"] == 1
    finally:
        broker.shutdown()


@pytest.mark.parametrize("media_action", ["play", "pause", "stop"])
def test_media_command_retries_transient_player_action_rejection(
    media_action: str,
) -> None:
    """Play/Pause/Stop 暂时拒绝后应统一有限重试并成功。"""
    player = _MediaPlayer(transient_failures=2)
    view = _MediaPlaybackView(player)
    broker, session = _build_broker(view)
    try:
        broker.command(
            PptCommandRequest(
                session,
                PptCommand.CONTROL_MEDIA,
                media_id="42",
                media_action=media_action,
            )
        )

        assert view.player_shape_ids == [42, 42, 42]
        assert player.action_attempts[media_action] == 3
    finally:
        broker.shutdown()


def test_media_command_keeps_missing_player_as_no_op() -> None:
    """确定性 Player 不存在仍应保持兼容 no-op，而不是命令失败。"""
    player = _MediaPlayer()
    view = _MediaPlaybackView(player, player_missing=True)
    broker, session = _build_broker(view)
    try:
        state = broker.command(_media_command(session, media_id="42"))

        assert state.playback_state == "playing"
        assert view.player_shape_ids == [42]
        assert player.action_attempts["play"] == 0
    finally:
        broker.shutdown()


@pytest.mark.parametrize("failure_stage", ["current_position", "slides"])
def test_media_command_retries_transient_current_slide_resolution(
    failure_stage: str,
) -> None:
    """当前页码或 Slides 暂时拒绝后应重试完整媒体控制。"""
    player = _MediaPlayer()
    view = _MediaPlaybackView(player)
    shape = _MediaShape(501)
    slides = _SlideCollection(
        _Slide([shape]),
        transient_failures=2 if failure_stage == "slides" else 0,
    )
    broker, session = _build_broker(view, slides)
    if failure_stage == "current_position":
        view.transient_position_failures = 2
        view.position_read_attempts = 0
    try:
        broker.command(_media_command(session))

        assert view.player_shape_ids == [501]
        assert player.action_attempts["play"] == 1
        if failure_stage == "current_position":
            assert view.position_read_attempts == 4
        else:
            assert slides.call_attempts == 3
    finally:
        broker.shutdown()


@pytest.mark.parametrize("transient_attribute", ["media_format", "id"])
def test_media_command_retries_transient_media_shape_inspection(
    transient_attribute: str,
) -> None:
    """MediaFormat 或 Id 暂时拒绝后应重试并找到同一媒体 Shape。"""
    player = _MediaPlayer()
    view = _MediaPlaybackView(player)
    shape = _MediaShape(
        501,
        transient_attribute=transient_attribute,
        transient_failures=2,
    )
    slides = _SlideCollection(_Slide([shape]))
    broker, session = _build_broker(view, slides)
    try:
        broker.command(_media_command(session))

        assert view.player_shape_ids == [501]
        assert shape.media_format_reads == 3
        assert shape.id_reads == (3 if transient_attribute == "id" else 1)
        assert player.action_attempts["play"] == 1
    finally:
        broker.shutdown()


def test_media_command_keeps_missing_current_slide_as_no_op() -> None:
    """确定性当前页缺失仍应保持 no-op，不触发 COM 重试。"""
    player = _MediaPlayer()
    view = _MediaPlaybackView(player)
    slides = _SlideCollection(slide_missing=True)
    broker, session = _build_broker(view, slides)
    try:
        state = broker.command(_media_command(session))

        assert state.playback_state == "playing"
        assert slides.call_attempts == 1
        assert view.player_shape_ids == []
        assert player.action_attempts["play"] == 0
    finally:
        broker.shutdown()


def test_media_command_skips_deterministic_non_media_shape() -> None:
    """确定性无 MediaFormat 的 Shape 应跳过并继续查找后续媒体。"""
    player = _MediaPlayer()
    view = _MediaPlaybackView(player)
    non_media_shape = _MediaShape(101, is_media=False)
    media_shape = _MediaShape(202)
    slides = _SlideCollection(_Slide([non_media_shape, media_shape]))
    broker, session = _build_broker(view, slides)
    try:
        broker.command(_media_command(session))

        assert view.player_shape_ids == [202]
        assert non_media_shape.media_format_reads == 1
        assert player.action_attempts["play"] == 1
    finally:
        broker.shutdown()
