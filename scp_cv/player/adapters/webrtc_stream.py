#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
WebRTC 流适配器，封装 GStreamer WebRTC 管线。
通过 WHEP 协议接收 MediaMTX 的 WebRTC 流并渲染到窗口。

线程模型：
- open() 在 Qt 主线程中调用（由 PlayerController 保证）
- GStreamer 管线创建和启动在主线程执行
- GStreamer 信号（ICE 候选收集、pad 链接）通过 GLib MainContext 在主线程处理
  （由 PlayerController 的 GLib 事件泵驱动）
- WHEP SDP 交换在工作线程中执行（HTTP 请求，避免阻塞主线程）

ICE 候选收集完成后，工作线程执行 WHEP 交换并设置远端 SDP Answer。
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

    非阻塞设计：
    - open() 启动管线后立即返回（不等待 ICE 完成）
    - ICE 收集由 GLib 事件泵异步驱动
    - ICE 完成后在工作线程中执行 WHEP SDP 交换
    - 连接成功后标记为已打开
    """

    def __init__(self) -> None:
        super().__init__(adapter_name="webrtc_stream")
        # GStreamer 管线和同步器引用（延迟导入避免启动时加载 Gst）
        self._pipeline: Optional[object] = None
        self._frame_sync: Optional[object] = None
        self._whep_url: str = ""
        self._window_handle: int = 0
        self._is_connected: bool = False
        # WHEP 交换线程
        self._whep_thread: Optional[threading.Thread] = None

    def open(self, uri: str, window_handle: int, autoplay: bool = True) -> None:
        """
        启动 WebRTC 流连接。在 Qt 主线程中调用。
        管线创建和启动在主线程进行，ICE 收集通过 GLib 事件泵异步处理。
        open() 不阻塞等待连接完成。
        :param uri: WHEP 端点 URL（如 http://127.0.0.1:8889/stream_id/whep）
        :param window_handle: 渲染目标窗口的原生句柄
        :param autoplay: 是否自动开始播放（WebRTC 流总是自动播放）
        """
        self._whep_url = uri
        self._window_handle = window_handle
        self._is_connected = False

        self._start_pipeline()

        # 立即标记为已打开（实际连接在异步回调中完成）
        self._mark_open()
        self._logger.info("WebRTC 管线已启动，等待 ICE 收集完成：%s", uri)

    def _start_pipeline(self) -> None:
        """
        在 Qt 主线程中创建并启动 GStreamer 管线。
        管线的 on-negotiation-needed → create-offer → ICE 收集
        由 GLib MainContext 事件泵驱动。
        """
        from scp_cv.player.gst_pipeline import GstWebRTCPipeline
        from scp_cv.player.frame_sync import FrameSyncCoordinator

        # 停止旧管线
        self._stop_pipeline()

        # 创建帧同步器
        self._frame_sync = FrameSyncCoordinator()
        shared_clock = self._frame_sync.get_shared_clock()

        # 创建 GStreamer 管线（ICE 完成后回调 _on_ice_complete）
        pipeline = GstWebRTCPipeline(
            whep_url=self._whep_url,
            window_handle=self._window_handle,
            shared_clock=shared_clock,
            on_ice_complete=self._on_ice_gathering_complete,
            on_error=self._on_pipeline_error,
        )

        # 注册到帧同步器
        self._frame_sync.register_pipeline(pipeline)

        # 构建管线元素
        pipeline.build_pipeline()

        # 启动管线 → 触发 on-negotiation-needed → create-offer → ICE 收集
        pipeline.start_playing()

        self._pipeline = pipeline

    def _on_ice_gathering_complete(self, offer_sdp: str) -> None:
        """
        ICE 候选收集完成回调（在 GLib 事件上下文中触发）。
        在工作线程中执行 WHEP SDP 交换，避免阻塞事件循环。
        :param offer_sdp: 包含所有 ICE 候选的完整 SDP Offer
        """
        self._logger.info("ICE 收集完成，启动 WHEP SDP 交换")

        self._whep_thread = threading.Thread(
            target=self._exchange_sdp_and_connect,
            args=(offer_sdp,),
            daemon=True,
            name="webrtc-whep-exchange",
        )
        self._whep_thread.start()

    def _exchange_sdp_and_connect(self, offer_sdp: str) -> None:
        """
        工作线程：执行 WHEP SDP 交换并设置远端 Answer。
        :param offer_sdp: 本地 SDP Offer
        """
        if self._pipeline is None:
            return

        try:
            from scp_cv.player.whep_client import WhepClient

            whep_client = WhepClient(self._whep_url)
            answer_sdp = whep_client.exchange_sdp(offer_sdp)

            # 设置远端 SDP Answer（GStreamer 线程安全操作）
            self._pipeline.set_remote_answer(answer_sdp)

            # 更新主时钟
            if self._frame_sync is not None:
                self._frame_sync.update_master_clock(self._pipeline)

            self._is_connected = True
            self._logger.info("WebRTC 连接已建立：%s", self._whep_url)

        except (ConnectionError, RuntimeError) as connect_error:
            self._logger.error("WHEP SDP 交换失败：%s", connect_error)
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
            # 查询播放位置
            position_ns = 0
            try:
                position_ns = self._pipeline.query_position_ns()
            except Exception:
                pass

            return AdapterState(
                playback_state="playing",
                position_ms=position_ns // 1_000_000 if position_ns > 0 else 0,
            )

        # 管线存在但未连接 → 正在连接中
        if self._pipeline is not None and not self._is_connected:
            return AdapterState(playback_state="loading")

        return AdapterState(playback_state="idle")
