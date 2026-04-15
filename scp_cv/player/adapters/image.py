#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
图片源适配器，通过 QLabel + QPixmap 在 PlayerWindow 中显示图片。
支持常见图片格式（PNG、JPG、BMP、GIF、WebP 等）。
@Project : SCP-cv
@File : image.py
@Author : Qintsg
@Date : 2026-04-15
'''
from __future__ import annotations

import logging
import os
from typing import Optional

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel, QWidget

from scp_cv.player.adapters.base import AdapterState, SourceAdapter

logger = logging.getLogger(__name__)


class ImageSourceAdapter(SourceAdapter):
    """
    图片显示适配器。

    使用 QLabel + QPixmap 渲染静态图片，自适应缩放至容器大小。
    图片居中显示，保持原始宽高比。

    与 PlayerWindow 的集成：
    - QLabel 作为子 widget 嵌入到播放器窗口的视频容器中
    - 窗口大小变化时需外部调用 _resize_to_container() 更新
    """

    def __init__(self) -> None:
        super().__init__(adapter_name="image")
        self._label: Optional[QLabel] = None
        self._pixmap: Optional[QPixmap] = None
        self._file_path: str = ""
        self._parent_widget: Optional[QWidget] = None

    def open(self, uri: str, window_handle: int, autoplay: bool = True) -> None:
        """
        打开图片文件并显示。
        :param uri: 图片文件绝对路径
        :param window_handle: 渲染目标窗口的原生句柄
        :param autoplay: 忽略（图片无播放概念）
        """
        if not os.path.isfile(uri):
            raise FileNotFoundError(f"图片文件不存在：{uri}")

        self._file_path = uri

        # 加载图片
        pixmap = QPixmap(uri)
        if pixmap.isNull():
            raise ValueError(f"无法加载图片：{uri}")
        self._pixmap = pixmap

        # 查找目标窗口的视频容器
        self._parent_widget = self._find_widget_by_handle(window_handle)

        # 创建 QLabel 作为图片显示容器
        self._label = QLabel(self._parent_widget)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setStyleSheet("background-color: black;")

        if self._parent_widget is not None:
            self._label.setGeometry(self._parent_widget.rect())

        # 缩放图片至容器大小（保持宽高比）
        self._apply_scaled_pixmap()
        self._label.show()

        self._mark_open()
        self._logger.info("图片已打开：%s（%dx%d）", uri, pixmap.width(), pixmap.height())

    def _apply_scaled_pixmap(self) -> None:
        """将原始图片缩放至 QLabel 当前尺寸并居中显示。"""
        if self._label is None or self._pixmap is None:
            return

        label_size = self._label.size()
        scaled_pixmap = self._pixmap.scaled(
            label_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._label.setPixmap(scaled_pixmap)

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

    def close(self) -> None:
        """关闭图片并释放资源。"""
        if self._label is not None:
            self._label.hide()
            self._label.deleteLater()
            self._label = None

        self._pixmap = None
        self._parent_widget = None
        self._file_path = ""
        self._mark_closed()
        self._logger.info("图片已关闭")

    # ═══════════════════ 播放控制（图片无时间线） ═══════════════════

    def play(self) -> None:
        """图片无播放概念，忽略。"""
        self._logger.debug("图片不支持 play 操作")

    def pause(self) -> None:
        """图片无暂停概念，忽略。"""
        self._logger.debug("图片不支持 pause 操作")

    def stop(self) -> None:
        """图片无停止概念，忽略。"""
        self._logger.debug("图片不支持 stop 操作")

    # ═══════════════════ 状态获取 ═══════════════════

    def get_state(self) -> AdapterState:
        """
        获取图片显示状态。
        :return: 图片始终返回 playing 状态（正在显示）
        """
        if self._label is not None and self._pixmap is not None:
            return AdapterState(playback_state="playing")
        return AdapterState(playback_state="idle")
