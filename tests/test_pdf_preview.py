#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PDF 页面预览导出服务测试。
@Project : SCP-cv
@File : test_pdf_preview.py
@Author : Qintsg
@Date : 2026-08-05
'''
from __future__ import annotations

import os
from pathlib import Path
from typing import Iterator

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QGuiApplication

from scp_cv.services.pdf_preview import export_pdf_slide_previews_in_process


def _write_two_page_pdf(file_path: Path) -> None:
    """
    写入包含两页的最小 PDF 文件。
    :param file_path: 目标文件路径
    :return: None
    """
    file_path.write_bytes(
        b"""%PDF-1.1
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R 6 0 R]/Count 2>>endobj
3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 200]/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj
4 0 obj<</Length 44>>stream
BT /F1 24 Tf 50 100 Td (Hello) Tj ET
endstream
endobj
5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj
6 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 200]/Contents 7 0 R>>endobj
7 0 obj<</Length 20>>stream
BT /F1 24 Tf 50 100 Td (Two) Tj ET
endstream
endobj
xref
0 8
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000245 00000 n
0000000338 00000 n
0000000395 00000 n
0000000485 00000 n
trailer<</Size 8/Root 1 0 R>>
startxref
585
%%EOF"""
    )


@pytest.fixture(scope="module")
def qt_gui_app() -> Iterator[QGuiApplication]:
    """
    提供无界面的 QGuiApplication 实例。
    :return: QGuiApplication 迭代器
    """
    app = QGuiApplication.instance() or QGuiApplication([])
    yield app


def test_pdf_preview_renders_each_page(qt_gui_app: QGuiApplication, tmp_path: Path, settings) -> None:
    """PDF 预览服务应为每一页渲染 PNG。"""
    settings.MEDIA_ROOT = tmp_path / "media"
    pdf_path = tmp_path / "slides.pdf"
    _write_two_page_pdf(pdf_path)

    previews = export_pdf_slide_previews_in_process(pdf_path, 1)

    assert len(previews) == 2
    for preview in previews:
        assert preview.startswith("/media/pdf_previews/1/slide-")
    assert (settings.MEDIA_ROOT / "pdf_previews" / "1" / "slide-1.png").is_file()
    assert (settings.MEDIA_ROOT / "pdf_previews" / "1" / "slide-2.png").is_file()
