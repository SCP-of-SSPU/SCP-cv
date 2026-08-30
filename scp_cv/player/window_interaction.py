#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''播放器窗口的鼠标光标和 ID 覆盖层行为。'''

from __future__ import annotations

import logging

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import QWidget

logger = logging.getLogger(__name__)
CURSOR_IDLE_HIDE_DELAY_MS = 5000
OVERLAY_DISPLAY_DURATION_MS = 5000


class PlayerWindowInteractionMixin:
    """为 PlayerWindow 提供光标跟踪和 ID 覆盖层方法。"""

    def _install_cursor_tracking(self) -> None:
        """为播放窗口和当前渲染子组件安装鼠标事件过滤器。"""
        for widget in (
            self,
            self._background_label,
            self._video_viewport,
            self._video_container,
            self._web_viewport,
            self._web_container,
            self._overlay_label,
        ):
            self._track_cursor_widget(widget)
        self._restart_cursor_idle_timer()

    def _track_cursor_widget(self, widget: QWidget) -> None:
        """让指定 widget 参与鼠标静止隐藏逻辑。"""
        widget_id = id(widget)
        if widget_id in self._cursor_tracked_widgets:
            return
        self._cursor_tracked_widgets.add(widget_id)
        widget.setMouseTracking(True)
        if self._cursor_hidden:
            widget.setCursor(Qt.CursorShape.BlankCursor)
        widget.installEventFilter(self)
        for child in widget.findChildren(QWidget):
            self._track_cursor_widget(child)

    def _restart_cursor_idle_timer(self) -> None:
        """重置鼠标静止计时器。"""
        self._cursor_idle_timer.start(CURSOR_IDLE_HIDE_DELAY_MS)

    def _show_cursor_temporarily(self) -> None:
        """显示光标并重新开始静止计时。"""
        self._show_cursor()
        self._restart_cursor_idle_timer()

    def _show_cursor(self) -> None:
        """恢复播放窗口及子组件光标。"""
        if not self._cursor_hidden:
            return
        self._apply_cursor_shape(Qt.CursorShape.ArrowCursor)
        self._cursor_hidden = False
        logger.debug("窗口 [%d] 显示鼠标光标", self._window_id)

    @Slot()
    def _hide_idle_cursor(self) -> None:
        """鼠标静止超过阈值后隐藏光标。"""
        self._apply_cursor_shape(Qt.CursorShape.BlankCursor)
        self._cursor_hidden = True
        logger.debug("窗口 [%d] 隐藏鼠标光标", self._window_id)

    def _apply_cursor_shape(self, cursor_shape: Qt.CursorShape) -> None:
        """对窗口及所有已追踪子组件统一设置光标形状。"""
        self.setCursor(cursor_shape)
        for child in self.findChildren(QWidget):
            child.setCursor(cursor_shape)

    @Slot()
    def show_id_overlay(self) -> None:
        """显示窗口 ID 覆盖层并启动自动隐藏计时器。"""
        self._center_overlay()
        self._overlay_label.show()
        self._overlay_label.raise_()
        self._overlay_timer.start(OVERLAY_DISPLAY_DURATION_MS)
        logger.debug("窗口 [%d] 显示 ID 覆盖层", self._window_id)

    @Slot()
    def _hide_id_overlay(self) -> None:
        """隐藏窗口 ID 覆盖层。"""
        self._overlay_label.hide()
        logger.debug("窗口 [%d] 隐藏 ID 覆盖层", self._window_id)

    def _center_overlay(self) -> None:
        """将覆盖层居中定位到当前窗口中央。"""
        overlay_width = self._overlay_label.width()
        overlay_height = self._overlay_label.height()
        center_x = (self.width() - overlay_width) // 2
        center_y = (self.height() - overlay_height) // 2
        self._overlay_label.move(max(0, center_x), max(0, center_y))
