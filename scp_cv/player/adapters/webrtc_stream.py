#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
WebRTC 流适配器，封装现有 GStreamer WebRTC 管线。
通过 WHEP 协议接收 MediaMTX 的 WebRTC 流并渲染到窗口。
@Project : SCP-cv
@File : webrtc_stream.py
@Author : Qintsg
@Date : 2026-04-15
'''
from __future__ import annotations

import logging
import threading
from typing import Optional

from scp_cv.player.adapters.base import AdapterState, SourceAdapter

logger = logging.getLogger(__name__)


class WebRTCStreamAdapter(SourceAdapter):
    """
    WebRTC 流播放适配器，封装 GstWebRTCPipeline。

    通过 WHEP 协议从 MediaMTX 接收 WebRTC 流，
    使用 GStreamer webrtcbin 解码后渲染到 d3d11videosink。

    帧同步：
    - 多窗口场景下使用 FrameSyncCoordinator 共享 GStreamer 时钟
    - 漂移超过阈值时自动重同步
    """

    def __init__(self) -> None:
        super().__init__(adapter_name="webrtc_stream")
        # GStreamer 管线和同步器引用（延迟导入避免启动时加载 Gst）
        self._pipeline: Optional[object] = None
        self._frame_sync: Optional[object] = None
        self._whep_url: str = ""
        self._window_handle: int = 0
        self._is_connected: bool = False
        # WebRTC 连接在工作线程中执行（阻塞操作）
        self._connect_thread: Optional[threading.Thread] = None
        self._connect_lock = threading.Lock()

    def open(self, uri: str, window_handle: int, autoplay: bool = True) -> None:
        """
        连接 WebRTC 流。URI 为 WHEP 端点 URL。
        :param uri: WHEP 端点 URL（如 http://127.0.0.1:8889/stream_id/whep）
        :param window_handle: 渲染目标窗口的原生句柄
        :param autoplay: 是否自动开始播放（WebRTC 流总是自动播放）
        """
        self._whep_url = uri
        self._window_handle = window_handle
        self._is_connected = False

        # 在工作线程中执行 WHEP 连接（阻塞操作）
        with self._connect_lock:
            if self._connect_thread is not None and self._connect_thread.is_alive():
                self._logger.warning("上一次连接仍在进行中，等待完成")
                self._connect_thread.join(timeout=5.0)

            self._connect_thread = threading.Thread(
                target=self._connect_stream,
                daemon=True,
                name="webrtc-adapter-connect",
            )
            self._connect_thread.start()
            # 等待连接完成（最多 15 秒）
            self._connect_thread.join(timeout=15.0)

        if self._is_connected:
            self._mark_open()
            self._logger.info("WebRTC 流已连接：%s", uri)
        else:
            raise ConnectionError(f"WebRTC 流连接超时或失败：{uri}")

    def _connect_stream(self) -> None:
        """
        工作线程：创建 GStreamer 管线、执行 WHEP 协商、启动播放。
        """
        from scp_cv.player.gst_pipeline import GstWebRTCPipeline
        from scp_cv.player.frame_sync import FrameSyncCoordinator

        try:
            # 停止旧管线
            self._stop_pipeline()

            # 创建帧同步器（单管线也使用，保持接口一致）
            self._frame_sync = FrameSyncCoordinator()
            shared_clock = self._frame_sync.get_shared_clock()

            # 创建 GStreamer 管线
            pipeline = GstWebRTCPipeline(
                whep_url=self._whep_url,
                window_handle=self._window_handle,
                shared_clock=shared_clock,
                on_error=self._on_pipeline_error,
            )

            # 注册到帧同步器
            self._frame_sync.register_pipeline(pipeline)

            # 执行 WHEP 连接（阻塞）
            pipeline.connect_and_play()

            # 更新主时钟
            self._frame_sync.update_master_clock(pipeline)

            self._pipeline = pipeline
            self._is_connected = True

        except (TimeoutError, ConnectionError, RuntimeError) as connect_error:
            self._logger.error("WebRTC 流连接失败：%s", connect_error)
            self._is_connected = False

    def _on_pipeline_error(self, error_message: str) -> None:
        """
        GStreamer 管线错误回调。
        :param error_message: 错误描述
        """
        self._logger.error("GStreamer 管线错误：%s", error_message)
        self._is_connected = False

    def close(self) -> None:
        """断开 WebRTC 流并释放 GStreamer 资源。"""
        self._stop_pipeline()
        self._is_connected = False
        self._mark_closed()
        self._logger.info("WebRTC 流已断开")

    def _stop_pipeline(self) -> None:
        """停止 GStreamer 管线并清理帧同步。"""
        if self._frame_sync is not None:
            self._frame_sync.clear()
            self._frame_sync = None

        if self._pipeline is not None:
            try:
                self._pipeline.stop()
            except Exception as stop_error:
                self._logger.warning("停止管线异常：%s", stop_error)
            self._pipeline = None

    # ═══════════════════ 播放控制 ═══════════════════

    def play(self) -> None:
        """WebRTC 流不支持暂停后恢复，重新连接。"""
        if not self._is_connected and self._whep_url:
            self._logger.info("重新连接 WebRTC 流")
            self.open(self._whep_url, self._window_handle, autoplay=True)

    def pause(self) -> None:
        """WebRTC 实时流不支持暂停，忽略。"""
        self._logger.debug("WebRTC 流不支持暂停操作")

    def stop(self) -> None:
        """停止接收流。"""
        self._stop_pipeline()
        self._is_connected = False

    # ═══════════════════ 状态获取 ═══════════════════

    def get_state(self) -> AdapterState:
        """
        获取 WebRTC 流状态。
        :return: 流连接状态快照
        """
        if self._pipeline is not None and self._is_connected:
            # 查询播放位置（如果管线支持）
            position_ns = 0
            try:
                position_ns = self._pipeline.query_position_ns()
            except Exception:
                pass

            return AdapterState(
                playback_state="playing",
                position_ms=position_ns // 1_000_000 if position_ns > 0 else 0,
            )

        return AdapterState(playback_state="idle")
