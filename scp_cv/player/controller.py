#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
播放器控制器：桥接 Django 服务层与 PySide6 播放器窗口。
监听 SSE 事件总线，将播放状态变更转换为窗口操作指令。
@Project : SCP-cv
@File : controller.py
@Author : Qintsg
@Date : 2026-04-10
'''
from __future__ import annotations

import logging
import threading
from typing import Optional

from PySide6.QtCore import QObject, QRect, Signal, Slot

logger = logging.getLogger(__name__)


class PlayerController(QObject):
    """
    在 Qt 主线程中运行的播放器控制器。
    从服务层获取状态快照，驱动 PlayerWindow 执行内容切换、翻页、显示器定位等。
    使用 Qt 信号在线程间安全通信。
    """

    # 信号定义：在非 Qt 线程触发，Qt 主线程的 slot 接收
    sig_show_page = Signal(str)          # 页面图片路径
    sig_play_media = Signal(str)         # 媒体文件路径
    sig_pause_media = Signal()
    sig_play_stream = Signal(str)        # SRT 流 URL
    sig_stop_all = Signal()
    sig_reposition = Signal(QRect)       # 窗口定位矩形

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._player_window: Optional[object] = None
        self._poll_thread: Optional[threading.Thread] = None
        self._poll_running = False

        # 上一次应用的快照 hash，避免重复操作
        self._last_applied_hash = ""

    def bind_window(self, player_window: object) -> None:
        """
        绑定播放器窗口并连接信号。
        :param player_window: PlayerWindow 实例
        """
        from scp_cv.player.window import PlayerWindow
        if not isinstance(player_window, PlayerWindow):
            raise TypeError("需要 PlayerWindow 实例")

        self._player_window = player_window

        # 连接信号到窗口 slot
        self.sig_show_page.connect(player_window.show_page_image)
        self.sig_play_media.connect(player_window.play_media)
        self.sig_pause_media.connect(player_window.pause_media)
        self.sig_play_stream.connect(player_window.play_srt_stream)
        self.sig_stop_all.connect(player_window.stop_all)
        self.sig_reposition.connect(player_window.position_on_display)

        logger.info("控制器已绑定到播放器窗口")

    def start_polling(self, interval_seconds: float = 1.0) -> None:
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
        """停止后台轮询。"""
        self._poll_running = False
        if self._poll_thread is not None:
            self._poll_thread.join(timeout=3.0)
            self._poll_thread = None
        logger.info("播放器轮询线程已停止")

    def _poll_loop(self, interval_seconds: float) -> None:
        """
        轮询循环：从 Django ORM 读取当前播放会话，对比变更后发射信号。
        :param interval_seconds: 轮询间隔
        """
        import time
        import hashlib
        import json

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

        # 简单哈希检测变更
        snapshot_key = json.dumps(snapshot, sort_keys=True, default=str)
        snapshot_hash = hashlib.md5(snapshot_key.encode()).hexdigest()

        if snapshot_hash == self._last_applied_hash:
            return  # 无变更，跳过

        self._last_applied_hash = snapshot_hash
        logger.debug("检测到会话状态变更，开始驱动窗口")

        content_kind = snapshot.get("content_kind", "none")
        playback_state = snapshot.get("playback_state", "idle")

        # 停止/空闲状态 → 黑屏
        if content_kind == "none" or playback_state in ("idle", "stopped"):
            self.sig_stop_all.emit()
            return

        # PPT 模式 → 显示页面图片
        if content_kind == "ppt":
            self._apply_ppt_state(snapshot)
            return

        # SRT 流模式 → 流播放
        if content_kind == "stream":
            self._apply_stream_state(snapshot)
            return

    def _apply_ppt_state(self, snapshot: dict[str, object]) -> None:
        """
        根据 PPT 快照驱动窗口显示页面图片。
        :param snapshot: 会话快照字典
        """
        from scp_cv.services.ppt_processor import get_page_image_path
        from scp_cv.services.playback import get_or_create_session

        session = get_or_create_session()
        if session.content_resource is None:
            self.sig_stop_all.emit()
            return

        resource_id = session.content_resource.pk
        page_number = session.current_page_number
        image_path = get_page_image_path(resource_id, page_number)

        if image_path is not None:
            self.sig_show_page.emit(str(image_path))
        else:
            logger.warning(
                "PPT 页面图片缺失：resource_id=%d, page=%d",
                resource_id, page_number,
            )

    def _apply_stream_state(self, snapshot: dict[str, object]) -> None:
        """
        根据 SRT 流快照驱动窗口播放流。
        使用 SRT 直连 URL 跳过 RTSP 中转环节，降低延迟。
        :param snapshot: 会话快照字典
        """
        from scp_cv.services.playback import get_or_create_session

        session = get_or_create_session()
        if session.stream_source is None:
            self.sig_stop_all.emit()
            return

        stream = session.stream_source
        # SRT 直连读取：跳过 RTSP 中转，mpv 通过 FFmpeg 直读 MediaMTX SRT
        # latency=100000 → 100ms SRT 级最小延迟
        stream_identifier = stream.stream_identifier
        srt_read_url = (
            f"srt://127.0.0.1:8890"
            f"?streamid=read:{stream_identifier}"
            f"&latency=100000"
            f"&pkt_size=1316"
        )
        self.sig_play_stream.emit(srt_read_url)

    @Slot()
    def apply_display_position(self) -> None:
        """
        根据当前会话的显示模式配置，重新定位窗口到目标显示器。
        从 DisplayTarget 数据读取坐标并发射 reposition 信号。
        """
        from scp_cv.services.playback import get_or_create_session
        from scp_cv.services.display import list_display_targets, build_left_right_splice_target
        from scp_cv.apps.playback.models import PlaybackMode

        session = get_or_create_session()
        display_targets = list_display_targets()

        if session.display_mode == PlaybackMode.LEFT_RIGHT_SPLICE:
            splice_target = build_left_right_splice_target(display_targets)
            if splice_target is not None:
                rect = QRect(
                    splice_target.left.x,
                    splice_target.left.y,
                    splice_target.width,
                    splice_target.height,
                )
                self.sig_reposition.emit(rect)
                return

        # 单屏模式：找到匹配的显示器
        target_label = session.target_display_label
        matched_display = next(
            (dt for dt in display_targets if dt.name == target_label),
            None,
        )
        if matched_display is not None:
            rect = QRect(
                matched_display.x, matched_display.y,
                matched_display.width, matched_display.height,
            )
            self.sig_reposition.emit(rect)
        elif display_targets:
            # 回退到第一个显示器
            fallback_display = display_targets[0]
            rect = QRect(
                fallback_display.x, fallback_display.y,
                fallback_display.width, fallback_display.height,
            )
            self.sig_reposition.emit(rect)
