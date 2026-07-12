#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
播放器窗口显示器定位和渲染客户区同步 mixin。
@Project : SCP-cv
@File : window_display.py
@Author : Qintsg
@Date : 2026-07-12
'''
from __future__ import annotations

import logging

from PySide6.QtCore import QRect, QTimer, Slot
from PySide6.QtGui import QGuiApplication, QScreen

logger = logging.getLogger("scp_cv.player.window")

# 开发预览窗口最多占目标屏幕的 80%，四个窗口以 24 像素步长错位。
DEBUG_PREVIEW_MAX_SCREEN_RATIO = 0.8
DEBUG_PREVIEW_CASCADE_OFFSET_PX = 24
RENDER_RESIZE_DEBOUNCE_MS = 50


class PlayerWindowDisplayMixin:
    """封装显示器选择、窗口几何和渲染客户区尺寸同步。"""

    def _initialize_display_runtime(self) -> None:
        """
        初始化渲染客户区几何和尺寸防抖通知。
        :return: None
        """
        self._apply_render_viewport_geometry()
        self._render_resize_timer = QTimer(self)
        self._render_resize_timer.setSingleShot(True)
        self._render_resize_timer.timeout.connect(
            self._emit_render_viewport_resize,
        )

    @Slot(QRect)
    def position_on_display(self, geometry: QRect) -> None:
        """
        将窗口定位到指定的屏幕矩形区域。
        :param geometry: QRect，屏幕的绝对坐标矩形
        :return: None
        """
        target_geometry = self._normalize_qt_geometry(geometry)
        window_handle = self.windowHandle()
        target_screen = self._screen_for_geometry(target_geometry)
        if window_handle is not None and target_screen is not None:
            window_handle.setScreen(target_screen)

        if self._debug_mode:
            self.setMinimumSize(0, 0)
            self.setMaximumSize(16777215, 16777215)
            applied_geometry = self._debug_preview_geometry(target_geometry)
        else:
            self.setFixedSize(target_geometry.size())
            applied_geometry = target_geometry

        self.setGeometry(applied_geometry)
        self._apply_render_viewport_geometry()
        self.show()
        if not self._debug_mode:
            self.raise_()
        logger.info(
            "窗口 [%d] 定位到 Qt 屏幕区域 (%d, %d) %dx%d",
            self._window_id,
            applied_geometry.x(),
            applied_geometry.y(),
            applied_geometry.width(),
            applied_geometry.height(),
        )

    def _debug_preview_geometry(self, target_geometry: QRect) -> QRect:
        """
        计算目标屏幕内可缩放且按窗口编号错位的 16:9 预览矩形。
        :param target_geometry: Qt 目标屏幕几何
        :return: 开发预览窗口几何
        """
        max_width = max(
            16,
            int(target_geometry.width() * DEBUG_PREVIEW_MAX_SCREEN_RATIO),
        )
        max_height = max(
            9,
            int(target_geometry.height() * DEBUG_PREVIEW_MAX_SCREEN_RATIO),
        )
        preview_scale = max(1, min(max_width // 16, max_height // 9))
        preview_width = preview_scale * 16
        preview_height = preview_scale * 9
        centered_x = target_geometry.x() + (
            target_geometry.width() - preview_width
        ) // 2
        centered_y = target_geometry.y() + (
            target_geometry.height() - preview_height
        ) // 2
        cascade_offset = (
            max(0, self._window_id - 1) % 4
        ) * DEBUG_PREVIEW_CASCADE_OFFSET_PX
        preview_x = min(
            centered_x + cascade_offset,
            target_geometry.right() - preview_width + 1,
        )
        preview_y = min(
            centered_y + cascade_offset,
            target_geometry.bottom() - preview_height + 1,
        )
        return QRect(
            preview_x,
            preview_y,
            preview_width,
            preview_height,
        )

    @staticmethod
    def _normalize_qt_geometry(requested_geometry: QRect) -> QRect:
        """
        将外部显示器坐标归一到 Qt 坐标系，避免高 DPI 下窗口跨屏放大。
        :param requested_geometry: 外部检测到的目标几何
        :return: 更适合 Qt 窗口定位的几何
        """
        matched_screen = PlayerWindowDisplayMixin._screen_for_geometry(
            requested_geometry,
        )
        if matched_screen is not None:
            return QRect(matched_screen.geometry())

        screens = QGuiApplication.screens()
        if not screens:
            return QRect(requested_geometry)

        requested_center = requested_geometry.center()
        closest_screen = min(
            screens,
            key=lambda screen: (
                abs(screen.geometry().center().x() - requested_center.x())
                + abs(screen.geometry().center().y() - requested_center.y())
            ),
        )
        return QRect(closest_screen.geometry())

    @staticmethod
    def _screen_for_geometry(geometry: QRect) -> QScreen | None:
        """
        按最大交叠面积查找 Qt 屏幕，避免物理坐标和 Qt 逻辑坐标缩放差异导致错屏。
        :param geometry: 待匹配的窗口几何
        :return: QScreen 或 None
        """
        best_screen: QScreen | None = None
        best_area = 0
        for screen in QGuiApplication.screens():
            screen_geometry = screen.geometry()
            intersected = screen_geometry.intersected(geometry)
            area = max(0, intersected.width()) * max(0, intersected.height())
            if area > best_area:
                best_area = area
                best_screen = screen
        if best_screen is not None:
            return best_screen

        geometry_center = geometry.center()
        screens = QGuiApplication.screens()
        if not screens:
            return None
        return min(
            screens,
            key=lambda screen: (
                abs(screen.geometry().center().x() - geometry_center.x())
                + abs(screen.geometry().center().y() - geometry_center.y())
            ),
        )

    def _apply_render_viewport_geometry(self) -> None:
        """根据当前窗口尺寸更新渲染容器几何。"""
        viewport_width = max(1, self.width())
        viewport_height = max(1, self.height())
        self._video_container.setGeometry(0, 0, viewport_width, viewport_height)
        self._web_container.setGeometry(0, 0, viewport_width, viewport_height)

    def _emit_render_viewport_resize(self) -> None:
        """把稳定后的渲染客户区尺寸通知控制器。"""
        self.render_viewport_resized.emit(
            self._window_id,
            max(1, self._video_container.width()),
            max(1, self._video_container.height()),
        )

    @staticmethod
    def _flush_window_events() -> None:
        """
        处理一次 Qt 事件队列，让首次 show/resize 的原生窗口矩形同步到 Win32。
        :return: None
        """
        app = QGuiApplication.instance()
        if app is None:
            return
        app.processEvents()

    def resizeEvent(self, event: object) -> None:
        """窗口尺寸变化时同步渲染客户区并防抖通知控制器。"""
        super().resizeEvent(event)
        self._apply_render_viewport_geometry()
        resize_timer = getattr(self, "_render_resize_timer", None)
        if resize_timer is not None:
            resize_timer.start(RENDER_RESIZE_DEBOUNCE_MS)


__all__ = [
    "DEBUG_PREVIEW_CASCADE_OFFSET_PX",
    "DEBUG_PREVIEW_MAX_SCREEN_RATIO",
    "PlayerWindowDisplayMixin",
    "RENDER_RESIZE_DEBOUNCE_MS",
]
