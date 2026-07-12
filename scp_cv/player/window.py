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

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QLabel,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

from scp_cv.player.window_display import (
    DEBUG_PREVIEW_CASCADE_OFFSET_PX,
    DEBUG_PREVIEW_MAX_SCREEN_RATIO,
    RENDER_RESIZE_DEBOUNCE_MS,
    PlayerWindowDisplayMixin,
)
from scp_cv.player.window_interactions import (
    CURSOR_IDLE_HIDE_DELAY_MS,
    OVERLAY_DISPLAY_DURATION_MS,
    PlayerWindowInteractionMixin,
)

logger = logging.getLogger(__name__)


class PlayerWindow(
    PlayerWindowInteractionMixin,
    PlayerWindowDisplayMixin,
    QWidget,
):
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
    render_viewport_resized = Signal(int, int, int)

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

        # 主 layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addLayout(self._stacked_layout)

        self._initialize_window_interactions()
        self._initialize_display_runtime()

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

    # ═══════════════════ 事件处理 ═══════════════════

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


__all__ = [
    "CURSOR_IDLE_HIDE_DELAY_MS",
    "DEBUG_PREVIEW_CASCADE_OFFSET_PX",
    "DEBUG_PREVIEW_MAX_SCREEN_RATIO",
    "OVERLAY_DISPLAY_DURATION_MS",
    "PlayerWindow",
    "RENDER_RESIZE_DEBOUNCE_MS",
]
