#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
播放器显示窗口：每物理屏幕一个实例，支持全屏/无边框/置顶。
视频通过适配器渲染到嵌入的原生容器中。
@Project : SCP-cv
@File : window.py
@Author : Qintsg
@Date : 2026-04-14
'''
from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import QRect, QTimer, Qt, Signal, Slot
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QLabel,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

from PySide6.QtWebEngineWidgets import QWebEngineView

logger = logging.getLogger(__name__)

# 窗口 ID 覆盖层显示时长（毫秒）
OVERLAY_DISPLAY_DURATION_MS = 5000


class PlayerWindow(QWidget):
    """
    播放器显示窗口。每个物理屏幕对应一个实例。

    职责：
    - 全屏/无边框/置顶（正常模式）或可调窗口（DEBUG 模式）
    - 提供原生窗口句柄供视频渲染
    - 显示器定位（坐标和尺寸由外部控制器指定）
    - 窗口 ID 覆盖层（按钮触发后 5 秒自动隐藏）

    与视频管线的交互：
    - 通过 video_window_handle 属性提供渲染目标
    - 视频管线的创建和生命周期由 PlayerController 管理
    """

    # 信号：外部可监听窗口关闭
    window_closed = Signal()

    def __init__(
        self,
        window_id: int = 0,
        debug_mode: bool = False,
        parent: Optional[QWidget] = None,
    ) -> None:
        """
        初始化播放器窗口。
        :param window_id: 窗口编号（1-4）
        :param debug_mode: True 时不强制全屏/置顶，方便调试
        :param parent: 父 widget
        """
        super().__init__(parent)
        self._window_id = window_id
        self._debug_mode = debug_mode
        self._is_showing_video = False

        # ═══ 窗口属性 ═══
        self.setWindowTitle(f"SCP-cv 播放器 [窗口{window_id}]")
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)

        if not debug_mode:
            # 正常模式：无边框 + 置顶
            self.setWindowFlags(
                Qt.WindowType.FramelessWindowHint
                | Qt.WindowType.WindowStaysOnTopHint
            )
        else:
            # DEBUG 模式：普通窗口，可移动/缩放
            self.setWindowFlags(Qt.WindowType.Window)

        # ═══ 布局：stacked layout（黑屏背景 + 视频容器叠加） ═══
        self._stacked_layout = QStackedLayout()
        self._stacked_layout.setStackingMode(
            QStackedLayout.StackingMode.StackAll,
        )

        # 底层：黑屏背景
        self._background_label = QLabel()
        self._background_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._background_label.setStyleSheet("background-color: #000000;")
        self._stacked_layout.addWidget(self._background_label)

        # 视频渲染容器（原生窗口）
        self._video_container = QWidget()
        self._video_container.setAttribute(
            Qt.WidgetAttribute.WA_NativeWindow, True,
        )
        self._video_container.setStyleSheet("background-color: #000000;")
        self._video_container.hide()
        self._stacked_layout.addWidget(self._video_container)

        # 网页渲染容器（标准 QWidget，不设置 WA_NativeWindow 以支持鼠标交互）
        self._web_container = QWidget()
        self._web_container.setStyleSheet("background-color: #000000;")
        # 启用鼠标追踪，确保 QWebEngineView 子组件能接收鼠标事件
        self._web_container.setMouseTracking(True)
        self._web_container.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._web_container.hide()
        self._stacked_layout.addWidget(self._web_container)

        # 主 layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addLayout(self._stacked_layout)

        # ═══ 窗口 ID 覆盖层 ═══
        self._overlay_label = QLabel(self)
        self._overlay_label.setText(f"窗口 {window_id}")
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
        # 覆盖层始终居中显示——在 resizeEvent 中重新定位
        self._overlay_label.raise_()

        # 覆盖层自动隐藏计时器
        self._overlay_timer = QTimer(self)
        self._overlay_timer.setSingleShot(True)
        self._overlay_timer.timeout.connect(self._hide_id_overlay)

        logger.info(
            "播放器窗口已初始化（id=%d, debug=%s）",
            window_id,
            "开" if debug_mode else "关",
        )

    @property
    def window_id(self) -> int:
        """窗口编号。"""
        return self._window_id

    @property
    def video_window_handle(self) -> int:
        """
        视频容器的原生窗口句柄。
        视频适配器通过此句柄将帧渲染到窗口中。
        :return: 原生窗口句柄（int）
        """
        return int(self._video_container.winId())

    @property
    def is_showing_video(self) -> bool:
        """当前是否正在显示视频。"""
        return self._is_showing_video

    @property
    def web_container(self) -> QWidget:
        """
        网页渲染容器 widget。
        WebSourceAdapter 将 QWebEngineView 创建为此容器的子组件，
        从而支持鼠标点击、滚动等交互操作。
        :return: 网页容器 QWidget
        """
        return self._web_container

    # ═══════════════════ 窗口定位 ═══════════════════

    @Slot(QRect)
    def position_on_display(self, geometry: QRect) -> None:
        """
        将窗口定位到指定的屏幕矩形区域。
        :param geometry: QRect，屏幕的绝对坐标矩形
        """
        self.setGeometry(geometry)
        if not self._debug_mode:
            self.showFullScreen()
        else:
            self.show()
        logger.info(
            "窗口 [%d] 定位到 (%d, %d) %dx%d",
            self._window_id,
            geometry.x(), geometry.y(),
            geometry.width(), geometry.height(),
        )

    # ═══════════════════ 视频显示控制 ═══════════════════

    @Slot()
    def show_video_container(self) -> None:
        """切换到视频显示模式：隐藏黑屏和网页容器，显示视频渲染容器。"""
        self._background_label.hide()
        self._web_container.hide()
        self._video_container.show()
        self._stacked_layout.setCurrentWidget(self._video_container)
        self._is_showing_video = True
        logger.debug("窗口 [%d] 切换到视频模式", self._window_id)

    @Slot()
    def show_web_container(self) -> None:
        """
        切换到网页显示模式：隐藏黑屏和视频容器，显示网页渲染容器。
        网页容器不使用 WA_NativeWindow，因此 QWebEngineView 能正常接收
        鼠标点击、滚动、键盘输入等用户交互事件。
        """
        self._background_label.hide()
        self._video_container.hide()
        self._web_container.show()
        self._stacked_layout.setCurrentWidget(self._web_container)
        self._is_showing_video = True
        logger.debug("窗口 [%d] 切换到网页模式", self._window_id)

    @Slot()
    def show_black_screen(self) -> None:
        """切换到黑屏模式：隐藏视频和网页容器，显示纯黑背景。"""
        self._video_container.hide()
        self._web_container.hide()
        self._background_label.show()
        self._background_label.clear()
        self._background_label.setStyleSheet("background-color: #000000;")
        self._stacked_layout.setCurrentWidget(self._background_label)
        self._is_showing_video = False
        logger.debug("窗口 [%d] 切换到黑屏模式", self._window_id)

    @Slot()
    def stop_all(self) -> None:
        """停止所有显示内容并回到黑屏。"""
        self.show_black_screen()
        logger.info("窗口 [%d] 已停止所有内容", self._window_id)

    @Slot()
    def hide_window(self) -> None:
        """隐藏窗口但不销毁。"""
        self.hide()

    # ═══════════════════ 窗口 ID 覆盖层 ═══════════════════

    @Slot()
    def show_id_overlay(self) -> None:
        """
        显示窗口 ID 覆盖层，5 秒后自动隐藏。
        若已显示则重置计时器。
        """
        self._center_overlay()
        self._overlay_label.show()
        self._overlay_label.raise_()
        # 重置计时器（如果已在倒计时则重新开始）
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

    # ═══════════════════ 事件处理 ═══════════════════

    def resizeEvent(self, event: object) -> None:
        """窗口尺寸变化时重新居中覆盖层。"""
        super().resizeEvent(event)
        if self._overlay_label.isVisible():
            self._center_overlay()

    def closeEvent(self, event: object) -> None:
        """窗口关闭时停止所有内容。"""
        self.stop_all()
        self.window_closed.emit()
        super().closeEvent(event)

    def keyPressEvent(self, event: object) -> None:
        """按 Escape 退出全屏或关闭窗口。"""
        from PySide6.QtCore import Qt as QtKey
        if hasattr(event, 'key') and event.key() == QtKey.Key.Key_Escape:
            if self._debug_mode:
                self.close()
            else:
                logger.info("正常模式下按下 Escape，忽略")
        else:
            super().keyPressEvent(event)
