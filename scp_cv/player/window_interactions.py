#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
播放器窗口覆盖层和鼠标交互 mixin。
@Project : SCP-cv
@File : window_interactions.py
@Author : Qintsg
@Date : 2026-07-12
'''
from __future__ import annotations

import logging

from PySide6.QtCore import QEvent, QTimer, Qt, Slot
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QLabel, QWidget

logger = logging.getLogger("scp_cv.player.window")

# 窗口 ID 覆盖层显示时长（毫秒）
OVERLAY_DISPLAY_DURATION_MS = 5000

# 鼠标在播放窗口内静止后隐藏光标的等待时长（毫秒）
CURSOR_IDLE_HIDE_DELAY_MS = 5000


class PlayerWindowInteractionMixin:
    """封装窗口 ID 覆盖层和鼠标静止隐藏状态机。"""

    def _initialize_window_interactions(self) -> None:
        """
        创建覆盖层、计时器并接入所有现有渲染子控件。
        :return: None
        """
        self._cursor_hidden = False
        self._cursor_tracked_widgets: set[int] = set()

        self._overlay_label = QLabel(self)
        self._overlay_label.setText(f"窗口 {self._window_id}")
        self._overlay_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        overlay_font = QFont("Microsoft YaHei", 72, QFont.Weight.Bold)
        self._overlay_label.setFont(overlay_font)
        self._overlay_label.setStyleSheet(
            "color: #FFFFFF;"
            "background-color: rgba(0, 0, 0, 180);"
            "border-radius: 20px;"
            "padding: 20px 40px;"
        )
        self._overlay_label.setFixedSize(400, 200)
        self._overlay_label.hide()
        self._overlay_label.raise_()

        self._overlay_timer = QTimer(self)
        self._overlay_timer.setSingleShot(True)
        self._overlay_timer.timeout.connect(self._hide_id_overlay)

        self._cursor_idle_timer = QTimer(self)
        self._cursor_idle_timer.setSingleShot(True)
        self._cursor_idle_timer.timeout.connect(self._hide_idle_cursor)
        self._install_cursor_tracking()

    def _install_cursor_tracking(self) -> None:
        """
        为播放窗口和当前渲染子组件安装鼠标事件过滤器。
        :return: None
        """
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
        """
        让指定 widget 参与鼠标静止隐藏逻辑。
        :param widget: 待追踪的 QWidget
        :return: None
        """
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
        """
        重置鼠标静止计时器。
        :return: None
        """
        self._cursor_idle_timer.start(CURSOR_IDLE_HIDE_DELAY_MS)

    def _show_cursor_temporarily(self) -> None:
        """
        鼠标进入或移动时显示光标，并重新开始静止计时。
        :return: None
        """
        self._show_cursor()
        self._restart_cursor_idle_timer()

    def _show_cursor(self) -> None:
        """
        恢复播放窗口及子组件光标。
        :return: None
        """
        if not self._cursor_hidden:
            return
        self._apply_cursor_shape(Qt.CursorShape.ArrowCursor)
        self._cursor_hidden = False
        logger.debug("窗口 [%d] 显示鼠标光标", self._window_id)

    @Slot()
    def _hide_idle_cursor(self) -> None:
        """
        鼠标静止超过阈值后隐藏播放窗口光标。
        :return: None
        """
        self._apply_cursor_shape(Qt.CursorShape.BlankCursor)
        self._cursor_hidden = True
        logger.debug("窗口 [%d] 隐藏鼠标光标", self._window_id)

    def _apply_cursor_shape(self, cursor_shape: Qt.CursorShape) -> None:
        """
        对窗口及所有已追踪子组件统一设置光标形状。
        :param cursor_shape: Qt 光标形状
        :return: None
        """
        self.setCursor(cursor_shape)
        for child in self.findChildren(QWidget):
            child.setCursor(cursor_shape)

    @Slot()
    def show_id_overlay(self) -> None:
        """
        显示窗口 ID 覆盖层，5 秒后自动隐藏。
        若已显示则重置计时器。
        :return: None
        """
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

    def eventFilter(self, watched: object, event: object) -> bool:
        """
        捕获播放窗口及子组件鼠标事件，用于自动隐藏光标。
        :param watched: 事件来源对象
        :param event: Qt 事件
        :return: 是否拦截事件
        """
        if isinstance(event, QEvent):
            event_type = event.type()
            if event_type == QEvent.Type.ChildAdded and hasattr(event, "child"):
                child = event.child()
                if isinstance(child, QWidget):
                    self._track_cursor_widget(child)
            elif event_type in {QEvent.Type.Enter, QEvent.Type.MouseMove}:
                self._show_cursor_temporarily()
            elif event_type == QEvent.Type.Leave and watched is self:
                self._cursor_idle_timer.stop()
                self._show_cursor()
        return super().eventFilter(watched, event)

    def childEvent(self, event: object) -> None:
        """
        新增子组件时接入鼠标静止隐藏逻辑。
        :param event: Qt child 事件
        :return: None
        """
        super().childEvent(event)
        if not hasattr(self, "_cursor_tracked_widgets"):
            return
        if hasattr(event, "added") and hasattr(event, "child") and event.added():
            child = event.child()
            if isinstance(child, QWidget):
                self._track_cursor_widget(child)

    def resizeEvent(self, event: object) -> None:
        """窗口尺寸变化时重新居中覆盖层。"""
        super().resizeEvent(event)
        if self._overlay_label.isVisible():
            self._center_overlay()


__all__ = [
    "CURSOR_IDLE_HIDE_DELAY_MS",
    "OVERLAY_DISPLAY_DURATION_MS",
    "PlayerWindowInteractionMixin",
]
