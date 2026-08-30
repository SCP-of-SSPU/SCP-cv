#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
播放器显示布局与窗口重建逻辑。
@Project : SCP-cv
@File : controller_display.py
@Author : Qintsg
@Date : 2026-08-30
'''
from __future__ import annotations

import logging

from PySide6.QtCore import QRect, Slot

logger = logging.getLogger(__name__)


class PlayerDisplayLayoutMixin:
    """提供显示目标变更、布局恢复和窗口重建行为。"""

    @Slot(int, QRect)
    def _reposition_window(self, window_id: int, rect: QRect) -> None:
        """在 Qt 主线程把显示目标变更应用到对应窗口。"""
        window = self._windows.get(window_id)
        if window is not None:
            window.position_on_display(rect)

    def apply_display_positions(self) -> None:
        """根据各窗口会话的显示配置定位所有窗口。"""
        from scp_cv.services.display import list_display_targets
        from scp_cv.services.playback import get_or_create_session

        display_targets = list_display_targets()
        for window_id, window in self._windows.items():
            session = get_or_create_session(window_id)
            target_label = session.target_display_label
            if not target_label:
                continue
            matched_display = next((dt for dt in display_targets if dt.name == target_label), None)
            if matched_display is not None:
                window.position_on_display(
                    QRect(matched_display.x, matched_display.y, matched_display.width, matched_display.height)
                )

    def apply_current_layout(self) -> None:
        """按数据库中持久化的显示器目标恢复播放器窗口位置。"""
        self.apply_display_positions()

    def rebuild_registered_windows(self) -> None:
        """关闭并替换当前已注册窗口，然后按持久化显示配置重新显示。"""
        from scp_cv.player.window import PlayerWindow

        qt_app, previous_quit_on_last_window = self._disable_qt_last_window_auto_quit()
        old_windows = list(self._windows.items())
        try:
            self._windows = {}
            for window_id, old_window in old_windows:
                self._disconnect_window_signals(old_window)
                if hasattr(old_window, "close_for_rebuild"):
                    old_window.close_for_rebuild()
                else:
                    old_window.hide()
                    old_window.deleteLater()
                logger.info("窗口 %d 已为全局重置关闭", window_id)
            for window_id, old_window in old_windows:
                debug_mode = bool(getattr(old_window, "debug_mode", False))
                new_window = PlayerWindow(window_id=window_id, debug_mode=debug_mode)
                self.register_window(window_id, new_window)
                if debug_mode:
                    new_window.resize(960, 540)
                    new_window.show()
            self.apply_current_layout()
        finally:
            self._restore_qt_last_window_auto_quit(qt_app, previous_quit_on_last_window)
        logger.info("已按当前显示配置重建 %d 个播放器窗口", len(old_windows))

    @staticmethod
    def _disable_qt_last_window_auto_quit() -> tuple[object | None, bool | None]:
        """重建窗口期间暂时关闭 Qt 最后窗口关闭即退出。"""
        try:
            from PySide6.QtWidgets import QApplication
        except Exception as import_error:
            logger.debug("Qt 应用不可用，跳过自动退出保护：%s", import_error)
            return None, None
        qt_app = QApplication.instance()
        if qt_app is None:
            return None, None
        previous = bool(qt_app.quitOnLastWindowClosed())
        qt_app.setQuitOnLastWindowClosed(False)
        return qt_app, previous

    @staticmethod
    def _restore_qt_last_window_auto_quit(
        qt_app: object | None,
        previous_quit_on_last_window: bool | None,
    ) -> None:
        """恢复 Qt 自动退出设置。"""
        if qt_app is None or previous_quit_on_last_window is None:
            return
        try:
            qt_app.setQuitOnLastWindowClosed(previous_quit_on_last_window)
        except RuntimeError as restore_error:
            logger.debug("恢复 Qt 自动退出设置失败：%s", restore_error)

    def _disconnect_window_signals(self, player_window: object) -> None:
        """断开控制器持有的窗口信号。"""
        try:
            self.sig_stop_all.disconnect(player_window.stop_all)
        except (RuntimeError, TypeError):
            pass
        if self._window_closed_callback is not None:
            try:
                player_window.window_closed.disconnect(self._window_closed_callback)
            except (RuntimeError, TypeError):
                pass


__all__ = ["PlayerDisplayLayoutMixin"]
