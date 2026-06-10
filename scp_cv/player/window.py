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

from PySide6.QtCore import QEvent, QRect, QTimer, Qt, Signal, Slot
from PySide6.QtGui import QFont, QGuiApplication, QScreen
from PySide6.QtWidgets import (
    QLabel,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)

# 窗口 ID 覆盖层显示时长（毫秒）
OVERLAY_DISPLAY_DURATION_MS = 5000

# 鼠标在播放窗口内静止后隐藏光标的等待时长（毫秒）
CURSOR_IDLE_HIDE_DELAY_MS = 5000


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
        self._suppress_close_signal = False
        self._cursor_hidden = False
        self._cursor_tracked_widgets: set[int] = set()

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

        self._video_viewport = QWidget()
        self._video_viewport.setStyleSheet("background-color: #000000;")
        self._video_viewport.hide()
        self._stacked_layout.addWidget(self._video_viewport)

        self._video_container = QWidget(self._video_viewport)
        self._video_container.setAttribute(
            Qt.WidgetAttribute.WA_NativeWindow, True,
        )
        self._video_container.setStyleSheet("background-color: #000000;")

        # 网页渲染容器同样放在裁剪视口内，保证网页/图片/PPT 逻辑一致。
        self._web_viewport = QWidget()
        self._web_viewport.setStyleSheet("background-color: #000000;")
        self._web_viewport.hide()
        self._stacked_layout.addWidget(self._web_viewport)

        self._web_container = QWidget(self._web_viewport)
        self._web_container.setStyleSheet("background-color: #000000;")
        # 启用鼠标追踪，确保 QWebEngineView 子组件能接收鼠标事件
        self._web_container.setMouseTracking(True)
        self._web_container.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._apply_render_viewport_geometry()

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

        self._cursor_idle_timer = QTimer(self)
        self._cursor_idle_timer.setSingleShot(True)
        self._cursor_idle_timer.timeout.connect(self._hide_idle_cursor)
        self._install_cursor_tracking()

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
    def top_level_window_handle(self) -> int:
        """
        播放器顶层窗口原生句柄。
        :return: 顶层窗口 HWND
        """
        return int(self.winId())

    @property
    def is_showing_video(self) -> bool:
        """当前是否正在显示视频。"""
        return self._is_showing_video

    @property
    def debug_mode(self) -> bool:
        """当前窗口是否使用开发调试模式。"""
        return self._debug_mode

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
        target_geometry = self._normalize_qt_geometry(geometry)
        window_handle = self.windowHandle()
        target_screen = self._screen_for_geometry(target_geometry)
        if window_handle is not None and target_screen is not None:
            window_handle.setScreen(target_screen)

        self.setFixedSize(target_geometry.size())
        self.move(target_geometry.topLeft())
        self.resize(target_geometry.size())
        self.setGeometry(target_geometry)
        self._apply_render_viewport_geometry()
        if not self._debug_mode:
            self.show()
            self.raise_()
        else:
            self.show()
        logger.info(
            "窗口 [%d] 定位到 Qt 屏幕区域 (%d, %d) %dx%d",
            self._window_id,
            target_geometry.x(), target_geometry.y(),
            target_geometry.width(), target_geometry.height(),
        )

    @staticmethod
    def _normalize_qt_geometry(requested_geometry: QRect) -> QRect:
        """
        将外部显示器坐标归一到 Qt 坐标系，避免高 DPI 下窗口跨屏放大。
        :param requested_geometry: 外部检测到的目标几何
        :return: 更适合 Qt 窗口定位的几何
        """
        matched_screen = PlayerWindow._screen_for_geometry(requested_geometry)
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

    # ═══════════════════ 视频显示控制 ═══════════════════

    @Slot()
    def show_video_container(self) -> None:
        """切换到视频显示模式：隐藏黑屏和网页容器，显示视频渲染容器。"""
        self._background_label.hide()
        self._web_viewport.hide()
        self._video_viewport.show()
        self._video_container.show()
        self._stacked_layout.setCurrentWidget(self._video_viewport)
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
        self._video_viewport.hide()
        self._web_viewport.show()
        self._web_container.show()
        self._stacked_layout.setCurrentWidget(self._web_viewport)
        self._is_showing_video = True
        logger.debug("窗口 [%d] 切换到网页模式", self._window_id)

    @Slot()
    def show_black_screen(self) -> None:
        """切换到黑屏模式：隐藏视频和网页容器，显示纯黑背景。"""
        self._video_viewport.hide()
        self._web_viewport.hide()
        self._background_label.show()
        self._background_label.clear()
        self._background_label.setStyleSheet("background-color: #000000;")
        self._stacked_layout.setCurrentWidget(self._background_label)
        self._is_showing_video = False
        logger.debug("窗口 [%d] 切换到黑屏模式", self._window_id)

    def prepare_ppt_container(self) -> None:
        """
        首次启动 PowerPoint 放映前激活渲染容器，确保嵌入容器矩形已稳定。
        :return: None
        """
        self.show_video_container()
        self._apply_render_viewport_geometry()
        self.show()
        self.raise_()
        self._flush_window_events()
        logger.debug("窗口 [%d] 已激活 PPT 嵌入容器", self._window_id)

    @Slot()
    def stop_all(self) -> None:
        """停止所有显示内容并回到黑屏。"""
        self.show_black_screen()
        logger.info("窗口 [%d] 已停止所有内容", self._window_id)

    @Slot(bool)
    def set_always_on_top(self, enabled: bool) -> None:
        """
        调整播放器窗口置顶状态。
        :param enabled: True 表示置顶，False 表示取消置顶
        :return: None
        """
        if not self._apply_win32_topmost(enabled):
            self._apply_qt_topmost(enabled)

    def _apply_win32_topmost(self, enabled: bool) -> bool:
        """
        通过 Win32 SetWindowPos 调整置顶，避免 Qt flag 变更导致窗口闪烁。
        :param enabled: 是否置顶
        :return: True 表示已通过 Win32 应用
        """
        try:
            import win32con
            import win32gui
        except Exception:
            return False
        try:
            hwnd = self.top_level_window_handle
            insert_after = win32con.HWND_TOPMOST if enabled else win32con.HWND_NOTOPMOST
            win32gui.SetWindowPos(
                hwnd,
                insert_after,
                0,
                0,
                0,
                0,
                win32con.SWP_NOMOVE
                | win32con.SWP_NOSIZE
                | win32con.SWP_NOACTIVATE
                | win32con.SWP_SHOWWINDOW,
            )
            return True
        except Exception as topmost_error:
            logger.debug("窗口 [%d] Win32 置顶调整失败：%s", self._window_id, topmost_error)
            return False

    def _apply_qt_topmost(self, enabled: bool) -> None:
        """
        Win32 不可用时回退到 Qt window flags 调整。
        :param enabled: 是否置顶
        :return: None
        """
        if self._debug_mode:
            return
        was_visible = self.isVisible()
        flags = self.windowFlags()
        if enabled:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        else:
            flags &= ~Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        if was_visible:
            self.show()

    def close_for_rebuild(self) -> None:
        """
        为全局重置关闭窗口，不触发用户关闭导致的应用退出回调。
        :return: None
        """
        self._suppress_close_signal = True
        try:
            self.close()
            self.deleteLater()
        finally:
            self._suppress_close_signal = False

    # ═══════════════════ 鼠标光标自动隐藏 ═══════════════════

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

    def _apply_render_viewport_geometry(self) -> None:
        """根据当前窗口尺寸更新渲染容器几何。"""
        viewport_width = max(1, self.width())
        viewport_height = max(1, self.height())
        self._video_container.setGeometry(0, 0, viewport_width, viewport_height)
        self._web_container.setGeometry(0, 0, viewport_width, viewport_height)

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

    # ═══════════════════ 事件处理 ═══════════════════

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
        if hasattr(event, "added") and hasattr(event, "child") and event.added():
            child = event.child()
            if isinstance(child, QWidget):
                self._track_cursor_widget(child)

    def resizeEvent(self, event: object) -> None:
        """窗口尺寸变化时重新居中覆盖层。"""
        super().resizeEvent(event)
        self._apply_render_viewport_geometry()
        if self._overlay_label.isVisible():
            self._center_overlay()

    def closeEvent(self, event: object) -> None:
        """窗口关闭时停止所有内容。"""
        self.stop_all()
        if not self._suppress_close_signal:
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
