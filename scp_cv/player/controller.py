#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
播放器控制器：桥接 Django 数据库指令与适配器执行层。
通过轮询 PlaybackSession.pending_command 驱动适配器行为，
并将适配器状态回写到数据库供 Django 前端展示。
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

from PySide6.QtCore import QObject, QRect, Signal, Slot

from scp_cv.player.adapters import AdapterState, SourceAdapter, create_adapter

logger = logging.getLogger(__name__)


class PlayerController(QObject):
    """
    统一播放器控制器。

    职责：
    - 管理 PlayerWindow 实例（单屏 1 个，拼接 2 个）
    - 轮询 DB 中的 pending_command 并分发到当前适配器
    - 将适配器状态回写 DB
    - 窗口定位与显示模式切换

    架构：
    - Qt 主线程：窗口操作、信号处理
    - 轮询线程：定期读取 DB → 分发指令 → 回写状态
    - 适配器执行线程：部分适配器的阻塞操作（如 WHEP 连接）
    """

    # 信号：工作线程 → Qt 主线程
    sig_show_video = Signal(str)       # 窗口 ID → 切换到视频模式
    sig_show_black = Signal(str)       # 窗口 ID → 切换到黑屏
    sig_stop_all = Signal()            # 停止所有窗口
    sig_reposition = Signal(str, QRect)  # 窗口 ID + 目标矩形

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

    # ═══════════════════ 轮询生命周期 ═══════════════════

    def start_polling(self, interval_seconds: float = 0.5) -> None:
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
        """停止轮询并关闭当前适配器。"""
        self._poll_running = False
        if self._poll_thread is not None:
            self._poll_thread.join(timeout=3.0)
            self._poll_thread = None

        self._close_current_adapter()
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
        DB 轮询主循环：读取 pending_command → 分发 → 回写状态。
        :param interval_seconds: 轮询间隔
        """
        import django
        django.setup()

        while self._poll_running:
            try:
                self._process_pending_command()
                self._report_adapter_state()
            except Exception as poll_error:
                logger.error("轮询处理异常：%s", poll_error)
            time.sleep(interval_seconds)

    def _process_pending_command(self) -> None:
        """读取 DB 中的待执行指令，分发到适配器。"""
        from scp_cv.apps.playback.models import PlaybackCommand, PlaybackSession

        session = PlaybackSession.objects.first()
        if session is None:
            return

        pending = session.pending_command
        if not pending or pending == PlaybackCommand.NONE:
            return

        # 构建指令 hash 避免重复处理
        command_key = f"{pending}:{json.dumps(session.command_args, sort_keys=True)}"
        command_hash = hashlib.md5(command_key.encode()).hexdigest()
        if command_hash == self._last_command_hash:
            return
        self._last_command_hash = command_hash

        logger.info("收到指令：%s，参数=%s", pending, session.command_args)

        # 分发到对应处理方法
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
        }

        handler = command_dispatch.get(pending)
        if handler is not None:
            try:
                handler(session)
            except Exception as cmd_error:
                logger.error("执行指令 %s 失败：%s", pending, cmd_error)
                self._update_session_state(session, "error")

        # 清除已执行的指令
        from scp_cv.services.playback import clear_pending_command
        clear_pending_command()

    def _report_adapter_state(self) -> None:
        """将当前适配器状态回写到 DB。"""
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

    # ═══════════════════ 指令处理 ═══════════════════

    def _handle_open(self, session: object) -> None:
        """
        处理 OPEN 指令：关闭旧适配器，创建新适配器并打开源。
        :param session: PlaybackSession 实例
        """
        args = session.command_args or {}
        source_type = args.get("source_type", "")
        uri = args.get("uri", "")
        autoplay = args.get("autoplay", True)

        if not source_type or not uri:
            logger.warning("OPEN 指令缺少 source_type 或 uri")
            return

        # 关闭旧适配器
        self._close_current_adapter()

        # 创建新适配器
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

        self._update_session_state(session, "playing" if autoplay else "loading")

    def _handle_play(self, session: object) -> None:
        """处理 PLAY 指令。"""
        if self._current_adapter is not None:
            self._current_adapter.play()
            self._update_session_state(session, "playing")

    def _handle_pause(self, session: object) -> None:
        """处理 PAUSE 指令。"""
        if self._current_adapter is not None:
            self._current_adapter.pause()
            self._update_session_state(session, "paused")

    def _handle_stop(self, session: object) -> None:
        """处理 STOP 指令。"""
        if self._current_adapter is not None:
            self._current_adapter.stop()
            self._update_session_state(session, "stopped")

    def _handle_close(self, session: object) -> None:
        """处理 CLOSE 指令：关闭适配器并重置会话。"""
        self._close_current_adapter()
        self.sig_stop_all.emit()

        # 重置会话
        from scp_cv.apps.playback.models import PlaybackState
        session.media_source = None
        session.playback_state = PlaybackState.IDLE
        session.current_slide = 0
        session.total_slides = 0
        session.position_ms = 0
        session.duration_ms = 0
        session.save()

    def _handle_next(self, session: object) -> None:
        """处理 NEXT 指令。"""
        if self._current_adapter is not None:
            self._current_adapter.next_item()

    def _handle_prev(self, session: object) -> None:
        """处理 PREV 指令。"""
        if self._current_adapter is not None:
            self._current_adapter.prev_item()

    def _handle_goto(self, session: object) -> None:
        """处理 GOTO 指令。"""
        if self._current_adapter is not None:
            target_index = (session.command_args or {}).get("target_index", 1)
            self._current_adapter.goto_item(target_index)

    def _handle_seek(self, session: object) -> None:
        """处理 SEEK 指令。"""
        if self._current_adapter is not None:
            position_ms = (session.command_args or {}).get("position_ms", 0)
            self._current_adapter.seek(position_ms)

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
    def _update_session_state(session: object, playback_state: str) -> None:
        """
        更新会话播放状态。
        :param session: PlaybackSession 实例
        :param playback_state: 新的播放状态值
        """
        session.playback_state = playback_state
        session.save(update_fields=["playback_state", "last_updated_at"])
