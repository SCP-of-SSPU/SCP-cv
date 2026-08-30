#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PDF 演示文稿播放适配器，使用 QtPdf 渲染 QImage 并自绘显示。
不依赖 QPdfView，避免灰框、滚动条和页面留白。
@Project : SCP-cv
@File : pdf.py
@Author : Qintsg
@Date : 2026-08-05
'''
from __future__ import annotations

import logging
import os
from typing import Optional

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtPdf import QPdfDocument
from PySide6.QtWidgets import QWidget

from scp_cv.player.adapters.base import AdapterState, SourceAdapter

logger = logging.getLogger(__name__)


class _PdfPageWidget(QWidget):
    """只负责把当前页 QImage 按宽高比绘制到黑色背景上。"""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """
        初始化页面控件。
        :param parent: 父级窗口
        :return: None
        """
        super().__init__(parent)
        self._image = QImage()
        self._on_resize: object | None = None
        self.setAutoFillBackground(True)
        self.setStyleSheet("background-color: #000000; border: none;")

    def set_page_image(self, image: QImage) -> None:
        """
        设置当前页图像并触发重绘。
        :param image: 渲染后的页面图像
        :return: None
        """
        self._image = image
        self.update()

    def set_resize_callback(self, callback: object) -> None:
        """
        注入窗口尺寸变化回调，用于按新尺寸重新渲染 PDF 页。
        :param callback: 无参可调用对象
        :return: None
        """
        self._on_resize = callback

    def resizeEvent(self, event: object) -> None:
        """
        窗口尺寸变化时通知适配器重新渲染。
        :param event: resize 事件
        :return: None
        """
        super().resizeEvent(event)
        callback = self._on_resize
        if callable(callback):
            callback()

    def paintEvent(self, event: object) -> None:
        """
        绘制当前 PDF 页，保持宽高比并居中。
        :param event: paint 事件
        :return: None
        """
        painter = QPainter(self)
        painter.fillRect(self.rect(), Qt.GlobalColor.black)
        if self._image.isNull():
            return
        scaled = self._image.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        offset_x = (self.width() - scaled.width()) // 2
        offset_y = (self.height() - scaled.height()) // 2
        painter.drawImage(offset_x, offset_y, scaled)


class PdfSourceAdapter(SourceAdapter):
    capabilities = frozenset({"next", "prev", "goto"})
    """
    PDF 演示文稿显示适配器。

    使用 QPdfDocument.render() 渲染当前页为 QImage，
    再交给自绘控件全屏显示，无滚动、无灰框、无页面留白。
    """

    def __init__(self) -> None:
        """
        初始化 PDF 适配器。
        :return: None
        """
        super().__init__(adapter_name="pdf")
        self._document: Optional[QPdfDocument] = None
        self._view: Optional[_PdfPageWidget] = None
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

        view = _PdfPageWidget(self._parent_widget)
        view.setGeometry(self._parent_widget.rect())
        view.set_resize_callback(self._render_current_page)
        view.show()

        self._document = document
        self._view = view
        self._total_pages = int(document.pageCount())
        self._current_page = 0
        if autoplay:
            self.goto_item(1)
        else:
            self._render_current_page()

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
        跳转到指定页（1-based）并重新渲染。
        :param index: 目标页码
        """
        if self._view is None or self._document is None or self._total_pages <= 0:
            return
        self._current_page = max(1, min(int(index), self._total_pages)) - 1
        self._render_current_page()

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

    def _render_current_page(self) -> None:
        """
        按当前控件尺寸渲染当前 PDF 页。
        :return: None
        """
        if self._view is None or self._document is None:
            return
        target_size = self._view.size()
        if target_size.isEmpty():
            target_size = self._parent_widget.rect().size() if self._parent_widget is not None else QSize(1920, 1080)
        render_width = max(1, int(target_size.width() * self._view.devicePixelRatioF()))
        render_height = max(1, int(target_size.height() * self._view.devicePixelRatioF()))
        image = self._document.render(self._current_page, QSize(render_width, render_height))
        self._view.set_page_image(image)

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
