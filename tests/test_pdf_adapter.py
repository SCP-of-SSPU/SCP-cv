#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PDF 演示文稿播放适配器测试。
@Project : SCP-cv
@File : test_pdf_adapter.py
@Author : Qintsg
@Date : 2026-08-05
'''
from __future__ import annotations

import os
from pathlib import Path
from typing import Iterator

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QWidget

from scp_cv.player.adapters.pdf import PdfSourceAdapter


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
def qt_app() -> Iterator[QApplication]:
    """
    提供无界面的 QApplication 实例。
    :return: QApplication 迭代器
    """
    app = QApplication.instance() or QApplication([])
    yield app


def test_pdf_adapter_opens_navigates_and_closes(qt_app: QApplication, tmp_path: Path) -> None:
    """PDF 适配器应支持打开、翻页、跳页和关闭。"""
    pdf_path = tmp_path / "slides.pdf"
    _write_two_page_pdf(pdf_path)
    parent = QWidget()
    parent.resize(800, 450)
    parent.show()
    qt_app.processEvents()
    handle = int(parent.winId())
    adapter = PdfSourceAdapter()

    try:
        adapter.open(str(pdf_path), handle)
        state = adapter.get_state()
        assert state.playback_state == "playing"
        assert state.current_slide == 1
        assert state.total_slides == 2

        adapter.next_item()
        assert adapter.get_state().current_slide == 2
        adapter.next_item()
        assert adapter.get_state().current_slide == 2
        adapter.prev_item()
        assert adapter.get_state().current_slide == 1
        adapter.goto_item(2)
        assert adapter.get_state().current_slide == 2
    finally:
        adapter.close()
        parent.close()
        qt_app.processEvents()


def test_pdf_adapter_rejects_missing_file(qt_app: QApplication) -> None:
    """不存在的 PDF 文件应抛出 FileNotFoundError。"""
    adapter = PdfSourceAdapter()
    with pytest.raises(FileNotFoundError):
        adapter.open("Z:/no/such/slides.pdf", 0)


def test_pdf_adapter_rejects_non_pdf(qt_app: QApplication, tmp_path: Path) -> None:
    """非 PDF 文件应抛出 ValueError。"""
    other_path = tmp_path / "slides.pptx"
    other_path.write_bytes(b"not-pdf")
    adapter = PdfSourceAdapter()
    with pytest.raises(ValueError):
        adapter.open(str(other_path), 0)
