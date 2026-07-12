#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PowerPoint Broker COM 导出任务测试。
@Project : SCP-cv
@File : test_ppt_broker_powerpoint_exports.py
@Author : Qintsg
@Date : 2026-07-12
'''
from __future__ import annotations

from pathlib import Path

from scp_cv.player.ppt_broker import (
    PptBrokerEngine,
    PptShowExportRequest,
    PptShowFormat,
    PptSlideExportRequest,
)
from scp_cv.player.ppt_broker.powerpoint import PowerPointComBackend


class _ExportSlide:
    """记录 PowerPoint Slide.Export 调用。"""

    def __init__(self) -> None:
        self.export_calls: list[tuple[str, str]] = []

    def Export(self, output_path: str, image_format: str) -> None:
        self.export_calls.append((output_path, image_format))


class _ExportSlides:
    """支持 Count 和 1-based 调用的 Slides 集合。"""

    def __init__(self, count: int = 2) -> None:
        self.items = [_ExportSlide() for _ in range(count)]
        self.Count = count

    def __call__(self, index: int) -> _ExportSlide:
        return self.items[index - 1]


class _ExportPresentation:
    """记录 SaveAs、逐页 Export 和 Close 的任务 Presentation。"""

    def __init__(self) -> None:
        self.Saved = False
        self.Slides = _ExportSlides()
        self.save_as_calls: list[tuple[str, int]] = []
        self.close_called = False

    def SaveAs(self, target_uri: str, save_format: int) -> None:
        self.save_as_calls.append((target_uri, save_format))

    def Close(self, *_args: object) -> None:
        self.close_called = True


class _ExportPresentations:
    """每个导出任务返回独立 Presentation。"""

    Count = 0

    def __init__(self) -> None:
        self.opened: list[_ExportPresentation] = []

    def Open(self, *_args: object, **_kwargs: object) -> _ExportPresentation:
        presentation = _ExportPresentation()
        self.opened.append(presentation)
        return presentation


class _ExportPowerPoint:
    """记录 Application 是否被任务错误退出。"""

    def __init__(self) -> None:
        self.Presentations = _ExportPresentations()
        self.DisplayAlerts = 2
        self.quit_called = False

    def Quit(self) -> None:
        self.quit_called = True


def test_show_and_slide_exports_share_application_and_close_task_presentations(
    tmp_path: Path,
) -> None:
    """SaveAs/PNG 导出应复用 Application，且每次只关闭任务 Presentation。"""
    application = _ExportPowerPoint()
    application_creations = 0

    def create_application() -> object:
        nonlocal application_creations
        application_creations += 1
        return application

    backend = PowerPointComBackend(
        application_factory=create_application,
        process_id_reader=lambda _app: 4242,
        window_port=object(),
        file_exists=lambda _path: True,
    )
    broker = PptBrokerEngine(backend)
    show_path = tmp_path / "cached.ppsx"
    slide_dir = tmp_path / "slides"
    slide_dir.mkdir()
    try:
        show_result = broker.export_show(
            PptShowExportRequest(
                source_uri="C:/slides/source.pptx",
                target_uri=str(show_path),
                target_format=PptShowFormat.PPSX,
            )
        )
        slide_result = broker.export_slides(
            PptSlideExportRequest(
                source_uri="C:/slides/source.pptx",
                output_dir=str(slide_dir),
            )
        )

        assert application_creations == 1
        assert show_result.paths == (str(show_path),)
        assert slide_result.paths == (
            str(slide_dir / "slide-1.png"),
            str(slide_dir / "slide-2.png"),
        )
        assert application.Presentations.opened[0].save_as_calls == [
            (str(show_path), 28),
        ]
        assert application.Presentations.opened[1].Slides.items[0].export_calls == [
            (str(slide_dir / "slide-1.png"), "PNG"),
        ]
        assert all(
            presentation.close_called
            for presentation in application.Presentations.opened
        )
        assert application.quit_called is False
    finally:
        broker.shutdown()
