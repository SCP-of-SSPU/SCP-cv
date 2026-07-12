#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PowerPoint Broker 的确定性内存 Adapter，供测试和无 COM 调用方使用。
@Project : SCP-cv
@File : memory.py
@Author : Qintsg
@Date : 2026-07-11
'''
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from scp_cv.player.ppt_broker.contracts import (
    PptCommand,
    PptCommandRequest,
    PptExportResult,
    PptOpenRequest,
    PptPreheatRequest,
    PptShowExportRequest,
    PptSlideExportRequest,
    PptState,
)
from scp_cv.player.ppt_broker.engine import PptBrokerEngine


@dataclass(slots=True)
class _MemorySession:
    """内存 Adapter 的单窗口会话。"""

    parent_hwnd: int
    current_slide: int
    total_slides: int = 100
    playback_state: str = "playing"
    visible: bool = True
    slideshow_hwnd: int = 0


class _MemoryBackend:
    """不依赖 Office 的 PowerPoint 后端 Adapter。"""

    def open(self, request: PptOpenRequest) -> object:
        return _MemorySession(
            parent_hwnd=request.parent_hwnd,
            current_slide=request.start_slide,
            playback_state="playing" if request.autoplay else "stopped",
            slideshow_hwnd=10_000 + request.session.window_id,
        )

    def command(self, handle: object, request: PptCommandRequest) -> None:
        session = self._session(handle)
        if request.command is PptCommand.PLAY:
            session.playback_state = "playing"
        elif request.command is PptCommand.PAUSE:
            session.playback_state = "paused"
        elif request.command is PptCommand.STOP:
            session.playback_state = "stopped"
        elif request.command is PptCommand.NEXT:
            session.current_slide = min(session.total_slides, session.current_slide + 1)
        elif request.command is PptCommand.PREVIOUS:
            session.current_slide = max(1, session.current_slide - 1)
        elif request.command is PptCommand.GOTO:
            if request.slide_index > session.total_slides:
                raise ValueError(
                    f"PPT 页码 {request.slide_index} 超出总页数 {session.total_slides}"
                )
            session.current_slide = request.slide_index

    def get_state(self, handle: object) -> PptState:
        session = self._session(handle)
        return PptState(
            playback_state=session.playback_state,
            current_slide=session.current_slide,
            total_slides=session.total_slides,
            powerpoint_pid=os.getpid(),
            slideshow_hwnd=session.slideshow_hwnd,
            parent_hwnd=session.parent_hwnd,
        )

    def hide(self, handle: object) -> None:
        self._session(handle).visible = False

    def show(self, handle: object) -> None:
        self._session(handle).visible = True

    def close(self, handle: object) -> None:
        session = self._session(handle)
        session.playback_state = "idle"
        session.visible = False

    def preheat(self, request: PptPreheatRequest) -> None:
        del request

    def export_show(self, request: PptShowExportRequest) -> PptExportResult:
        return PptExportResult((request.target_uri,), powerpoint_pid=os.getpid())

    def export_slides(self, request: PptSlideExportRequest) -> PptExportResult:
        output_dir = Path(request.output_dir)
        return PptExportResult(
            tuple(str(output_dir / f"slide-{index}.png") for index in range(1, 4)),
            powerpoint_pid=os.getpid(),
        )

    def shutdown(self) -> None:
        return

    @staticmethod
    def _session(handle: object) -> _MemorySession:
        if not isinstance(handle, _MemorySession):
            raise TypeError("无效的内存 PPT 会话")
        return handle


class InMemoryPptBroker(PptBrokerEngine):
    """通过真实 Broker 会话引擎运行内存后端。"""

    def __init__(self) -> None:
        super().__init__(_MemoryBackend())


__all__ = ["InMemoryPptBroker"]
