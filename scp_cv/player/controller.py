#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
播放器控制器：桥接 Django 服务层与 PySide6 播放器窗口。
管理多窗口实例、GStreamer WebRTC 管线和帧同步。
@Project : SCP-cv
@File : controller.py
@Author : Qintsg
@Date : 2026-04-14
'''
from __future__ import annotations

import logging
import threading
from typing import Optional

from PySide6.QtCore import QObject, QRect, Signal, Slot

logger = logging.getLogger(__name__)

# MediaMTX WebRTC WHEP 端点模板
_WHEP_URL_TEMPLATE = "http://127.0.0.1:8889/{stream_id}/whep"


class PlayerController(QObject):
    """
    多窗口播放器控制器。

    职责：
    - 管理多个 PlayerWindow 实例（单屏模式 1 个，拼接模式 2 个）
    - 为每个窗口创建和管理 GStreamer WebRTC 管线
    - 协调帧同步（多管线共享时钟）
    - 轮询数据库状态并驱动窗口操作

    架构：
    - Qt 主线程：窗口操作、信号处理
    - 轮询线程：定期读取 DB 会话状态
    - WHEP 工作线程：执行 WebRTC 连接（阻塞操作）
    """

    # 信号：在工作线程触发，Qt 主线程 slot 接收
    sig_show_video = Signal(str)       # 窗口 ID → 切换到视频模式
    sig_show_black = Signal(str)       # 窗口 ID → 切换到黑屏
    sig_stop_all = Signal()            # 停止所有窗口
    sig_reposition = Signal(str, QRect)  # 窗口 ID + 目标矩形

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)

        # 窗口映射：window_id → PlayerWindow
        self._windows: dict[str, object] = {}

        # GStreamer 管线映射：window_id → GstWebRTCPipeline
        self._pipelines: dict[str, object] = {}

        # 帧同步协调器
        self._frame_sync: Optional[object] = None

        # 轮询线程
        self._poll_thread: Optional[threading.Thread] = None
        self._poll_running = False

        # WebRTC 连接工作线程
        self._connect_thread: Optional[threading.Thread] = None

        # 上一次应用的快照 hash
        self._last_applied_hash = ""

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

        # 连接信号到窗口
        self.sig_stop_all.connect(player_window.stop_all)

        logger.info("控制器已注册窗口：%s", window_id)

    def start_polling(self, interval_seconds: float = 0.5) -> None:
        """
        启动后台轮询线程，定期从数据库读取会话快照并驱动窗口。
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
        logger.info("播放器轮询线程已启动（间隔 %.1fs）", interval_seconds)

    def stop_polling(self) -> None:
        """停止后台轮询并清理所有管线。"""
        self._poll_running = False
        if self._poll_thread is not None:
            self._poll_thread.join(timeout=3.0)
            self._poll_thread = None

        self._stop_all_pipelines()
        logger.info("播放器轮询线程已停止")

    def apply_display_positions(self) -> None:
        """
        根据当前会话的显示模式，为所有注册窗口设置屏幕定位。
        从 DisplayTarget 数据读取坐标。
        """
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
                # 拼接模式：左右窗口各占一个物理显示器
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
            # 单屏模式只有一个窗口（"single" 或第一个注册的）
            target_window = self._windows.get("single")
            if target_window is None and self._windows:
                target_window = next(iter(self._windows.values()))
            if target_window is not None:
                target_window.position_on_display(rect)

    # ═══════════════════ 轮询逻辑 ═══════════════════

    def _poll_loop(self, interval_seconds: float) -> None:
        """
        轮询循环：从 Django ORM 读取当前播放会话，对比变更后驱动窗口操作。
        :param interval_seconds: 轮询间隔
        """
        import time

        import django
        django.setup()

        while self._poll_running:
            try:
                self._apply_current_state()
            except Exception as poll_error:
                logger.error("轮询处理异常：%s", poll_error)
            time.sleep(interval_seconds)

    def _apply_current_state(self) -> None:
        """读取当前播放会话快照并驱动窗口操作。"""
        import hashlib
        import json

        from scp_cv.services.playback import get_session_snapshot

        snapshot = get_session_snapshot()

        # 哈希变更检测
        snapshot_key = json.dumps(snapshot, sort_keys=True, default=str)
        snapshot_hash = hashlib.md5(snapshot_key.encode()).hexdigest()

        if snapshot_hash == self._last_applied_hash:
            return
        self._last_applied_hash = snapshot_hash
        logger.debug("检测到会话状态变更，驱动窗口")

        content_kind = snapshot.get("content_kind", "none")
        playback_state = snapshot.get("playback_state", "idle")

        # 停止/空闲 → 黑屏
        if content_kind == "none" or playback_state in ("idle", "stopped"):
            self._stop_all_pipelines()
            self.sig_stop_all.emit()
            return

        # WebRTC 流模式
        if content_kind == "stream":
            self._apply_stream_state(snapshot)
            return

    def _apply_stream_state(self, snapshot: dict[str, object]) -> None:
        """
        根据流快照驱动窗口播放 WebRTC 流。
        为每个活跃窗口创建 GStreamer WHEP 管线并启动播放。
        :param snapshot: 会话快照字典
        """
        from scp_cv.services.playback import get_or_create_session

        session = get_or_create_session()
        if session.stream_source is None:
            self._stop_all_pipelines()
            self.sig_stop_all.emit()
            return

        stream_identifier = session.stream_source.stream_identifier
        whep_url = _WHEP_URL_TEMPLATE.format(stream_id=stream_identifier)

        # 检查是否已在播放同一流
        if self._pipelines and all(
            pipeline.is_connected for pipeline in self._pipelines.values()
        ):
            return

        # 在工作线程中建立 WebRTC 连接（阻塞操作）
        if self._connect_thread is None or not self._connect_thread.is_alive():
            self._connect_thread = threading.Thread(
                target=self._connect_webrtc_streams,
                args=(whep_url,),
                daemon=True,
                name="webrtc-connect",
            )
            self._connect_thread.start()

    def _connect_webrtc_streams(self, whep_url: str) -> None:
        """
        WebRTC 连接工作线程：为每个窗口创建管线、执行 WHEP 协商、启动播放。
        此方法在工作线程中执行，通过信号通知 Qt 主线程。
        :param whep_url: WHEP 端点 URL
        """
        from scp_cv.player.gst_pipeline import GstWebRTCPipeline
        from scp_cv.player.frame_sync import FrameSyncCoordinator

        # 停止旧管线
        self._stop_all_pipelines()

        # 创建帧同步协调器
        frame_sync = FrameSyncCoordinator()
        self._frame_sync = frame_sync

        active_windows = list(self._windows.items())
        if not active_windows:
            logger.warning("没有注册的窗口，跳过 WebRTC 连接")
            return

        # 为每个窗口创建管线
        for window_id, window in active_windows:
            try:
                shared_clock = frame_sync.get_shared_clock()
                pipeline = GstWebRTCPipeline(
                    whep_url=whep_url,
                    window_handle=window.video_window_handle,
                    shared_clock=shared_clock,
                    on_error=lambda msg, wid=window_id: logger.error(
                        "窗口 [%s] 管线错误：%s", wid, msg,
                    ),
                )

                # 注册到帧同步
                frame_sync.register_pipeline(pipeline)

                # 执行 WHEP 连接（阻塞）
                pipeline.connect_and_play()

                # 连接成功后更新主时钟
                if frame_sync.master_clock is None:
                    frame_sync.update_master_clock(pipeline)

                self._pipelines[window_id] = pipeline

                # 通知 Qt 主线程显示视频容器
                window.show_video_container()

                logger.info(
                    "窗口 [%s] WebRTC 流已连接：%s", window_id, whep_url,
                )

            except (TimeoutError, ConnectionError, RuntimeError) as connect_error:
                logger.error(
                    "窗口 [%s] WebRTC 连接失败：%s", window_id, connect_error,
                )

        # 多窗口时启动帧同步漂移监控
        if len(self._pipelines) > 1:
            frame_sync.start_drift_monitoring(check_interval_seconds=1.0)
            logger.info("多窗口帧同步漂移监控已启动")

    def _stop_all_pipelines(self) -> None:
        """停止所有 GStreamer 管线并清理帧同步。"""
        if self._frame_sync is not None:
            self._frame_sync.clear()
            self._frame_sync = None

        for window_id, pipeline in self._pipelines.items():
            try:
                pipeline.stop()
            except Exception as stop_error:
                logger.warning(
                    "停止窗口 [%s] 管线异常：%s", window_id, stop_error,
                )
        self._pipelines.clear()
