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
from typing import Optional

from PySide6.QtCore import QObject, QRect, Signal, Slot

from scp_cv.player.adapters import SourceAdapter, create_adapter

logger = logging.getLogger(__name__)


class PlayerController(QObject):
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

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)

        # 窗口映射：window_id(int) → PlayerWindow
        self._windows: dict[int, object] = {}

        # 适配器映射：window_id(int) → SourceAdapter（每窗口独立）
        self._adapters: dict[int, SourceAdapter] = {}
        # 适配器源类型记录：window_id → source_type
        self._adapter_source_types: dict[int, str] = {}

        # 轮询线程
        self._poll_thread: Optional[threading.Thread] = None
        self._poll_running = False

        # 每个窗口上一次已上报状态，避免轮询线程无变化时频繁写库。
        self._last_reported_states: dict[int, tuple[str, int, int, int, int]] = {}

        # 连接指令分发信号到主线程处理槽
        self.sig_dispatch_command.connect(self._execute_command_on_main_thread)

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
        """停止轮询并关闭所有适配器。"""
        self._poll_running = False
        if self._poll_thread is not None:
            self._poll_thread.join(timeout=3.0)
            self._poll_thread = None

        # 关闭所有窗口的适配器
        for wid in list(self._adapters.keys()):
            self._close_adapter(wid)
        logger.info("控制器轮询已停止")

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
                # 上报所有活跃适配器的状态
                self._report_all_adapter_states()
            except Exception as poll_error:
                logger.error("轮询处理异常：%s", poll_error)
            time.sleep(interval_seconds)

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
            PlaybackCommand.SHOW_ID: self._handle_show_id,
        }

        handler = command_dispatch.get(command)
        if handler is not None:
            try:
                handler(window_id, command_args)
            except Exception as cmd_error:
                logger.error("执行指令 %s（窗口 %d）失败：%s", command, window_id, cmd_error)
                self._update_session_error(window_id, str(cmd_error))

    def _report_all_adapter_states(self) -> None:
        """将所有活跃适配器的状态回写到 DB（轮询线程中调用）。"""
        from scp_cv.services.playback import update_playback_progress

        for window_id, adapter in self._adapters.items():
            if adapter is None or not adapter.is_open:
                continue
            adapter_state = adapter.get_state()
            state_signature = (
                adapter_state.playback_state,
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
                current_slide=adapter_state.current_slide,
                total_slides=adapter_state.total_slides,
                position_ms=adapter_state.position_ms,
                duration_ms=adapter_state.duration_ms,
            )
            self._last_reported_states[window_id] = state_signature

    # ═══════════════════ 指令处理（主线程执行） ═══════════════════

    def _handle_open(self, window_id: int, command_args: dict[str, object]) -> None:
        """
        处理 OPEN 指令：关闭旧适配器，创建新适配器并打开源。
        在 Qt 主线程中执行，保证 Qt widget 和 COM 对象创建安全。
        :param window_id: 目标窗口编号
        :param command_args: 包含 source_type, uri, autoplay 的参数字典
        """
        source_type = str(command_args.get("source_type", ""))
        uri = str(command_args.get("uri", ""))
        autoplay = bool(command_args.get("autoplay", True))

        if not source_type or not uri:
            logger.warning("窗口 %d：OPEN 指令缺少 source_type 或 uri", window_id)
            return

        # 关闭该窗口旧适配器
        self._close_adapter(window_id)

        # 创建新适配器（主线程，Qt widget 安全创建）
        adapter = create_adapter(source_type)
        window_handle = self.get_window_handle(window_id)

        if window_handle == 0:
            logger.warning("窗口 %d 没有可用句柄，跳过 OPEN", window_id)
            return

        # 网页源使用专用的网页容器（支持鼠标交互）
        is_web_source = source_type == "web"
        if is_web_source:
            window = self.get_window(window_id)
            if window is not None:
                # 注入网页容器给适配器，避免使用原生窗口句柄查找
                from scp_cv.player.adapters.web import WebSourceAdapter
                if isinstance(adapter, WebSourceAdapter):
                    adapter.set_parent_container(window.web_container)

        adapter.open(uri=uri, window_handle=window_handle, autoplay=autoplay)
        self._adapters[window_id] = adapter
        self._adapter_source_types[window_id] = source_type

        # 网页源切换到网页容器，其他源切换到视频容器
        window = self.get_window(window_id)
        if window is not None:
            if is_web_source:
                window.show_web_container()
            else:
                window.show_video_container()

        self._update_session_state(window_id, "playing" if autoplay else "loading")

    def _handle_play(self, window_id: int, command_args: dict[str, object]) -> None:
        """处理 PLAY 指令。"""
        adapter = self._adapters.get(window_id)
        if adapter is not None:
            adapter.play()
            self._update_session_state(window_id, "playing")

    def _handle_pause(self, window_id: int, command_args: dict[str, object]) -> None:
        """处理 PAUSE 指令。"""
        adapter = self._adapters.get(window_id)
        if adapter is not None:
            adapter.pause()
            self._update_session_state(window_id, "paused")

    def _handle_stop(self, window_id: int, command_args: dict[str, object]) -> None:
        """处理 STOP 指令。"""
        adapter = self._adapters.get(window_id)
        if adapter is not None:
            adapter.stop()
            self._update_session_state(window_id, "stopped")

    def _handle_close(self, window_id: int, command_args: dict[str, object]) -> None:
        """处理 CLOSE 指令：关闭适配器并重置会话。"""
        self._close_adapter(window_id)

        # 切换窗口到黑屏
        window = self.get_window(window_id)
        if window is not None:
            window.show_black_screen()

        # 重置会话
        from scp_cv.apps.playback.models import PlaybackState, PlaybackSession
        session = PlaybackSession.objects.filter(window_id=window_id).first()
        if session is not None:
            session.media_source = None
            session.playback_state = PlaybackState.IDLE
            session.current_slide = 0
            session.total_slides = 0
            session.position_ms = 0
            session.duration_ms = 0
            session.save()

    def _handle_next(self, window_id: int, command_args: dict[str, object]) -> None:
        """处理 NEXT 指令。"""
        adapter = self._adapters.get(window_id)
        if adapter is not None:
            adapter.next_item()

    def _handle_prev(self, window_id: int, command_args: dict[str, object]) -> None:
        """处理 PREV 指令。"""
        adapter = self._adapters.get(window_id)
        if adapter is not None:
            adapter.prev_item()

    def _handle_goto(self, window_id: int, command_args: dict[str, object]) -> None:
        """处理 GOTO 指令。"""
        adapter = self._adapters.get(window_id)
        if adapter is not None:
            target_index = int(command_args.get("target_index", 1))
            adapter.goto_item(target_index)

    def _handle_seek(self, window_id: int, command_args: dict[str, object]) -> None:
        """处理 SEEK 指令。"""
        adapter = self._adapters.get(window_id)
        if adapter is not None:
            position_ms = int(command_args.get("position_ms", 0))
            adapter.seek(position_ms)

    def _handle_set_loop(self, window_id: int, command_args: dict[str, object]) -> None:
        """
        处理 SET_LOOP 指令：切换指定窗口适配器的循环播放状态。
        :param window_id: 窗口编号
        :param command_args: 包含 enabled 字段的参数字典
        """
        adapter = self._adapters.get(window_id)
        if adapter is not None:
            loop_enabled = bool(command_args.get("enabled", False))
            adapter.set_loop(loop_enabled)
            logger.info("窗口 %d 循环播放已设置为 %s", window_id, loop_enabled)

    def _handle_show_id(self, window_id: int, command_args: dict[str, object]) -> None:
        """
        处理 SHOW_ID 指令：在指定窗口显示半透明 ID 覆盖层 5 秒。
        :param window_id: 窗口编号
        :param command_args: 未使用
        """
        window = self.get_window(window_id)
        if window is not None:
            window.show_id_overlay()
            logger.info("窗口 %d 触发 ID 覆盖层显示", window_id)

    # ═══════════════════ 适配器管理 ═══════════════════

    def _close_adapter(self, window_id: int) -> None:
        """
        关闭并释放指定窗口的适配器。
        :param window_id: 窗口编号
        """
        adapter = self._adapters.pop(window_id, None)
        if adapter is not None:
            try:
                adapter.close()
            except Exception as close_error:
                logger.warning("关闭窗口 %d 适配器异常：%s", window_id, close_error)
        self._adapter_source_types.pop(window_id, None)
        self._last_reported_states.pop(window_id, None)

    def _update_session_state(self, window_id: int, playback_state: str) -> None:
        """
        更新指定窗口会话播放状态。
        :param window_id: 窗口编号
        :param playback_state: 新的播放状态值
        """
        from scp_cv.apps.playback.models import PlaybackSession
        session = PlaybackSession.objects.filter(window_id=window_id).first()
        if session is not None:
            session.playback_state = playback_state
            session.save(update_fields=["playback_state", "last_updated_at"])

    def _update_session_error(self, window_id: int, error_message: str) -> None:
        """
        更新指定窗口会话为错误状态。
        :param window_id: 窗口编号
        :param error_message: 错误描述
        """
        logger.error("窗口 %d 播放会话错误：%s", window_id, error_message)
        from scp_cv.apps.playback.models import PlaybackSession
        session = PlaybackSession.objects.filter(window_id=window_id).first()
        if session is not None:
            session.playback_state = "error"
            session.save(update_fields=["playback_state", "last_updated_at"])
