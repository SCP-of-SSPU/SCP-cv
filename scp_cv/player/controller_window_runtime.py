#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PlayerController 的窗口运行时深模块。

集中维护 PlayerWindow 注册、显示布局、重建、渲染尺寸同步，以及活动
Adapter 状态向 PlaybackSession 的投影。调用方仍只通过 PlayerController
使用这些接口。
@Project : SCP-cv
@File : controller_window_runtime.py
@Author : Qintsg
@Date : 2026-07-11
'''
from __future__ import annotations

import logging
import threading
from typing import Callable, Optional

from PySide6.QtCore import QRect, Slot

from scp_cv.player.adapters import SourceAdapter
from scp_cv.player.controller_window_helpers import PlayerWindowHelpersMixin

logger = logging.getLogger(__name__)


class PlayerWindowRuntimeMixin(PlayerWindowHelpersMixin):
    """封装窗口生命周期及窗口 Adapter 状态同步。"""

    def _initialize_window_runtime(self) -> None:
        """初始化窗口注册表和 Adapter 状态投影缓存。"""
        self._windows: dict[int, object] = {}
        self._adapters: dict[int, SourceAdapter] = {}
        self._adapter_source_types: dict[int, str] = {}
        self._adapter_source_ids: dict[int, int] = {}
        self._window_closed_callback: Callable[[], None] | None = None
        self._last_reported_states: dict[
            int, tuple[str, str, int, int, int, int]
        ] = {}
        self._state_report_pending = False
        self._state_report_lock = threading.Lock()

    def set_window_closed_callback(self, callback: Callable[[], None] | None) -> None:
        """
        设置窗口被用户关闭时的统一回调。
        :param callback: 关闭回调；None 表示不处理窗口关闭事件
        :return: None
        """
        self._window_closed_callback = callback

    def register_window(self, window_id: int, player_window: object) -> None:
        """
        注册播放器窗口到控制器。
        :param window_id: 窗口编号（1-4）
        :param player_window: PlayerWindow 实例
        """
        from scp_cv.player.window import PlayerWindow

        if not isinstance(player_window, PlayerWindow):
            raise TypeError("需要 PlayerWindow 实例")

        self._windows[window_id] = player_window
        self.sig_stop_all.connect(player_window.stop_all)
        resize_signal = getattr(player_window, "render_viewport_resized", None)
        if resize_signal is not None:
            resize_signal.connect(self._resize_adapter_output)
        if self._window_closed_callback is not None:
            player_window.window_closed.connect(self._window_closed_callback)
        logger.info("控制器已注册窗口：%d", window_id)

    @Slot(int, int, int)
    def _resize_adapter_output(self, window_id: int, width: int, height: int) -> None:
        """把 Player 渲染客户区变化同步给当前窗口 Adapter。"""
        adapter = self._adapters.get(window_id)
        if adapter is None or not bool(getattr(adapter, "is_open", False)):
            return
        try:
            adapter.resize_output(max(1, int(width)), max(1, int(height)))
        except Exception as resize_error:
            logger.warning(
                "窗口 %d 同步 Adapter 输出尺寸失败：%s",
                window_id,
                resize_error,
            )

    def get_window(self, window_id: int) -> Optional[object]:
        """
        获取指定编号的窗口实例。
        :param window_id: 窗口编号（1-4）
        :return: PlayerWindow 实例，不存在时返回 None
        """
        return self._windows.get(window_id)

    def get_window_handle(self, window_id: int) -> int:
        """
        获取指定窗口的原生句柄。
        :param window_id: 窗口编号（1-4）
        :return: 窗口句柄（int），无窗口时返回 0
        """
        window = self._windows.get(window_id)
        if window is not None:
            return window.video_window_handle
        return 0

    @property
    def registered_window_ids(self) -> list[int]:
        """已注册的窗口编号列表（排序后）。"""
        return sorted(self._windows.keys())

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

            matched_display = next(
                (display for display in display_targets if display.name == target_label),
                None,
            )
            if matched_display is not None:
                rect = QRect(
                    matched_display.x,
                    matched_display.y,
                    matched_display.width,
                    matched_display.height,
                )
                window.position_on_display(rect)

    def apply_current_layout(self) -> None:
        """按数据库中持久化的显示器目标恢复播放器窗口位置。"""
        self.apply_display_positions()

    def rebuild_registered_windows(self) -> None:
        """
        关闭并替换当前已注册窗口，然后按持久化显示配置重新显示。
        :return: None
        """
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
                    new_window.show()

            self.apply_current_layout()
        finally:
            self._restore_qt_last_window_auto_quit(
                qt_app,
                previous_quit_on_last_window,
            )
        logger.info("已按当前显示配置重建 %d 个播放器窗口", len(old_windows))

    @staticmethod
    def _disable_qt_last_window_auto_quit() -> tuple[object | None, bool | None]:
        """
        重建播放窗口期间暂时关闭 Qt 最后窗口关闭即退出，避免启动重置导致播放器退出。
        :return: QApplication 实例和原设置；不可用时均为空
        """
        try:
            from PySide6.QtWidgets import QApplication
        except Exception as import_error:
            logger.debug("Qt 应用不可用，跳过自动退出保护：%s", import_error)
            return None, None
        qt_app = QApplication.instance()
        if qt_app is None:
            return None, None
        previous_quit_on_last_window = bool(qt_app.quitOnLastWindowClosed())
        qt_app.setQuitOnLastWindowClosed(False)
        return qt_app, previous_quit_on_last_window

    @staticmethod
    def _restore_qt_last_window_auto_quit(
        qt_app: object | None,
        previous_quit_on_last_window: bool | None,
    ) -> None:
        """
        恢复 Qt 最后窗口关闭即退出原设置。
        :param qt_app: QApplication 实例
        :param previous_quit_on_last_window: 原设置
        :return: None
        """
        if qt_app is None or previous_quit_on_last_window is None:
            return
        try:
            qt_app.setQuitOnLastWindowClosed(previous_quit_on_last_window)
        except RuntimeError as restore_error:
            logger.debug("恢复 Qt 自动退出设置失败：%s", restore_error)

    def _disconnect_window_signals(self, player_window: object) -> None:
        """
        断开控制器持有的窗口信号，避免旧窗口销毁后继续响应广播。
        :param player_window: 待销毁的 PlayerWindow 实例
        :return: None
        """
        try:
            self.sig_stop_all.disconnect(player_window.stop_all)
        except (RuntimeError, TypeError):
            pass
        resize_signal = getattr(player_window, "render_viewport_resized", None)
        if resize_signal is not None:
            try:
                resize_signal.disconnect(self._resize_adapter_output)
            except (RuntimeError, TypeError):
                pass
        if self._window_closed_callback is not None:
            try:
                player_window.window_closed.disconnect(self._window_closed_callback)
            except (RuntimeError, TypeError):
                pass

    def _request_adapter_state_report(self) -> None:
        """请求 Qt 主线程上报适配器状态，避免跨线程访问 Qt 对象。"""
        with self._state_report_lock:
            if self._state_report_pending:
                return
            self._state_report_pending = True
        self.sig_report_states.emit()

    @Slot()
    def _report_all_adapter_states(self) -> None:
        """在 Qt 主线程读取所有活跃适配器状态并回写到 DB。"""
        from scp_cv.services.playback import update_playback_progress

        try:
            for window_id, adapter in self._adapters.items():
                if adapter is None or not adapter.is_open:
                    continue
                if not self._adapter_matches_current_session(window_id):
                    logger.debug("窗口 %d adapter 源已过期，跳过本次状态上报", window_id)
                    continue
                try:
                    adapter_state = adapter.get_state()
                except Exception as state_error:
                    logger.warning("窗口 %d 读取适配器状态失败：%s", window_id, state_error)
                    if self._should_persist_adapter_state_error(window_id, adapter):
                        error_message = f"PowerPoint Broker 状态读取失败：{state_error}"
                        error_signature = (
                            "error",
                            error_message,
                            0,
                            0,
                            0,
                            0,
                        )
                        if self._last_reported_states.get(window_id) != error_signature:
                            self._update_session_error(window_id, error_message)
                            self._last_reported_states[window_id] = error_signature
                    continue
                state_signature = (
                    adapter_state.playback_state,
                    adapter_state.error_message,
                    adapter_state.current_slide,
                    adapter_state.total_slides,
                    adapter_state.position_ms,
                    adapter_state.duration_ms,
                )
                if state_signature == self._last_reported_states.get(window_id):
                    continue

                update_playback_progress(
                    window_id=window_id,
                    playback_state=adapter_state.playback_state,
                    error_message=adapter_state.error_message,
                    current_slide=adapter_state.current_slide,
                    total_slides=adapter_state.total_slides,
                    position_ms=adapter_state.position_ms,
                    duration_ms=adapter_state.duration_ms,
                )
                self._last_reported_states[window_id] = state_signature
            if self._enable_background_audio:
                self._report_background_audio_state()
        finally:
            with self._state_report_lock:
                self._state_report_pending = False

    def _adapter_matches_current_session(self, window_id: int) -> bool:
        """
        判断 adapter 是否仍对应当前会话源。
        :param window_id: 窗口编号
        :return: True 表示允许该 adapter 状态写回数据库
        """
        expected_source_id = self._adapter_source_ids.get(window_id)
        if expected_source_id is None:
            return True

        from scp_cv.apps.playback.models import PlaybackSession

        session = (
            PlaybackSession.objects.filter(window_id=window_id)
            .only("media_source_id")
            .first()
        )
        return session is not None and session.media_source_id == expected_source_id

    def _should_persist_adapter_state_error(
        self,
        window_id: int,
        adapter: object,
    ) -> bool:
        """仅把 PPT Broker 断连类状态错误提升为会话错误。"""
        if self._adapter_source_types.get(window_id) == "ppt":
            return True
        from scp_cv.player.adapters.ppt_broker import PptBrokerSourceAdapter

        return isinstance(adapter, PptBrokerSourceAdapter)


__all__ = ["PlayerWindowRuntimeMixin"]
