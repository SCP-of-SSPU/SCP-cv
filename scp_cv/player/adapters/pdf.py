#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PDF 演示文稿播放适配器，使用 QtPdf 渲染，不依赖 PowerPoint COM。
@Project : SCP-cv
@File : pdf.py
@Author : Qintsg
@Date : 2026-08-05
'''
from __future__ import annotations

import logging
import os
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtPdf import QPdfDocument
from PySide6.QtPdfWidgets import QPdfView
from PySide6.QtWidgets import QWidget

from scp_cv.player.adapters.base import AdapterState, SourceAdapter

logger = logging.getLogger(__name__)


class PdfSourceAdapter(SourceAdapter):
    """
    PDF 演示文稿显示适配器。

    使用 QtPdf 的 QPdfDocument + QPdfView 渲染 PDF 页面，
    嵌入 PlayerWindow 的视频容器中全屏显示，支持翻页和跳页。
    """

    def __init__(self) -> None:
        """
        初始化 PDF 适配器。
        :return: None
        """
        super().__init__(adapter_name="pdf")
        self._document: Optional[QPdfDocument] = None
        self._view: Optional[QPdfView] = None
        self._parent_widget: Optional[QWidget] = None
        self._file_path: str = ""
        self._current_page: int = 0
        self._total_pages: int = 0

    def open(self, uri: str, window_handle: int, autoplay: bool = True) -> None:
        """
        打开 PDF 文件并显示第一页。
        :param uri: PDF 文件绝对路径
        :param window_handle: 渲染目标窗口的原生句柄
        :param autoplay: 是否打开后自动显示第一页
        """
        if not os.path.isfile(uri):
            raise FileNotFoundError(f"PDF 文件不存在：{uri}")
        if not uri.lower().endswith(".pdf"):
            raise ValueError(f"不是 PDF 文件：{uri}")

        self._file_path = uri
        document = QPdfDocument()
        document.load(uri)
        if document.status() != QPdfDocument.Status.Ready:
            error_message = f"PDF 文档加载失败：{uri}"
            document.close()
            self._logger.error(error_message)
            raise ValueError(error_message)

        self._parent_widget = self._find_widget_by_handle(window_handle)
        if self._parent_widget is None:
            document.close()
            raise RuntimeError("无法获取渲染容器")

        view = QPdfView(self._parent_widget)
        view.setDocument(document)
        view.setPageMode(QPdfView.PageMode.SinglePage)
        view.setZoomMode(QPdfView.ZoomMode.FitInView)
        view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        view.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        view.setGeometry(self._parent_widget.rect())
        view.show()

        self._document = document
        self._view = view
        self._total_pages = int(document.pageCount())
        self._current_page = 0
        if autoplay:
            self.goto_item(1)

        self._mark_open()
        self._logger.info("PDF 已打开：%s（%d 页）", uri, self._total_pages)

    def close(self) -> None:
        """
        关闭 PDF 并释放资源。
        :return: None
        """
        if self._view is not None:
            self._view.hide()
            self._view.deleteLater()
            self._view = None
        if self._document is not None:
            try:
                self._document.close()
            except Exception:
                pass
            self._document = None
        self._parent_widget = None
        self._file_path = ""
        self._current_page = 0
        self._total_pages = 0
        self._mark_closed()
        self._logger.info("PDF 已关闭")

    def play(self) -> None:
        """PDF 无播放概念，忽略。"""
        self._logger.debug("PDF 不支持 play 操作")

    def pause(self) -> None:
        """PDF 无暂停概念，忽略。"""
        self._logger.debug("PDF 不支持 pause 操作")

    def stop(self) -> None:
        """PDF 无停止概念，忽略。"""
        self._logger.debug("PDF 不支持 stop 操作")

    def next_item(self) -> None:
        """切换到下一页。"""
        if self._total_pages <= 0:
            return
        self.goto_item(min(self._current_page + 2, self._total_pages))

    def prev_item(self) -> None:
        """切换到上一页。"""
        if self._total_pages <= 0:
            return
        self.goto_item(max(self._current_page, 1))

    def goto_item(self, index: int) -> None:
        """
        跳转到指定页（1-based）。
        :param index: 目标页码
        """
        if self._view is None or self._document is None or self._total_pages <= 0:
            return
        page_index = max(1, min(int(index), self._total_pages)) - 1
        navigator = self._view.pageNavigator()
        try:
            navigator.jump(page_index)
        except TypeError:
            navigator.jump(page_index, self._view.rect().topLeft())
        self._current_page = page_index

    def get_state(self) -> AdapterState:
        """
        获取 PDF 显示状态。
        :return: PDF 显示中返回 playing，否则 idle
        """
        if self._view is not None and self._document is not None:
            return AdapterState(
                playback_state="playing",
                current_slide=self._current_page + 1,
                total_slides=self._total_pages,
            )
        return AdapterState(playback_state="idle")

    @staticmethod
    def _find_widget_by_handle(window_handle: int) -> Optional[QWidget]:
        """
        通过原生窗口句柄查找对应的 QWidget。
        :param window_handle: 原生窗口句柄
        :return: 对应的 QWidget，找不到返回 None
        """
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            return None
        for widget in app.allWidgets():
            if int(widget.winId()) == window_handle:
                return widget
        return None


__all__ = ["PdfSourceAdapter"]
