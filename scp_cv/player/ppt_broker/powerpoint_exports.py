#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PowerPoint Broker 的放映文件和逐页 PNG 导出实现。
@Project : SCP-cv
@File : powerpoint_exports.py
@Author : Qintsg
@Date : 2026-07-11
'''
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from scp_cv.player.ppt_broker.com_support import same_path
from scp_cv.player.ppt_broker.contracts import (
    PptExportResult,
    PptShowExportRequest,
    PptShowFormat,
    PptSlideExportRequest,
)

_POWERPOINT_SAVE_FORMATS = {
    PptShowFormat.PPSX: 28,
    PptShowFormat.PPS: 7,
}


class PowerPointExportHost(Protocol):
    """导出实现所需的 PowerPoint 后端内部 seam。"""

    _file_exists: Callable[[str], bool]
    _process_id: int

    def _ensure_application(self) -> object: ...

    def _open_presentation(
        self,
        application: object,
        uri: str,
        *,
        read_only: bool = False,
    ) -> object: ...

    def _run_operation(
        self,
        operation_name: str,
        callback: Callable[[], object],
    ) -> object: ...

    def _close_presentation(self, presentation: object) -> None: ...


def export_show(
    host: PowerPointExportHost,
    request: PptShowExportRequest,
) -> PptExportResult:
    """用共享 Application 把独立任务 Presentation 导出为放映文件。"""
    _validate_source(host, request.source_uri)
    target_path = Path(request.target_uri)
    if not target_path.parent.is_dir():
        raise FileNotFoundError(
            f"PPT 放映导出目录不存在：{target_path.parent}；请先由调用服务创建目录。"
        )
    if same_path(request.source_uri, request.target_uri):
        raise ValueError("PPT 放映导出目标不能覆盖源文件")
    application = host._ensure_application()
    presentation = host._open_presentation(
        application,
        request.source_uri,
        read_only=True,
    )
    try:
        save_format = _POWERPOINT_SAVE_FORMATS[request.target_format]
        host._run_operation(
            "导出 PowerPoint 放映文件",
            lambda: presentation.SaveAs(  # type: ignore[attr-defined]
                request.target_uri,
                save_format,
            ),
        )
        if not host._file_exists(request.target_uri):
            raise RuntimeError(
                f"PowerPoint 未生成放映导出文件：{request.target_uri}"
            )
        return PptExportResult(
            (request.target_uri,),
            powerpoint_pid=host._process_id,
        )
    finally:
        host._close_presentation(presentation)


def export_slides(
    host: PowerPointExportHost,
    request: PptSlideExportRequest,
) -> PptExportResult:
    """用共享 Application 把独立任务 Presentation 逐页导出为 PNG。"""
    _validate_source(host, request.source_uri)
    output_dir = Path(request.output_dir)
    if not output_dir.is_dir():
        raise FileNotFoundError(
            f"PPT 预览导出目录不存在：{output_dir}；请先由调用服务创建目录。"
        )
    application = host._ensure_application()
    presentation = host._open_presentation(
        application,
        request.source_uri,
        read_only=True,
    )
    output_paths: list[str] = []
    try:
        slide_count = int(presentation.Slides.Count)  # type: ignore[attr-defined]
        for slide_index in range(1, slide_count + 1):
            output_path = str(output_dir / f"slide-{slide_index}.png")
            slide = presentation.Slides(slide_index)  # type: ignore[attr-defined]
            host._run_operation(
                f"导出 PowerPoint 第 {slide_index} 页 PNG",
                lambda slide=slide, output_path=output_path: slide.Export(
                    output_path,
                    request.image_format,
                ),
            )
            if not host._file_exists(output_path):
                raise RuntimeError(
                    f"PowerPoint 未生成第 {slide_index} 页预览：{output_path}"
                )
            output_paths.append(output_path)
        return PptExportResult(
            tuple(output_paths),
            powerpoint_pid=host._process_id,
        )
    finally:
        host._close_presentation(presentation)


def _validate_source(host: PowerPointExportHost, source_uri: str) -> None:
    if not host._file_exists(source_uri):
        raise FileNotFoundError(f"PPT 导出源文件不存在：{source_uri}")


__all__ = ["PowerPointExportHost", "export_show", "export_slides"]
