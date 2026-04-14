#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
帧同步协调器：管理多个 GStreamer 管线间的时钟共享和延迟漂移检测。
确保多屏播放时所有管线渲染同一帧，防止长时间运行后延迟累积。
@Project : SCP-cv
@File : frame_sync.py
@Author : Qintsg
@Date : 2026-04-14
'''
from __future__ import annotations

import logging
import threading
import time
from typing import Optional

from scp_cv.player import init_gstreamer

init_gstreamer()

import gi  # noqa: E402
gi.require_version('Gst', '1.0')
from gi.repository import Gst  # noqa: E402

from scp_cv.player.gst_pipeline import GstWebRTCPipeline  # noqa: E402

logger = logging.getLogger(__name__)

# 帧同步漂移阈值（纳秒），超过此值触发重同步
# 33ms ≈ 1 帧 @30fps，16ms ≈ 1 帧 @60fps
_DEFAULT_DRIFT_THRESHOLD_NS: int = 33_000_000


class FrameSyncCoordinator:
    """
    帧同步协调器：让多个 GStreamer 管线共享同一时钟，确保帧级同步。

    工作原理：
    1. 第一个注册的管线成为"时钟主节点"，提供参考时钟
    2. 后续管线使用主节点的时钟，所有渲染基于相同时基
    3. 后台监控线程周期性检测管线间的播放位置漂移
    4. 漂移超过阈值时执行重同步（刷新时钟基准）

    单流防漂移：
    GStreamer videosink 的 sync=True 保证帧按 PTS 渲染，不累积延迟。
    WebRTC 的 RTCP 反馈机制处理网络抖动，jitter buffer 平滑到达时间。
    """

    def __init__(
        self,
        drift_threshold_ns: int = _DEFAULT_DRIFT_THRESHOLD_NS,
    ) -> None:
        """
        初始化帧同步协调器。
        :param drift_threshold_ns: 漂移检测阈值（纳秒），默认 33ms
        """
        self._master_clock: Optional[Gst.Clock] = None
        self._pipelines: list[GstWebRTCPipeline] = []
        self._drift_threshold_ns = drift_threshold_ns
        self._monitor_running = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    @property
    def master_clock(self) -> Optional[Gst.Clock]:
        """当前主时钟（第一个注册管线的时钟）。"""
        return self._master_clock

    @property
    def pipeline_count(self) -> int:
        """已注册管线数量。"""
        return len(self._pipelines)

    def get_shared_clock(self) -> Optional[Gst.Clock]:
        """
        获取共享时钟。供新管线在创建时使用。
        若尚无主时钟，返回 None（第一个管线将成为主节点）。
        :return: 共享时钟或 None
        """
        return self._master_clock

    def register_pipeline(self, pipeline: GstWebRTCPipeline) -> None:
        """
        注册管线到帧同步组。
        第一个注册的管线成为时钟主节点，后续管线共享其时钟。
        :param pipeline: 已创建但尚未播放的 GStreamer 管线
        """
        with self._lock:
            self._pipelines.append(pipeline)

            if self._master_clock is None:
                # 第一个管线：等待其启动后获取时钟
                logger.info("帧同步：管线 #1 注册为时钟主节点（时钟待管线启动后获取）")
            else:
                # 后续管线：立即设置共享时钟
                pipeline.use_clock(self._master_clock)
                logger.info(
                    "帧同步：管线 #%d 已注册并使用共享时钟",
                    len(self._pipelines),
                )

    def update_master_clock(self, pipeline: GstWebRTCPipeline) -> None:
        """
        从指定管线获取时钟并设置为主时钟。
        通常在第一个管线启动播放后调用。
        :param pipeline: 已启动的管线
        """
        with self._lock:
            clock = pipeline.get_clock()
            if clock is not None:
                self._master_clock = clock
                # 同步到已注册的其它管线
                for registered_pipeline in self._pipelines:
                    if registered_pipeline is not pipeline:
                        registered_pipeline.use_clock(clock)
                logger.info("帧同步：主时钟已建立")

    def start_drift_monitoring(
        self,
        check_interval_seconds: float = 1.0,
    ) -> None:
        """
        启动漂移监控后台线程。
        周期性检查所有管线的播放位置差异，超过阈值时触发重同步。
        :param check_interval_seconds: 检查间隔（秒）
        """
        if self._monitor_running:
            return

        self._monitor_running = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(check_interval_seconds,),
            daemon=True,
            name="frame-sync-monitor",
        )
        self._monitor_thread.start()
        logger.info(
            "帧同步漂移监控已启动（间隔 %.1fs，阈值 %.1fms）",
            check_interval_seconds,
            self._drift_threshold_ns / 1_000_000,
        )

    def stop_drift_monitoring(self) -> None:
        """停止漂移监控线程。"""
        self._monitor_running = False
        if self._monitor_thread is not None:
            self._monitor_thread.join(timeout=3.0)
            self._monitor_thread = None
            logger.info("帧同步漂移监控已停止")

    def clear(self) -> None:
        """清空所有注册管线并停止监控。"""
        self.stop_drift_monitoring()
        with self._lock:
            self._pipelines.clear()
            self._master_clock = None
        logger.info("帧同步协调器已清空")

    # ═══════════════════ 监控逻辑 ═══════════════════

    def _monitor_loop(self, interval_seconds: float) -> None:
        """
        漂移监控循环：周期性检查管线间播放位置差异。
        :param interval_seconds: 检查间隔
        """
        while self._monitor_running:
            self._check_drift()
            time.sleep(interval_seconds)

    def _check_drift(self) -> None:
        """
        检查所有管线的播放位置漂移。
        若最大差异超过阈值，触发重同步。
        """
        with self._lock:
            active_pipelines = [
                pipeline for pipeline in self._pipelines
                if pipeline.is_connected
            ]

        if len(active_pipelines) < 2:
            return

        # 收集各管线的当前播放位置
        positions: list[int] = []
        for pipeline in active_pipelines:
            position = pipeline.query_position_ns()
            if position is not None:
                positions.append(position)

        if len(positions) < 2:
            return

        # 计算最大漂移
        max_drift_ns = max(positions) - min(positions)
        if max_drift_ns > self._drift_threshold_ns:
            logger.warning(
                "帧同步漂移检测：%.1fms（阈值 %.1fms），触发重同步",
                max_drift_ns / 1_000_000,
                self._drift_threshold_ns / 1_000_000,
            )
            self._resync_pipelines(active_pipelines)

    def _resync_pipelines(
        self,
        pipelines: list[GstWebRTCPipeline],
    ) -> None:
        """
        重同步管线：刷新时钟基准强制重新对齐。
        :param pipelines: 需要重同步的管线列表
        """
        if self._master_clock is None:
            return

        for pipeline in pipelines:
            gst_pipeline = pipeline.gst_pipeline
            if gst_pipeline is not None:
                # 重置起始时间让管线重新对齐时钟
                gst_pipeline.set_start_time(Gst.CLOCK_TIME_NONE)
                pipeline.use_clock(self._master_clock)

        logger.info("帧同步重校准完成（%d 管线）", len(pipelines))
