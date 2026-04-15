#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
GStreamer WebRTC 播放管线：通过 webrtcbin + WHEP 接收 WebRTC 流并渲染到指定窗口。
支持时钟共享实现多管线帧同步。

非阻塞设计：
- build_pipeline() 构建管线元素
- start_playing() 将管线设为 PLAYING 状态，触发协商
- ICE 收集完成后通过 on_ice_complete 回调通知上层
- 上层执行 WHEP SDP 交换后调用 set_remote_answer() 设置 Answer

所有 GStreamer 信号通过 GLib MainContext 处理，
由 PlayerController 的 GLib 事件泵在 Qt 主线程中驱动。
@Project : SCP-cv
@File : gst_pipeline.py
@Author : Qintsg
@Date : 2026-04-14
'''
from __future__ import annotations

import logging
import threading
from typing import Callable, Optional

from scp_cv.player import init_gstreamer

# GStreamer 必须在导入 gi 模块前初始化
init_gstreamer()

import gi  # noqa: E402
gi.require_version('Gst', '1.0')
gi.require_version('GstWebRTC', '1.0')
gi.require_version('GstSdp', '1.0')
gi.require_version('GstVideo', '1.0')
from gi.repository import Gst, GstSdp, GstVideo, GstWebRTC  # noqa: E402

logger = logging.getLogger(__name__)


class GstWebRTCPipeline:
    """
    GStreamer WebRTC 播放管线。

    通过 WHEP 协议从 MediaMTX 接收 WebRTC 流，
    decodebin 动态解码后渲染到指定窗口句柄。

    非阻塞生命周期：
    1. 创建实例，传入 WHEP URL 和目标窗口句柄
    2. build_pipeline() 构建管线
    3. start_playing() 启动管线，触发协商
    4. ICE 收集完成 → on_ice_complete 回调
    5. 外部执行 WHEP 交换 → set_remote_answer() 设置 Answer
    6. stop() 停止管线并释放资源
    """

    def __init__(
        self,
        whep_url: str,
        window_handle: int,
        shared_clock: Optional[Gst.Clock] = None,
        on_playing: Optional[Callable[[], None]] = None,
        on_ice_complete: Optional[Callable[[str], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
    ) -> None:
        """
        初始化 WebRTC 播放管线（不立即连接）。
        :param whep_url: WHEP 端点 URL（如 http://127.0.0.1:8889/stream/whep）
        :param window_handle: 视频渲染目标窗口的原生句柄 (int(QWidget.winId()))
        :param shared_clock: 多管线帧同步共享时钟（可选）
        :param on_playing: 开始播放时的回调
        :param on_ice_complete: ICE 收集完成回调，参数为完整 SDP Offer 文本
        :param on_error: 错误发生时的回调
        """
        self._whep_url = whep_url
        self._window_handle = window_handle
        self._shared_clock = shared_clock
        self._on_playing = on_playing
        self._on_ice_complete = on_ice_complete
        self._on_error = on_error

        self._pipeline: Optional[Gst.Pipeline] = None
        self._webrtcbin: Optional[Gst.Element] = None

        self._is_connected = False
        self._lock = threading.Lock()

        logger.debug(
            "GstWebRTCPipeline 已创建（whep=%s, handle=%d）",
            whep_url, window_handle,
        )

    @property
    def is_connected(self) -> bool:
        """管线是否已成功连接并播放。"""
        return self._is_connected

    @property
    def gst_pipeline(self) -> Optional[Gst.Pipeline]:
        """底层 GStreamer Pipeline 对象（用于时钟共享等操作）。"""
        return self._pipeline

    # ═══════════════════ 非阻塞生命周期 ═══════════════════

    def build_pipeline(self) -> None:
        """
        构建 GStreamer 管线：webrtcbin → decodebin → videoconvert → videosink。
        应在 Qt 主线程中调用。管线构建后处于 NULL 状态。
        :raises RuntimeError: 无法创建 webrtcbin 元素
        """
        with self._lock:
            self._build_pipeline_internal()

    def start_playing(self) -> None:
        """
        将管线设为 PLAYING 状态。
        触发 webrtcbin 的 on-negotiation-needed → 创建 offer → ICE 收集。
        ICE 收集由 GLib MainContext 事件泵驱动，完成后触发 on_ice_complete 回调。
        """
        if self._pipeline is None:
            logger.error("管线未构建，无法启动")
            return
        self._pipeline.set_state(Gst.State.PLAYING)
        logger.info("管线已设为 PLAYING，等待 ICE 收集")

    def set_remote_answer(self, answer_sdp: str) -> None:
        """
        设置远端 SDP Answer（WHEP 交换后调用）。
        可从任何线程安全调用（GStreamer 内部会处理线程安全）。
        :param answer_sdp: 远端返回的 SDP Answer 文本
        :raises RuntimeError: SDP 解析失败
        """
        if self._webrtcbin is None:
            logger.error("webrtcbin 不存在，无法设置 Answer")
            return

        # 解析 SDP Answer
        parse_result, sdp_message = GstSdp.SDPMessage.new_from_text(answer_sdp)
        if parse_result != GstSdp.SDPResult.OK:
            error_msg = "解析 SDP Answer 失败"
            self._notify_error(error_msg)
            raise RuntimeError(error_msg)

        answer_desc = GstWebRTC.WebRTCSessionDescription.new(
            GstWebRTC.WebRTCSDPType.ANSWER, sdp_message,
        )
        promise = Gst.Promise.new()
        self._webrtcbin.emit("set-remote-description", answer_desc, promise)
        promise.interrupt()

        self._is_connected = True
        logger.info("远端 SDP Answer 已设置，WebRTC 连接建立完成")

        if self._on_playing is not None:
            try:
                self._on_playing()
            except Exception as callback_error:
                logger.warning("播放回调异常：%s", callback_error)

    def stop(self) -> None:
        """
        停止管线并释放所有资源。
        幂等操作，可安全重复调用。
        """
        with self._lock:
            self._is_connected = False

            if self._pipeline is not None:
                self._pipeline.set_state(Gst.State.NULL)
                self._pipeline = None
                self._webrtcbin = None

        logger.info("GStreamer 管线已停止")

    def get_clock(self) -> Optional[Gst.Clock]:
        """
        获取管线当前使用的时钟（供帧同步协调器共享给其它管线）。
        :return: GStreamer 时钟对象，管线未启动时返回 None
        """
        if self._pipeline is not None:
            return self._pipeline.get_clock()
        return None

    def use_clock(self, clock: Gst.Clock) -> None:
        """
        设置外部共享时钟，用于多管线帧同步。
        必须在 start_playing() 之前调用。
        :param clock: 共享 GStreamer 时钟
        """
        self._shared_clock = clock
        if self._pipeline is not None:
            self._pipeline.use_clock(clock)
            logger.debug("管线已切换到共享时钟")

    def query_position_ns(self) -> Optional[int]:
        """
        查询管线当前播放位置（纳秒）。
        :return: 播放位置纳秒数，查询失败返回 None
        """
        if self._pipeline is None:
            return None
        query_ok, position = self._pipeline.query_position(Gst.Format.TIME)
        if query_ok:
            return position
        return None

    # ═══════════════════ 内部方法 ═══════════════════

    def _build_pipeline_internal(self) -> None:
        """
        构建 GStreamer 管线元素和信号连接。
        管线结构：webrtcbin → decodebin → videoconvert → videosink
        """
        self._pipeline = Gst.Pipeline.new("whep-pipeline")

        # 若指定了共享时钟，替换管线默认时钟
        if self._shared_clock is not None:
            self._pipeline.use_clock(self._shared_clock)

        # webrtcbin：WebRTC 接收端
        self._webrtcbin = Gst.ElementFactory.make("webrtcbin", "recv")
        if self._webrtcbin is None:
            raise RuntimeError(
                "无法创建 webrtcbin 元素。请确认 GStreamer bad plugins 已安装。"
            )

        # 设置 bundle policy（合并音视频到单个传输通道）
        self._webrtcbin.set_property(
            "bundle-policy",
            GstWebRTC.WebRTCBundlePolicy.MAX_BUNDLE,
        )

        # 添加视频 transceiver（仅接收模式）
        video_caps = Gst.caps_from_string(
            "application/x-rtp,media=video,encoding-name=H264,clock-rate=90000"
        )
        self._webrtcbin.emit(
            "add-transceiver",
            GstWebRTC.WebRTCRTPTransceiverDirection.RECVONLY,
            video_caps,
        )

        # 添加音频 transceiver（仅接收，大屏场景通常不输出音频）
        audio_caps = Gst.caps_from_string(
            "application/x-rtp,media=audio,encoding-name=OPUS,clock-rate=48000"
        )
        self._webrtcbin.emit(
            "add-transceiver",
            GstWebRTC.WebRTCRTPTransceiverDirection.RECVONLY,
            audio_caps,
        )

        self._pipeline.add(self._webrtcbin)

        # 连接 webrtcbin 信号
        self._webrtcbin.connect(
            "on-negotiation-needed", self._on_negotiation_needed,
        )
        self._webrtcbin.connect("pad-added", self._on_pad_added)
        self._webrtcbin.connect(
            "notify::ice-gathering-state",
            self._on_ice_gathering_state_changed,
        )
        self._webrtcbin.connect("on-ice-candidate", self._on_ice_candidate)

        # Bus：同步消息（窗口句柄绑定）+ 异步消息（错误/EOS）
        bus = self._pipeline.get_bus()
        bus.enable_sync_message_emission()
        bus.connect("sync-message::element", self._on_bus_sync_message)
        bus.add_signal_watch()
        bus.connect("message::error", self._on_bus_error)
        bus.connect("message::eos", self._on_bus_eos)

    def _on_negotiation_needed(self, webrtcbin: Gst.Element) -> None:
        """webrtcbin 请求协商 → 创建 SDP Offer。"""
        logger.info("webrtcbin 请求协商，创建 SDP Offer")
        promise = Gst.Promise.new_with_change_func(
            self._on_offer_created, webrtcbin, None,
        )
        webrtcbin.emit("create-offer", None, promise)

    def _on_offer_created(
        self,
        promise: Gst.Promise,
        webrtcbin: Gst.Element,
        _user_data: object,
    ) -> None:
        """SDP Offer 创建完成 → 设置为本地描述以触发 ICE 候选收集。"""
        promise.wait()
        reply = promise.get_reply()
        if reply is None:
            self._notify_error("创建 SDP Offer 失败：Promise 无回复")
            return

        offer = reply.get_value("offer")
        if offer is None:
            self._notify_error("创建 SDP Offer 失败：offer 为空")
            return

        # 设置本地描述 → 触发 ICE 候选收集
        set_promise = Gst.Promise.new()
        webrtcbin.emit("set-local-description", offer, set_promise)
        set_promise.interrupt()
        logger.debug("本地 SDP 描述已设置，等待 ICE 候选收集")

    def _on_ice_gathering_state_changed(
        self,
        webrtcbin: Gst.Element,
        _pspec: object,
    ) -> None:
        """
        ICE 候选收集状态变更。
        收集完成时提取完整 Offer SDP 并通过回调通知上层。
        """
        state = webrtcbin.get_property("ice-gathering-state")
        logger.debug("ICE 收集状态变更：%s", state.value_nick)

        if state == GstWebRTC.WebRTCICEGatheringState.COMPLETE:
            # 获取包含所有 ICE 候选的完整本地描述
            local_desc = webrtcbin.get_property("local-description")
            if local_desc is not None:
                complete_offer_sdp = local_desc.sdp.as_text()
                logger.info("ICE 收集完成，完整 Offer SDP 已就绪")

                # 通过回调通知上层执行 WHEP 交换
                if self._on_ice_complete is not None:
                    try:
                        self._on_ice_complete(complete_offer_sdp)
                    except Exception as callback_error:
                        logger.error("ICE 完成回调异常：%s", callback_error)
            else:
                self._notify_error("ICE 收集完成但无法获取本地 SDP 描述")

    def _on_ice_candidate(
        self,
        webrtcbin: Gst.Element,
        sdp_mline_index: int,
        candidate: str,
    ) -> None:
        """
        单个 ICE 候选生成回调（诊断用）。
        :param sdp_mline_index: SDP media line 索引
        :param candidate: ICE 候选 SDP 字符串
        """
        candidate_preview = candidate[:80] if candidate else "None"
        logger.info("ICE 候选生成: mline=%d, candidate=%s", sdp_mline_index, candidate_preview)

    def _on_pad_added(self, webrtcbin: Gst.Element, pad: Gst.Pad) -> None:
        """webrtcbin 新增 src pad → 连接 decodebin 动态解码。"""
        if pad.direction != Gst.PadDirection.SRC:
            return

        pad_name = pad.get_name()
        logger.debug("webrtcbin 新增 src pad：%s", pad_name)

        # 创建 decodebin 进行自动格式检测和解码
        decodebin = Gst.ElementFactory.make("decodebin3", None)
        if decodebin is None:
            # 回退到旧版 decodebin
            decodebin = Gst.ElementFactory.make("decodebin", None)
        if decodebin is None:
            logger.error("无法创建 decodebin 元素")
            return

        decodebin.connect("pad-added", self._on_decoded_pad_added)
        self._pipeline.add(decodebin)
        decodebin.sync_state_with_parent()

        link_result = pad.link(decodebin.get_static_pad("sink"))
        if link_result != Gst.PadLinkReturn.OK:
            logger.error(
                "webrtcbin → decodebin pad 链接失败：%s", link_result,
            )

    def _on_decoded_pad_added(
        self,
        decodebin: Gst.Element,
        pad: Gst.Pad,
    ) -> None:
        """decodebin 解码后输出 raw pad → 链接到视频/音频 sink。"""
        caps = pad.get_current_caps()
        if caps is None:
            return

        media_type = caps.get_structure(0).get_name()

        if media_type.startswith("video/"):
            self._connect_video_sink(pad)
        elif media_type.startswith("audio/"):
            # 大屏播放场景暂不处理音频输出
            logger.debug("跳过音频 pad：%s", media_type)
        else:
            logger.debug("跳过未知媒体类型 pad：%s", media_type)

    def _connect_video_sink(self, decoded_video_pad: Gst.Pad) -> None:
        """
        将解码后的视频 pad 连接到渲染 sink。
        Windows 优先使用 d3d11videosink（Direct3D 11 加速），
        依次回退到 glimagesink、autovideosink。
        :param decoded_video_pad: decodebin 输出的已解码视频 pad
        """
        videoconvert = Gst.ElementFactory.make("videoconvert", None)

        # Windows 优先 Direct3D 11 渲染 sink
        videosink = Gst.ElementFactory.make("d3d11videosink", None)
        if videosink is None:
            videosink = Gst.ElementFactory.make("glimagesink", None)
        if videosink is None:
            videosink = Gst.ElementFactory.make("autovideosink", None)

        if videoconvert is None or videosink is None:
            logger.error("无法创建视频渲染元素（videoconvert 或 videosink）")
            return

        # 启用时钟同步确保帧级对齐
        videosink.set_property("sync", True)

        self._pipeline.add(videoconvert)
        self._pipeline.add(videosink)
        videoconvert.sync_state_with_parent()
        videosink.sync_state_with_parent()

        decoded_video_pad.link(videoconvert.get_static_pad("sink"))
        videoconvert.link(videosink)

        sink_name = videosink.get_factory().get_name()
        logger.info("视频渲染管线已连接（sink=%s）", sink_name)

    def _on_bus_sync_message(
        self,
        bus: Gst.Bus,
        message: Gst.Message,
    ) -> Gst.BusSyncReply:
        """
        Bus 同步消息处理：在 streaming 线程中响应 prepare-window-handle。
        将视频 sink 的渲染输出绑定到 Qt 窗口句柄。
        """
        structure = message.get_structure()
        if structure is None:
            return Gst.BusSyncReply.PASS

        if structure.get_name() == "prepare-window-handle":
            # 将视频 sink 的输出绑定到 PySide6 窗口容器
            GstVideo.VideoOverlay.set_window_handle(
                message.src, self._window_handle,
            )
            logger.debug(
                "视频 sink 已绑定到窗口句柄 %d", self._window_handle,
            )
            return Gst.BusSyncReply.DROP

        return Gst.BusSyncReply.PASS

    def _on_bus_error(self, bus: Gst.Bus, message: Gst.Message) -> None:
        """Bus 错误消息处理：记录错误并通知上层。"""
        error, debug_info = message.parse_error()
        error_text = f"GStreamer 错误：{error.message}"
        if debug_info:
            error_text += f"（debug: {debug_info}）"
        self._notify_error(error_text)

    def _on_bus_eos(self, bus: Gst.Bus, message: Gst.Message) -> None:
        """Bus EOS 消息处理：流结束。"""
        logger.info("GStreamer 管线收到 EOS（流结束）")

    def _notify_error(self, error_message: str) -> None:
        """触发错误回调并记录日志。"""
        logger.error(error_message)
        if self._on_error is not None:
            try:
                self._on_error(error_message)
            except Exception as callback_error:
                logger.warning("错误回调自身异常：%s", callback_error)
