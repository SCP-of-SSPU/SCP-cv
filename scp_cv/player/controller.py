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

import itertools
import logging
import threading
import uuid
from typing import Callable, Optional

from PySide6.QtCore import QObject, QRect, QTimer, Signal, Slot

from scp_cv.player.adapters import SourceAdapter
from scp_cv.player.background_audio_handlers import BackgroundAudioHandlersMixin
from scp_cv.player.controller_handlers import PlayerCommandHandlersMixin
from scp_cv.player.controller_polling import PlayerPollingMixin
from scp_cv.player.controller_display import PlayerDisplayLayoutMixin

logger = logging.getLogger(__name__)


class PlayerController(PlayerDisplayLayoutMixin, PlayerPollingMixin, PlayerCommandHandlersMixin, BackgroundAudioHandlersMixin, QObject):
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
    sig_dispatch_command = Signal(int, str, dict, int, str)  # window, command, args, queue id, consumer
    sig_dispatch_background_audio_command = Signal(int, str, dict, str)  # id, command, args, consumer
    sig_report_states = Signal()                   # 轮询线程 → Qt 主线程：读取适配器状态
    # COM 工作线程 → Qt 主线程：PPT 后台打开完成（window_id, token, error）
    sig_ppt_open_finished = Signal(int, int, object)

    def __init__(
        self,
        parent: Optional[QObject] = None,
        enable_background_audio: bool = True,
        ppt_com_worker: object | None = None,
    ) -> None:
        super().__init__(parent)

        # 窗口映射：window_id(int) → PlayerWindow
        self._windows: dict[int, object] = {}

        # 适配器映射：window_id(int) → SourceAdapter（每窗口独立）
        self._adapters: dict[int, SourceAdapter] = {}
        # 适配器源类型记录：window_id → source_type
        self._adapter_source_types: dict[int, str] = {}
        # 适配器放映模式记录：window_id → pdf / powerpoint / ""
        self._adapter_kinds: dict[int, str] = {}
        # 适配器源 ID 记录：切源竞态中用于阻断旧 adapter 状态写回新会话。
        self._adapter_source_ids: dict[int, int] = {}
        # 统一预热池：由 Qt 主线程创建和使用，避免切源时重复冷启动。
        self._preheat_pool: object | None = None
        # 共享 PPT COM 工作线程：None 时所有 PPT COM 操作内联执行（测试场景）。
        self._ppt_com_worker: object | None = ppt_com_worker
        # 在途 PPT 打开请求：window_id → _PendingPptOpen
        self._pending_ppt_opens: dict[int, object] = {}
        self._ppt_open_token_counter = itertools.count(1)
        # 非 dev 模式下由 run_player 注入关闭回调，窗口重建后仍需保持相同行为。
        self._window_closed_callback: Callable[[], None] | None = None
        # 背景音频单实例适配器，不占用任何 PlayerWindow。
        self._enable_background_audio = enable_background_audio
        self._background_audio_adapter: object | None = None
        self._background_audio_source_id = 0
        self._last_reported_background_audio_state: tuple[str, str, int, int] | None = None
        self._last_reset_all_token = ""
        self._last_reset_ppt_token = ""
        self._last_display_labels: dict[int, str] = {}

        # 轮询线程
        self._poll_thread: Optional[threading.Thread] = None
        self._poll_running = False
        self._poll_stop_event = threading.Event()
        self._consumer_id = uuid.uuid4().hex
        self._preheat_maintenance_timer: QTimer | None = None
        self._last_player_heartbeat_monotonic = 0.0

        # 每个窗口上一次已上报状态，避免轮询线程无变化时频繁写库。
        self._last_reported_states: dict[int, tuple[str, int, int, int, int]] = {}
        self._state_report_pending = False
        self._state_report_lock = threading.Lock()

        # 连接指令分发信号到主线程处理槽
        self.sig_dispatch_command.connect(self._execute_command_on_main_thread)
        self.sig_reposition.connect(self._reposition_window)
        if self._enable_background_audio:
            self.sig_dispatch_background_audio_command.connect(self._execute_background_audio_command_on_main_thread)
        self.sig_report_states.connect(self._report_all_adapter_states)
        self.sig_ppt_open_finished.connect(self._on_ppt_open_finished)

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
        self._poll_stop_event.clear()
        self._poll_thread = threading.Thread(
            target=self._poll_loop,
            args=(interval_seconds,),
            daemon=True,
            name="player-poll",
        )
        self._poll_thread.start()
        if self._preheat_pool is not None and self._preheat_maintenance_timer is None:
            self._preheat_maintenance_timer = QTimer(self)
            self._preheat_maintenance_timer.setInterval(1000)
            self._preheat_maintenance_timer.timeout.connect(self._maintain_preheat_resources)
            self._preheat_maintenance_timer.start()
        logger.info("控制器轮询已启动（间隔 %.1fs）", interval_seconds)

    def stop_polling(self) -> None:
        """停止轮询并关闭所有适配器。"""
        self._poll_running = False
        self._poll_stop_event.set()
        if self._preheat_maintenance_timer is not None:
            self._preheat_maintenance_timer.stop()
            self._preheat_maintenance_timer.deleteLater()
            self._preheat_maintenance_timer = None
        if self._poll_thread is not None:
            self._poll_thread.join(timeout=3.0)
            if self._poll_thread.is_alive():
                logger.error("播放器轮询线程在超时后仍未退出，延迟释放其可能使用的资源")
                return
            self._poll_thread = None
        from scp_cv.services.playback_commands import release_playback_command_lease

        try:
            released = release_playback_command_lease(self._consumer_id, tuple(self.registered_window_ids))
        except Exception as lease_error:
            logger.warning("退出时释放播放指令租约失败：%s", lease_error)
            released = 0
        if released:
            logger.info("退出时释放播放指令租约：%d 条", released)
        if self._enable_background_audio:
            from scp_cv.services.background_audio_commands import release_background_audio_command_lease

            try:
                released_audio = release_background_audio_command_lease(self._consumer_id)
            except Exception as lease_error:
                logger.warning("退出时释放背景音频租约失败：%s", lease_error)
                released_audio = 0
            if released_audio:
                logger.info("退出时释放背景音频指令租约：%d 条", released_audio)

        # 取消在途 PPT 打开，再关闭所有窗口的适配器
        self._abort_pending_ppt_opens()
        for wid in list(self._adapters.keys()):
            self._close_adapter(wid, reheat=False)
        if self._preheat_pool is not None:
            self._preheat_pool.close_all()
            self._preheat_pool = None
        self._close_background_audio_adapter()
        self._shutdown_ppt_com_worker()
        logger.info("控制器轮询已停止")

    def _shutdown_ppt_com_worker(self) -> None:
        """
        关闭 PPT COM 工作线程，并兜底清理本系统拉起的残留 PowerPoint 进程。
        :return: None
        """
        if self._ppt_com_worker is None:
            return
        shutdown_ok = False
        try:
            shutdown_ok = bool(self._ppt_com_worker.shutdown(timeout_seconds=10.0))
            if not shutdown_ok:
                logger.error("PPT COM 工作线程未确认退出，保留资源以避免并发访问已终止 COM server")
        except Exception as shutdown_error:
            logger.warning("PPT COM 工作线程关闭异常：%s", shutdown_error)
        if not shutdown_ok:
            return
        from scp_cv.player.adapters.ppt_process import terminate_spawned_ppt_processes

        terminated = terminate_spawned_ppt_processes()
        if terminated:
            logger.info("退出时清理残留 PowerPoint 进程：%s", terminated)

    def _ensure_preheat_pool(self) -> object:
        """
        确保统一预热池已创建。
        :return: PlayerPreheatPool 实例
        """
        from scp_cv.player.preheat_pool import PlayerPreheatPool

        if self._preheat_pool is None:
            self._preheat_pool = PlayerPreheatPool()
            self._preheat_pool.attach_ppt_com_worker(self._ppt_com_worker)
        return self._preheat_pool

    def preheat_sources(self) -> None:
        """
        启动时预热所有启用预热的媒体源。
        :return: None
        """
        from scp_cv.apps.playback.models import MediaSource
        from scp_cv.apps.playback.models import SourceType
        from scp_cv.services.slides_pdf import resolve_slide_playback_uri

        preheat_pool = self._ensure_preheat_pool()
        for source in MediaSource.objects.filter(
            is_available=True,
            keep_alive=True,
            is_temporary=False,
        ).only("id", "source_type", "uri", "metadata"):
            if source.source_type == SourceType.AUDIO and not self._enable_background_audio:
                continue
            preheat_uri = resolve_slide_playback_uri(source) if source.source_type == SourceType.PPT else source.uri
            preheat_pool.preheat_source(
                source.pk,
                source.source_type,
                preheat_uri,
            )

    def preheat_web_sources(self) -> None:
        """
        兼容旧调用：预热所有已启用预热的媒体源。
        :return: None
        """
        self.preheat_sources()

    @Slot()
    def _maintain_preheat_resources(self) -> None:
        """在 Qt 主线程周期维护直播等长期预热资源。"""
        if self._preheat_pool is None:
            return
        maintain = getattr(self._preheat_pool, "maintain", None)
        if callable(maintain):
            maintain()

    @Slot(int, str, dict, int, str)
    def _execute_command_on_main_thread(
        self,
        window_id: int,
        command: str,
        command_args: dict[str, object],
        command_id: int = 0,
        consumer_id: str = "",
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
        # 排队检查必须先于 reset 去重：排队时不记录 reset token，
        # 否则打开完成后重放同一条 reset 指令会被误判为重复广播而丢弃。
        if self._defer_command_during_ppt_open(window_id, command, command_args, command_id, consumer_id):
            return
        if self._is_duplicate_reset_command(window_id, command, command_args):
            self._ack_command_record(command_id, consumer_id)
            return

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
            PlaybackCommand.RESET_PPT: self._handle_reset_ppt,
            PlaybackCommand.SHOW_ID: self._handle_show_id,
        }

        handler = command_dispatch.get(command)
        if handler is None:
            logger.error("窗口 %d 收到未知播放指令：%s", window_id, command)
            self._ack_command_record(command_id, consumer_id)
            return
        try:
            handler_args = dict(command_args)
            if command_id:
                handler_args["_command_record_id"] = command_id
                handler_args["_command_consumer_id"] = consumer_id
            handler(window_id, handler_args)
        except Exception as cmd_error:
            logger.error("执行指令 %s（窗口 %d）失败：%s", command, window_id, cmd_error)
            self._update_session_error(window_id, str(cmd_error))
        finally:
            # 异步 PPT 在完成回调中确认；其它命令在主线程 handler 返回后确认。
            if command_id and not (
                command == PlaybackCommand.OPEN and window_id in self._pending_ppt_opens
            ):
                self._ack_command_record(command_id, consumer_id)

    @staticmethod
    def _ack_command_record(command_id: int, consumer_id: str = "") -> None:
        """确认已处理的播放队列记录。"""
        if not command_id:
            return
        from scp_cv.services.playback_commands import acknowledge_playback_command

        acknowledge_playback_command(command_id, consumer_id or None)

    def _is_duplicate_reset_command(
        self,
        window_id: int,
        command: str,
        command_args: dict[str, object],
    ) -> bool:
        """
        判断全局重置广播是否已被当前单进程播放器消费。
        :param window_id: 触发窗口编号
        :param command: 播放器指令
        :param command_args: 指令参数
        :return: True 表示重复广播，应忽略
        """
        from scp_cv.apps.playback.models import PlaybackCommand
        from scp_cv.services.playback import RESET_ALL_WINDOWS_ARG, RESET_TOKEN_ARG

        reset_token = str(command_args.get(RESET_TOKEN_ARG, ""))
        if not reset_token:
            return False
        if command == PlaybackCommand.RESET_PPT:
            if self._last_reset_ppt_token == reset_token:
                logger.debug("窗口 %d 忽略重复 PPT reset token=%s", window_id, reset_token)
                return True
            self._last_reset_ppt_token = reset_token
            return False
        if command == PlaybackCommand.CLOSE and bool(command_args.get(RESET_ALL_WINDOWS_ARG)):
            if self._last_reset_all_token == reset_token:
                logger.debug("窗口 %d 忽略重复 reset-all token=%s", window_id, reset_token)
                return True
            self._last_reset_all_token = reset_token
        return False
