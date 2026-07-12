#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
播放器控制器：桥接 ControlCommand 持久化队列与适配器执行层。
轮询线程通过条件更新原子认领命令，再携带命令 ID 通过 Qt 信号分发；
适配器执行结果和运行状态分别回写命令队列与播放会话。

多窗口架构：每个输出窗口（window_id 1-4）独立管理一个适配器实例，
控制器同时轮询所有窗口的待执行指令并分发到 Qt 主线程。

线程模型：
- Qt 主线程：所有窗口操作、适配器创建和控制（通过信号分发）
- 轮询线程：定期认领 DB 中的 ControlCommand，发射信号到主线程

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
import time
from typing import Optional

from PySide6.QtCore import QObject, QRect, Signal, Slot

from scp_cv.player.background_audio_handlers import BackgroundAudioHandlersMixin
from scp_cv.player.controller_command_consumer import PlayerCommandConsumerMixin
from scp_cv.player.controller_handlers import PlayerCommandHandlersMixin
from scp_cv.player.controller_window_runtime import PlayerWindowRuntimeMixin

logger = logging.getLogger(__name__)


class PlayerController(
    PlayerCommandHandlersMixin,
    PlayerWindowRuntimeMixin,
    BackgroundAudioHandlersMixin,
    PlayerCommandConsumerMixin,
    QObject,
):
    """
    多窗口播放器控制器。

    职责：
    - 管理最多 4 个 PlayerWindow 实例（按 window_id 1-4 注册）
    - 每个窗口独立维护一个 SourceAdapter 实例
    - 原子认领所有窗口的 ControlCommand 并通过信号分发到 Qt 主线程
    - 将适配器状态回写 DB
    - 窗口定位与显示模式切换

    线程安全：
    - 适配器操作全部在 Qt 主线程执行（through sig_dispatch_command）
    - 轮询线程只访问命令/会话数据并发射信号，不直接操作适配器
    """

    # 信号：工作线程 → Qt 主线程
    sig_show_video = Signal(int)       # window_id → 切换到视频模式
    sig_show_black = Signal(int)       # window_id → 切换到黑屏
    sig_stop_all = Signal()            # 停止所有窗口
    sig_reposition = Signal(int, QRect)  # window_id + 目标矩形

    # 轮询线程 → Qt 主线程：分发指令执行（携带 window_id）
    sig_dispatch_command = Signal(int, str, dict)  # (window_id, command, command_args)
    sig_dispatch_queued_command = Signal(int, int, str, dict)  # (command_id, window_id, command, args)
    sig_dispatch_background_audio_command = Signal(str, dict)  # (command, command_args)
    sig_dispatch_queued_background_audio_command = Signal(int, str, dict)
    sig_report_states = Signal()                   # 轮询线程 → Qt 主线程：读取适配器状态
    # Broker 客户端线程 → Qt 主线程：PPT 后台打开完成（window_id, token, error）
    sig_ppt_open_finished = Signal(int, int, object)

    def __init__(
        self,
        parent: Optional[QObject] = None,
        enable_background_audio: bool = True,
        ppt_broker: object | None = None,
    ) -> None:
        super().__init__(parent)

        self._initialize_window_runtime()
        # 统一预热池：由 Qt 主线程创建和使用，避免切源时重复冷启动。
        self._preheat_pool: object | None = None
        # PowerPoint 生命周期只允许由独立 Broker 持有；播放器仅保留普通数据客户端。
        self._ppt_broker: object | None = ppt_broker
        # 在途 PPT 打开请求：window_id → _PendingPptOpen
        self._pending_ppt_opens: dict[int, object] = {}
        self._ppt_open_token_counter = itertools.count(1)
        # 背景音频单实例适配器，不占用任何 PlayerWindow。
        self._enable_background_audio = enable_background_audio
        self._background_audio_adapter: object | None = None
        self._background_audio_source_id = 0
        self._last_reported_background_audio_state: tuple[str, str, int, int] | None = None
        self._last_reset_all_token = ""
        self._last_reset_ppt_token = ""
        self._initialize_command_consumer_runtime()

        # 轮询线程
        self._poll_thread: Optional[threading.Thread] = None
        self._poll_running = False

        # 连接指令分发信号到主线程处理槽
        self.sig_dispatch_command.connect(self._execute_command_on_main_thread)
        self.sig_dispatch_queued_command.connect(
            self._execute_queued_command_on_main_thread
        )
        if self._enable_background_audio:
            self.sig_dispatch_background_audio_command.connect(self._execute_background_audio_command_on_main_thread)
            self.sig_dispatch_queued_background_audio_command.connect(
                self._execute_queued_background_audio_command_on_main_thread
            )
        self.sig_report_states.connect(self._report_all_adapter_states)
        self.sig_ppt_open_finished.connect(self._on_ppt_open_finished)

    # ═══════════════════ 轮询生命周期 ═══════════════════

    def start_polling(self, interval_seconds: float = 0.2) -> None:
        """
        启动后台轮询线程。
        :param interval_seconds: 轮询间隔（秒）
        """
        if self._poll_running:
            return

        self._recover_abandoned_commands()
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

        try:
            # 取消在途 PPT 打开，再关闭所有窗口的适配器
            try:
                self._abort_pending_ppt_opens()
            except Exception as abort_error:
                logger.warning("播放器退出时取消在途 PPT 打开失败：%s", abort_error)
            for wid in list(self._adapters.keys()):
                try:
                    self._close_adapter(wid, reheat=False)
                except Exception as close_error:
                    logger.warning(
                        "播放器退出时关闭窗口 %d 适配器失败：%s",
                        wid,
                        close_error,
                    )
            if self._preheat_pool is not None:
                try:
                    self._preheat_pool.close_all()
                except Exception as preheat_error:
                    logger.warning("播放器退出时关闭预热池失败：%s", preheat_error)
                finally:
                    self._preheat_pool = None
            try:
                self._close_background_audio_adapter()
            except Exception as audio_error:
                logger.warning("播放器退出时关闭背景音频失败：%s", audio_error)
        finally:
            if self._command_consumer_active:
                from scp_cv.services.command_queue import release_consumer

                release_consumer(self._command_consumer_identity)
                self._command_consumer_active = False
        logger.info("控制器轮询已停止")

    def _ensure_preheat_pool(self) -> object:
        """
        确保统一预热池已创建。
        :return: PlayerPreheatPool 实例
        """
        from scp_cv.player.preheat_pool import PlayerPreheatPool

        if self._preheat_pool is None:
            self._preheat_pool = PlayerPreheatPool(ppt_broker=self._ppt_broker)
        return self._preheat_pool

    def preheat_sources(self) -> None:
        """
        启动时预热所有启用预热的媒体源。
        :return: None
        """
        from scp_cv.apps.playback.models import MediaSource
        from scp_cv.apps.playback.models import SourceType
        from scp_cv.services.ppt_playback_cache import resolve_ppt_playback_uri

        preheat_pool = self._ensure_preheat_pool()
        for source in MediaSource.objects.filter(
            is_available=True,
            keep_alive=True,
            is_temporary=False,
        ).only("id", "source_type", "uri", "metadata"):
            if source.source_type == SourceType.AUDIO and not self._enable_background_audio:
                continue
            preheat_uri = resolve_ppt_playback_uri(source) if source.source_type == SourceType.PPT else source.uri
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

    # ═══════════════════ 轮询逻辑 ═══════════════════

    def _poll_loop(self, interval_seconds: float) -> None:
        """
        DB 轮询主循环：遍历所有已注册窗口，认领 ControlCommand → 发射信号。
        :param interval_seconds: 轮询间隔
        """
        import django
        django.setup()

        while self._poll_running:
            try:
                # 轮询所有已注册窗口的指令
                for window_id in self.registered_window_ids:
                    self._check_and_dispatch_command(window_id)
                if self._enable_background_audio:
                    self._check_and_dispatch_background_audio_command()
                self._maintain_command_consumer_if_due()
                self._prune_command_history_if_due()
                # Qt 适配器状态读取必须回到其创建时所在的主线程。
                self._request_adapter_state_report()
            except Exception as poll_error:
                logger.error("轮询处理异常：%s", poll_error)
            time.sleep(interval_seconds)

    @Slot(int, int, str, dict)
    def _execute_queued_command_on_main_thread(
        self,
        command_id: int,
        window_id: int,
        command: str,
        command_args: dict[str, object],
    ) -> None:
        """执行已领取的持久化指令，并在真实处理结束后确认结果。"""
        from scp_cv.apps.playback.models import ControlCommandStatus
        from scp_cv.services.command_queue import finish

        try:
            self._dispatching_command_id = command_id
            asynchronous = self._dispatch_command_on_main_thread(
                window_id,
                command,
                command_args,
            )
        except Exception as command_error:
            logger.error(
                "执行指令 id=%d %s（窗口 %d）失败：%s",
                command_id,
                command,
                window_id,
                command_error,
            )
            self._update_session_error(window_id, str(command_error))
            finish(
                command_id,
                self._command_consumer_id,
                status=ControlCommandStatus.FAILED,
                error_message=str(command_error),
            )
            return
        finally:
            self._dispatching_command_id = 0
        if asynchronous:
            return
        finish(
            command_id,
            self._command_consumer_id,
            status=ControlCommandStatus.SUCCEEDED,
        )

    @Slot(int, str, dict)
    def _execute_command_on_main_thread(
        self,
        window_id: int,
        command: str,
        command_args: dict[str, object],
    ) -> None:
        """
        在 Qt 主线程上执行适配器指令。
        由 sig_dispatch_command 信号触发，保证所有 Qt 操作在主线程执行，
        避免跨线程 GUI 操作错误；PPT 的 COM 操作只在 Broker STA 中发生。
        :param window_id: 目标窗口编号
        :param command: 指令名（PlaybackCommand 枚举值）
        :param command_args: 指令参数
        """
        try:
            self._dispatch_command_on_main_thread(window_id, command, command_args)
        except Exception as cmd_error:
            logger.error("执行指令 %s（窗口 %d）失败：%s", command, window_id, cmd_error)
            self._update_session_error(window_id, str(cmd_error))

    def _dispatch_command_on_main_thread(
        self,
        window_id: int,
        command: str,
        command_args: dict[str, object],
    ) -> bool:
        """分发一条指令；返回 True 表示异步 PPT 打开仍在执行。"""
        from scp_cv.apps.playback.models import PlaybackCommand

        logger.info("主线程执行指令：窗口 %d → %s", window_id, command)
        # 排队检查必须先于 reset 去重：排队时不记录 reset token，
        # 否则打开完成后重放同一条 reset 指令会被误判为重复广播而丢弃。
        if self._defer_command_during_ppt_open(window_id, command, command_args):
            return False
        if self._is_duplicate_reset_command(window_id, command, command_args):
            return False

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
            raise ValueError(f"未知的播放器指令：{command}")
        handler(window_id, command_args)
        return command == PlaybackCommand.OPEN and window_id in self._pending_ppt_opens

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
