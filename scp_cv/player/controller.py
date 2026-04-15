#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
播放器控制器：桥接 Django 数据库指令与适配器执行层。
通过轮询 PlaybackSession.pending_command 驱动适配器行为，
并将适配器状态回写到数据库供 Django 前端展示。

线程模型：
- Qt 主线程：所有窗口操作、适配器创建和控制（通过信号分发）
- 轮询线程：定期读取 DB 中的 pending_command，发射信号到主线程
- GLib 事件泵：QTimer 驱动 GLib.MainContext 迭代，处理 GStreamer 内部回调

所有适配器操作（open / play / pause / stop / close / 导航）
均通过 Qt 信号从轮询线程调度到主线程执行，避免跨线程 GUI 操作。
@Project : SCP-cv
@File : controller.py
@Author : Qintsg
@Date : 2026-04-15
'''
from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from typing import Optional

from PySide6.QtCore import QObject, QRect, QTimer, Signal, Slot

from scp_cv.player.adapters import AdapterState, SourceAdapter, create_adapter

logger = logging.getLogger(__name__)

# GLib 事件泵间隔（毫秒），驱动 GStreamer 信号分发
_GLIB_PUMP_INTERVAL_MS: int = 10


class PlayerController(QObject):
    """
    统一播放器控制器。

    职责：
    - 管理 PlayerWindow 实例（单屏 1 个，拼接 2 个）
    - 轮询 DB 中的 pending_command 并通过信号分发到 Qt 主线程
    - 将适配器状态回写 DB
    - 窗口定位与显示模式切换
    - GLib 事件泵驱动 GStreamer 内部回调

    线程安全：
    - 适配器操作全部在 Qt 主线程执行（through sig_dispatch_command）
    - 轮询线程只读 DB 并发射信号，不直接操作适配器
    """

    # 信号：工作线程 → Qt 主线程
    sig_show_video = Signal(str)       # 窗口 ID → 切换到视频模式
    sig_show_black = Signal(str)       # 窗口 ID → 切换到黑屏
    sig_stop_all = Signal()            # 停止所有窗口
    sig_reposition = Signal(str, QRect)  # 窗口 ID + 目标矩形

    # 轮询线程 → Qt 主线程：分发指令执行
    sig_dispatch_command = Signal(str, dict)  # (command, command_args)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)

        # 窗口映射：window_id → PlayerWindow
        self._windows: dict[str, object] = {}

        # 当前活跃适配器（同一时间只有一个源在播放）
        self._current_adapter: Optional[SourceAdapter] = None
        self._current_source_type: str = ""

        # 轮询线程
        self._poll_thread: Optional[threading.Thread] = None
        self._poll_running = False

        # 上一次处理的指令 hash（避免重复处理同一指令）
        self._last_command_hash = ""

        # GLib 事件泵定时器（驱动 GStreamer webrtcbin 信号分发）
        self._glib_pump_timer: Optional[QTimer] = None

        # 连接指令分发信号到主线程处理槽
        self.sig_dispatch_command.connect(self._execute_command_on_main_thread)

    def register_window(self, window_id: str, player_window: object) -> None:
        """
        注册播放器窗口到控制器。
        :param window_id: 窗口标识符（如 "single"、"left"、"right"）
        :param player_window: PlayerWindow 实例
        """
        from scp_cv.player.window import PlayerWindow
        if not isinstance(player_window, PlayerWindow):
            raise TypeError("需要 PlayerWindow 实例")

        self._windows[window_id] = player_window
        self.sig_stop_all.connect(player_window.stop_all)
        logger.info("控制器已注册窗口：%s", window_id)

    def get_primary_window(self) -> Optional[object]:
        """
        获取主窗口（单屏的 "single" 或第一个注册窗口）。
        :return: PlayerWindow 实例，无窗口时返回 None
        """
        primary_window = self._windows.get("single")
        if primary_window is None and self._windows:
            primary_window = next(iter(self._windows.values()))
        return primary_window

    def get_primary_window_handle(self) -> int:
        """
        获取主窗口的原生句柄。
        :return: 窗口句柄（int），无窗口时返回 0
        """
        primary_window = self.get_primary_window()
        if primary_window is not None:
            return primary_window.video_window_handle
        return 0

    # ═══════════════════ GLib 事件泵 ═══════════════════

    def _start_glib_pump(self) -> None:
        """
        启动 GLib 事件泵。通过 QTimer 周期性迭代 GLib.MainContext，
        使 GStreamer webrtcbin 的异步信号（ICE 候选收集、协商回调等）
        能在 Qt 事件循环中被处理。
        """
        if self._glib_pump_timer is not None:
            return

        self._glib_pump_timer = QTimer(self)
        self._glib_pump_timer.setInterval(_GLIB_PUMP_INTERVAL_MS)
        self._glib_pump_timer.timeout.connect(self._pump_glib_events)
        self._glib_pump_timer.start()
        logger.info("GLib 事件泵已启动（间隔 %dms）", _GLIB_PUMP_INTERVAL_MS)

    def _stop_glib_pump(self) -> None:
        """停止 GLib 事件泵。"""
        if self._glib_pump_timer is not None:
            self._glib_pump_timer.stop()
            self._glib_pump_timer.deleteLater()
            self._glib_pump_timer = None
            logger.info("GLib 事件泵已停止")

    @Slot()
    def _pump_glib_events(self) -> None:
        """
        迭代 GLib 默认 MainContext 中的待处理事件。
        每次最多处理所有排队事件，避免阻塞 Qt 事件循环。
        """
        try:
            from gi.repository import GLib
            context = GLib.MainContext.default()
            # 非阻塞迭代：处理所有已就绪事件
            while context.iteration(False):
                pass
        except ImportError:
            # GStreamer 未安装时忽略
            pass
        except Exception as pump_error:
            logger.debug("GLib 事件泵异常（忽略）：%s", pump_error)

    # ═══════════════════ 轮询生命周期 ═══════════════════

    def start_polling(self, interval_seconds: float = 0.5) -> None:
        """
        启动后台轮询线程和 GLib 事件泵。
        :param interval_seconds: 轮询间隔（秒）
        """
        if self._poll_running:
            return

        # 启动 GLib 事件泵（在 Qt 主线程，驱动 GStreamer 信号）
        self._start_glib_pump()

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
        """停止轮询、关闭适配器和 GLib 事件泵。"""
        self._poll_running = False
        if self._poll_thread is not None:
            self._poll_thread.join(timeout=3.0)
            self._poll_thread = None

        self._close_current_adapter()
        self._stop_glib_pump()
        logger.info("控制器轮询已停止")

    # ═══════════════════ 窗口定位 ═══════════════════

    def apply_display_positions(self) -> None:
        """根据当前会话的显示模式定位所有窗口。"""
        from scp_cv.services.playback import get_or_create_session
        from scp_cv.services.display import (
            list_display_targets,
            build_left_right_splice_target,
        )
        from scp_cv.apps.playback.models import PlaybackMode

        session = get_or_create_session()
        display_targets = list_display_targets()

        if session.display_mode == PlaybackMode.LEFT_RIGHT_SPLICE:
            splice_target = build_left_right_splice_target(display_targets)
            if splice_target is not None:
                left_rect = QRect(
                    splice_target.left.x, splice_target.left.y,
                    splice_target.left.width, splice_target.left.height,
                )
                right_rect = QRect(
                    splice_target.right.x, splice_target.right.y,
                    splice_target.right.width, splice_target.right.height,
                )
                if "left" in self._windows:
                    self._windows["left"].position_on_display(left_rect)
                if "right" in self._windows:
                    self._windows["right"].position_on_display(right_rect)
                return

        # 单屏模式
        target_label = session.target_display_label
        matched_display = next(
            (dt for dt in display_targets if dt.name == target_label),
            None,
        )
        if matched_display is None and display_targets:
            matched_display = display_targets[0]

        if matched_display is not None:
            rect = QRect(
                matched_display.x, matched_display.y,
                matched_display.width, matched_display.height,
            )
            primary_window = self.get_primary_window()
            if primary_window is not None:
                primary_window.position_on_display(rect)

    # ═══════════════════ 轮询逻辑 ═══════════════════

    def _poll_loop(self, interval_seconds: float) -> None:
        """
        DB 轮询主循环：读取 pending_command → 发射信号到主线程。
        此线程仅负责读取 DB 和上报状态，不直接操作适配器。
        :param interval_seconds: 轮询间隔
        """
        import django
        django.setup()

        while self._poll_running:
            try:
                self._check_and_dispatch_command()
                self._report_adapter_state()
            except Exception as poll_error:
                logger.error("轮询处理异常：%s", poll_error)
            time.sleep(interval_seconds)

    def _check_and_dispatch_command(self) -> None:
        """
        读取 DB 中的待执行指令，通过信号发射到 Qt 主线程。
        轮询线程仅读取 DB，不直接执行适配器操作。
        """
        from scp_cv.apps.playback.models import PlaybackCommand, PlaybackSession

        session = PlaybackSession.objects.first()
        if session is None:
            return

        pending = session.pending_command
        if not pending or pending == PlaybackCommand.NONE:
            return

        # 构建指令 hash 避免重复处理
        command_args = session.command_args or {}
        command_key = f"{pending}:{json.dumps(command_args, sort_keys=True)}"
        command_hash = hashlib.md5(command_key.encode()).hexdigest()
        if command_hash == self._last_command_hash:
            return
        self._last_command_hash = command_hash

        logger.info("轮询检测到指令：%s，参数=%s，发射到主线程", pending, command_args)

        # 通过 Qt 信号将指令调度到主线程执行
        # dict 需要序列化传递避免跨线程数据竞争
        self.sig_dispatch_command.emit(pending, dict(command_args))

        # 立即清除 DB 中的 pending_command，避免下次轮询重复检测
        from scp_cv.services.playback import clear_pending_command
        clear_pending_command()

    @Slot(str, dict)
    def _execute_command_on_main_thread(
        self,
        command: str,
        command_args: dict[str, object],
    ) -> None:
        """
        在 Qt 主线程上执行适配器指令。
        由 sig_dispatch_command 信号触发，保证所有 Qt 和 COM 操作
        在主线程执行，避免跨线程 GUI 操作错误。
        :param command: 指令名（PlaybackCommand 枚举值）
        :param command_args: 指令参数
        """
        from scp_cv.apps.playback.models import PlaybackCommand

        logger.info("主线程执行指令：%s", command)

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
        }

        handler = command_dispatch.get(command)
        if handler is not None:
            try:
                handler(command_args)
            except Exception as cmd_error:
                logger.error("执行指令 %s 失败：%s", command, cmd_error)
                self._update_session_error(str(cmd_error))

    def _report_adapter_state(self) -> None:
        """将当前适配器状态回写到 DB（轮询线程中调用）。"""
        if self._current_adapter is None or not self._current_adapter.is_open:
            return

        adapter_state = self._current_adapter.get_state()
        from scp_cv.services.playback import update_playback_progress
        update_playback_progress(
            playback_state=adapter_state.playback_state,
            current_slide=adapter_state.current_slide,
            total_slides=adapter_state.total_slides,
            position_ms=adapter_state.position_ms,
            duration_ms=adapter_state.duration_ms,
        )

    # ═══════════════════ 指令处理（主线程执行） ═══════════════════

    def _handle_open(self, command_args: dict[str, object]) -> None:
        """
        处理 OPEN 指令：关闭旧适配器，创建新适配器并打开源。
        在 Qt 主线程中执行，保证 Qt widget 和 COM 对象创建安全。
        :param command_args: 包含 source_type, uri, autoplay 的参数字典
        """
        source_type = str(command_args.get("source_type", ""))
        uri = str(command_args.get("uri", ""))
        autoplay = bool(command_args.get("autoplay", True))

        if not source_type or not uri:
            logger.warning("OPEN 指令缺少 source_type 或 uri")
            return

        # 关闭旧适配器
        self._close_current_adapter()

        # 创建新适配器（主线程，Qt widget 安全创建）
        adapter = create_adapter(source_type)
        window_handle = self.get_primary_window_handle()

        if window_handle == 0:
            logger.warning("没有可用窗口，跳过 OPEN")
            return

        adapter.open(uri=uri, window_handle=window_handle, autoplay=autoplay)
        self._current_adapter = adapter
        self._current_source_type = source_type

        # 切换窗口到视频模式
        primary_window = self.get_primary_window()
        if primary_window is not None:
            primary_window.show_video_container()

        self._update_session_state("playing" if autoplay else "loading")

    def _handle_play(self, command_args: dict[str, object]) -> None:
        """处理 PLAY 指令。"""
        if self._current_adapter is not None:
            self._current_adapter.play()
            self._update_session_state("playing")

    def _handle_pause(self, command_args: dict[str, object]) -> None:
        """处理 PAUSE 指令。"""
        if self._current_adapter is not None:
            self._current_adapter.pause()
            self._update_session_state("paused")

    def _handle_stop(self, command_args: dict[str, object]) -> None:
        """处理 STOP 指令。"""
        if self._current_adapter is not None:
            self._current_adapter.stop()
            self._update_session_state("stopped")

    def _handle_close(self, command_args: dict[str, object]) -> None:
        """处理 CLOSE 指令：关闭适配器并重置会话。"""
        self._close_current_adapter()
        self.sig_stop_all.emit()

        # 重置会话
        from scp_cv.apps.playback.models import PlaybackState, PlaybackSession
        session = PlaybackSession.objects.first()
        if session is not None:
            session.media_source = None
            session.playback_state = PlaybackState.IDLE
            session.current_slide = 0
            session.total_slides = 0
            session.position_ms = 0
            session.duration_ms = 0
            session.save()

    def _handle_next(self, command_args: dict[str, object]) -> None:
        """处理 NEXT 指令。"""
        if self._current_adapter is not None:
            self._current_adapter.next_item()

    def _handle_prev(self, command_args: dict[str, object]) -> None:
        """处理 PREV 指令。"""
        if self._current_adapter is not None:
            self._current_adapter.prev_item()

    def _handle_goto(self, command_args: dict[str, object]) -> None:
        """处理 GOTO 指令。"""
        if self._current_adapter is not None:
            target_index = int(command_args.get("target_index", 1))
            self._current_adapter.goto_item(target_index)

    def _handle_seek(self, command_args: dict[str, object]) -> None:
        """处理 SEEK 指令。"""
        if self._current_adapter is not None:
            position_ms = int(command_args.get("position_ms", 0))
            self._current_adapter.seek(position_ms)

    def _handle_set_loop(self, command_args: dict[str, object]) -> None:
        """
        处理 SET_LOOP 指令：切换当前适配器的循环播放状态。
        :param command_args: 包含 enabled 字段的参数字典
        """
        if self._current_adapter is not None:
            loop_enabled = bool(command_args.get("enabled", False))
            self._current_adapter.set_loop(loop_enabled)
            logger.info("循环播放已设置为 %s", loop_enabled)

    # ═══════════════════ 适配器管理 ═══════════════════

    def _close_current_adapter(self) -> None:
        """关闭并释放当前适配器。"""
        if self._current_adapter is not None:
            try:
                self._current_adapter.close()
            except Exception as close_error:
                logger.warning("关闭适配器异常：%s", close_error)
            self._current_adapter = None
            self._current_source_type = ""

    @staticmethod
    def _update_session_state(playback_state: str) -> None:
        """
        更新会话播放状态。
        :param playback_state: 新的播放状态值
        """
        from scp_cv.apps.playback.models import PlaybackSession
        session = PlaybackSession.objects.first()
        if session is not None:
            session.playback_state = playback_state
            session.save(update_fields=["playback_state", "last_updated_at"])

    @staticmethod
    def _update_session_error(error_message: str) -> None:
        """
        更新会话为错误状态。
        :param error_message: 错误描述（暂记录日志，不存 DB）
        """
        logger.error("播放会话错误：%s", error_message)
        from scp_cv.apps.playback.models import PlaybackSession
        session = PlaybackSession.objects.first()
        if session is not None:
            session.playback_state = "error"
            session.save(update_fields=["playback_state", "last_updated_at"])
