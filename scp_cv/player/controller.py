#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
播放器控制器：桥接 Django 数据库指令与适配器执行层。
通过轮询 PlaybackSession.pending_command 驱动适配器行为，
并将适配器状态回写到数据库供 Django 前端展示。

多窗口架构：每个输出窗口（window_id 1-4）独立管理一个适配器实例，
控制器同时轮询所有窗口的待执行指令并分发到 Qt 主线程。

线程模型：
- Qt 主线程：所有窗口操作、适配器创建和控制（通过信号分发）
- 轮询线程：定期读取 DB 中的 pending_command，发射信号到主线程

所有适配器操作（open / play / pause / stop / close / 导航）
均通过 Qt 信号从轮询线程调度到主线程执行，避免跨线程 GUI 操作。
@Project : SCP-cv
@File : controller.py
@Author : Qintsg
@Date : 2026-04-15
'''
from __future__ import annotations

import logging
import threading
import time
from typing import Callable, Optional

from PySide6.QtCore import QObject, QRect, Signal, Slot

from scp_cv.player.adapters import SourceAdapter
from scp_cv.player.controller_handlers import PlayerCommandHandlersMixin

logger = logging.getLogger(__name__)


class PlayerController(PlayerCommandHandlersMixin, QObject):
    """
    多窗口播放器控制器。

    职责：
    - 管理最多 4 个 PlayerWindow 实例（按 window_id 1-4 注册）
    - 每个窗口独立维护一个 SourceAdapter 实例
    - 轮询所有窗口的 DB pending_command 并通过信号分发到 Qt 主线程
    - 将适配器状态回写 DB
    - 窗口定位与显示模式切换

    线程安全：
    - 适配器操作全部在 Qt 主线程执行（through sig_dispatch_command）
    - 轮询线程只读 DB 并发射信号，不直接操作适配器
    """

    # 信号：工作线程 → Qt 主线程
    sig_show_video = Signal(int)       # window_id → 切换到视频模式
    sig_show_black = Signal(int)       # window_id → 切换到黑屏
    sig_stop_all = Signal()            # 停止所有窗口
    sig_reposition = Signal(int, QRect)  # window_id + 目标矩形

    # 轮询线程 → Qt 主线程：分发指令执行（携带 window_id）
    sig_dispatch_command = Signal(int, str, dict)  # (window_id, command, command_args)
    sig_report_states = Signal()                   # 轮询线程 → Qt 主线程：读取适配器状态

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)

        # 窗口映射：window_id(int) → PlayerWindow
        self._windows: dict[int, object] = {}

        # 适配器映射：window_id(int) → SourceAdapter（每窗口独立）
        self._adapters: dict[int, SourceAdapter] = {}
        # 适配器源类型记录：window_id → source_type
        self._adapter_source_types: dict[int, str] = {}
        # 适配器源 ID 记录：切源竞态中用于阻断旧 adapter 状态写回新会话。
        self._adapter_source_ids: dict[int, int] = {}
        # 网页源预热池：由 Qt 主线程创建和使用，避免切换网页源时重新首屏加载。
        self._web_preheat_pool: object | None = None
        # 非 dev 模式下由 run_player 注入关闭回调，窗口重建后仍需保持相同行为。
        self._window_closed_callback: Callable[[], None] | None = None

        # 轮询线程
        self._poll_thread: Optional[threading.Thread] = None
        self._poll_running = False

        # 每个窗口上一次已上报状态，避免轮询线程无变化时频繁写库。
        self._last_reported_states: dict[int, tuple[str, int, int, int, int]] = {}
        self._state_report_pending = False
        self._state_report_lock = threading.Lock()

        # 连接指令分发信号到主线程处理槽
        self.sig_dispatch_command.connect(self._execute_command_on_main_thread)
        self.sig_report_states.connect(self._report_all_adapter_states)

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
        if self._window_closed_callback is not None:
            player_window.window_closed.connect(self._window_closed_callback)
        logger.info("控制器已注册窗口：%d", window_id)

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

    # ═══════════════════ 轮询生命周期 ═══════════════════

    def start_polling(self, interval_seconds: float = 0.2) -> None:
        """
        启动后台轮询线程。
        :param interval_seconds: 轮询间隔（秒）
        """
        if self._poll_running:
            return

        self._poll_running = True
        self._poll_thread = threading.Thread(
            target=self._poll_loop,
            args=(interval_seconds,),
            daemon=True,
            name="player-poll",
        )
        self._poll_thread.start()
        logger.info("控制器轮询已启动（间隔 %.1fs）", interval_seconds)

    def stop_polling(self) -> None:
        """停止轮询并关闭所有适配器。"""
        self._poll_running = False
        if self._poll_thread is not None:
            self._poll_thread.join(timeout=3.0)
            self._poll_thread = None

        # 关闭所有窗口的适配器
        for wid in list(self._adapters.keys()):
            self._close_adapter(wid)
        if self._web_preheat_pool is not None:
            self._web_preheat_pool.close_all()
            self._web_preheat_pool = None
        logger.info("控制器轮询已停止")

    def preheat_web_sources(self) -> None:
        """
        启动时预热启用预热的网页源。
        :return: None
        """
        from scp_cv.apps.playback.models import MediaSource, SourceType
        from scp_cv.player.web_preheat import WebPreheatPool

        if self._web_preheat_pool is None:
            self._web_preheat_pool = WebPreheatPool()
        for source in MediaSource.objects.filter(
            source_type=SourceType.WEB,
            is_available=True,
            keep_alive=True,
        ).only("id", "uri"):
            self._web_preheat_pool.preheat_source(source.pk, source.uri)

    # ═══════════════════ 窗口定位 ═══════════════════

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
                (dt for dt in display_targets if dt.name == target_label),
                None,
            )
            if matched_display is not None:
                rect = QRect(
                    matched_display.x, matched_display.y,
                    matched_display.width, matched_display.height,
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

        old_windows = list(self._windows.items())
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
        logger.info("已按当前显示配置重建 %d 个播放器窗口", len(old_windows))

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
        if self._window_closed_callback is not None:
            try:
                player_window.window_closed.disconnect(self._window_closed_callback)
            except (RuntimeError, TypeError):
                pass

    # ═══════════════════ 轮询逻辑 ═══════════════════

    def _poll_loop(self, interval_seconds: float) -> None:
        """
        DB 轮询主循环：遍历所有已注册窗口，读取 pending_command → 发射信号。
        :param interval_seconds: 轮询间隔
        """
        import django
        django.setup()

        while self._poll_running:
            try:
                # 轮询所有已注册窗口的指令
                for window_id in self.registered_window_ids:
                    self._check_and_dispatch_command(window_id)
                # COM 和 Qt 状态读取必须回到适配器创建时所在的 Qt 主线程。
                self._request_adapter_state_report()
            except Exception as poll_error:
                logger.error("轮询处理异常：%s", poll_error)
            time.sleep(interval_seconds)

    def _request_adapter_state_report(self) -> None:
        """请求 Qt 主线程上报适配器状态，避免跨线程访问 COM/Qt 对象。"""
        with self._state_report_lock:
            if self._state_report_pending:
                return
            self._state_report_pending = True
        self.sig_report_states.emit()

    def _check_and_dispatch_command(self, window_id: int) -> None:
        """
        读取指定窗口 DB 中的待执行指令，通过信号发射到 Qt 主线程。
        :param window_id: 窗口编号
        """
        from scp_cv.apps.playback.models import PlaybackCommand, PlaybackSession

        session = PlaybackSession.objects.filter(window_id=window_id).first()
        if session is None:
            return

        pending = session.pending_command
        if not pending or pending == PlaybackCommand.NONE:
            return

        command_args = dict(session.command_args or {})

        logger.info(
            "窗口 %d 轮询检测到指令：%s，参数=%s，发射到主线程",
            window_id, pending, command_args,
        )

        # 通过 Qt 信号将指令调度到主线程执行（携带 window_id）
        self.sig_dispatch_command.emit(window_id, pending, dict(command_args))

        # 立即清除 DB 中的 pending_command
        from scp_cv.services.playback import clear_pending_command
        clear_pending_command(window_id)

    @Slot(int, str, dict)
    def _execute_command_on_main_thread(
        self,
        window_id: int,
        command: str,
        command_args: dict[str, object],
    ) -> None:
        """
        在 Qt 主线程上执行适配器指令。
        由 sig_dispatch_command 信号触发，保证所有 Qt 和 COM 操作
        在主线程执行，避免跨线程 GUI 操作错误。
        :param window_id: 目标窗口编号
        :param command: 指令名（PlaybackCommand 枚举值）
        :param command_args: 指令参数
        """
        from scp_cv.apps.playback.models import PlaybackCommand

        logger.info("主线程执行指令：窗口 %d → %s", window_id, command)

        command_dispatch: dict[str, object] = {
            PlaybackCommand.OPEN: self._handle_open,
            PlaybackCommand.PLAY: self._handle_play,
            PlaybackCommand.PAUSE: self._handle_pause,
            PlaybackCommand.STOP: self._handle_stop,
            PlaybackCommand.CLOSE: self._handle_close,
            PlaybackCommand.NEXT: self._handle_next,
            PlaybackCommand.PREV: self._handle_prev,
            PlaybackCommand.GOTO: self._handle_goto,
            PlaybackCommand.SEEK: self._handle_seek,
            PlaybackCommand.SET_LOOP: self._handle_set_loop,
            PlaybackCommand.SET_VOLUME: self._handle_set_volume,
            PlaybackCommand.SET_MUTE: self._handle_set_mute,
            PlaybackCommand.PPT_MEDIA: self._handle_ppt_media,
            PlaybackCommand.SHOW_ID: self._handle_show_id,
        }

        handler = command_dispatch.get(command)
        if handler is not None:
            try:
                handler(window_id, command_args)
            except Exception as cmd_error:
                logger.error("执行指令 %s（窗口 %d）失败：%s", command, window_id, cmd_error)
                self._update_session_error(window_id, str(cmd_error))

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
        session = PlaybackSession.objects.filter(window_id=window_id).only("media_source_id").first()
        return session is not None and session.media_source_id == expected_source_id
