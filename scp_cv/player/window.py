#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
播放器显示窗口：每物理屏幕一个实例，支持全屏/无边框/置顶。
视频通过 QMediaPlayer 渲染到嵌入的原生容器中。
@Project : SCP-cv
@File : window.py
@Author : Qintsg
@Date : 2026-04-14
'''
from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import QRect, Qt, Signal, Slot
from PySide6.QtWidgets import (
    QLabel,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)


class PlayerWindow(QWidget):
    """
    播放器显示窗口。每个物理屏幕对应一个实例。

    职责：
    - 全屏/无边框/置顶（正常模式）或可调窗口（DEBUG 模式）
    - 提供原生窗口句柄供视频渲染
    - 显示器定位（坐标和尺寸由外部控制器指定）

    与视频管线的交互：
    - 通过 video_window_handle 属性提供渲染目标
    - 视频管线的创建和生命周期由 PlayerController 管理
    """

    # 信号：外部可监听窗口关闭
    window_closed = Signal()

    def __init__(
        self,
        window_id: str = "",
        debug_mode: bool = False,
        parent: Optional[QWidget] = None,
    ) -> None:
        """
        初始化播放器窗口。
        :param window_id: 窗口标识符（如 "left"/"right"/"single"）
        :param debug_mode: True 时不强制全屏/置顶，方便调试
        :param parent: 父 widget
        """
        super().__init__(parent)
        self._window_id = window_id
        self._debug_mode = debug_mode
        self._is_showing_video = False

        # ═══ 窗口属性 ═══
        title_suffix = f" [{window_id}]" if window_id else ""
        self.setWindowTitle(f"SCP-cv 播放器{title_suffix}")
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

        # 顶层：视频渲染容器（原生窗口）
        self._video_container = QWidget()
        self._video_container.setAttribute(
            Qt.WidgetAttribute.WA_NativeWindow, True,
        )
        self._video_container.setStyleSheet("background-color: #000000;")
        self._video_container.hide()
        self._stacked_layout.addWidget(self._video_container)

        # 主 layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addLayout(self._stacked_layout)

        logger.info(
            "播放器窗口已初始化（id=%s, debug=%s）",
            window_id or "default",
            "开" if debug_mode else "关",
        )

    @property
    def window_id(self) -> str:
        """窗口标识符。"""
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
            "窗口 [%s] 定位到 (%d, %d) %dx%d",
            self._window_id,
            geometry.x(), geometry.y(),
            geometry.width(), geometry.height(),
        )

    # ═══════════════════ 视频显示控制 ═══════════════════

    @Slot()
    def show_video_container(self) -> None:
        """切换到视频显示模式：隐藏黑屏，显示视频渲染容器。"""
        self._background_label.hide()
        self._video_container.show()
        self._stacked_layout.setCurrentWidget(self._video_container)
        self._is_showing_video = True
        logger.debug("窗口 [%s] 切换到视频模式", self._window_id)

    @Slot()
    def show_black_screen(self) -> None:
        """切换到黑屏模式：隐藏视频容器，显示纯黑背景。"""
        self._video_container.hide()
        self._background_label.show()
        self._background_label.clear()
        self._background_label.setStyleSheet("background-color: #000000;")
        self._stacked_layout.setCurrentWidget(self._background_label)
        self._is_showing_video = False
        logger.debug("窗口 [%s] 切换到黑屏模式", self._window_id)

    @Slot()
    def stop_all(self) -> None:
        """停止所有显示内容并回到黑屏。"""
        self.show_black_screen()
        logger.info("窗口 [%s] 已停止所有内容", self._window_id)

    @Slot()
    def hide_window(self) -> None:
        """隐藏窗口但不销毁。"""
        self.hide()

    # ═══════════════════ 事件处理 ═══════════════════

    def resizeEvent(self, event: object) -> None:
        """窗口尺寸变化时处理布局更新。"""
        super().resizeEvent(event)

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
