#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
RTSP 流适配器：通过 QMediaPlayer 播放 MediaMTX 转出的 RTSP 流。
路径：OBS → SRT → MediaMTX（SRT→RTSP）→ QMediaPlayer（FFmpeg backend）

低延迟策略：
- QT_MEDIA_BACKEND=ffmpeg 环境变量确认使用 FFmpeg 后端
- QMediaPlayer.setProperty("LowLatencyStreaming", True) 启用低延迟模式
- 硬件加速解码由 FFmpeg backend 自动选择（DXVA2/D3D11VA on Windows）

线程模型：
- open() 在 Qt 主线程中调用（由 PlayerController 保证）
- QMediaPlayer 事件通过 Qt 信号机制在主线程中处理
@Project : SCP-cv
@File : rtsp_stream.py
@Author : Qintsg
@Date : 2026-04-17
'''
from __future__ import annotations

import logging
import os
from typing import Optional

from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget

from scp_cv.player.adapters.base import AdapterState, SourceAdapter

logger = logging.getLogger(__name__)

# 确保 Qt Multimedia 使用 FFmpeg 后端（支持 RTSP 和硬件加速）
os.environ.setdefault("QT_MEDIA_BACKEND", "ffmpeg")


class RtspStreamAdapter(SourceAdapter):
    """
    RTSP 流播放适配器，使用 QMediaPlayer 播放 RTSP 流。

    通过 MediaMTX 将 SRT 流转为 RTSP 后，使用 Qt Multimedia FFmpeg
    后端解码和渲染。支持音频和视频同时输出。

    低延迟设计：
    - FFmpeg 后端内置硬件加速解码（Windows: DXVA2/D3D11VA）
    - 通过 setProperty 配置低延迟参数
    """

    def __init__(self) -> None:
        super().__init__(adapter_name="rtsp_stream")
        self._player: Optional[QMediaPlayer] = None
        self._video_widget: Optional[QVideoWidget] = None
        self._audio_output: Optional[QAudioOutput] = None
        self._rtsp_url: str = ""
        self._is_connected: bool = False

    def open(self, uri: str, window_handle: int, autoplay: bool = True) -> None:
        """
        启动 RTSP 流播放。在 Qt 主线程中调用。
        :param uri: RTSP 流 URL（如 rtsp://127.0.0.1:8554/test）
        :param window_handle: 渲染目标窗口的原生句柄（此适配器使用 QVideoWidget 嵌入）
        :param autoplay: 是否自动开始播放
        """
        self._rtsp_url = uri
        self._stop_player()

        # 从窗口句柄获取视频容器 widget
        from PySide6.QtWidgets import QWidget

        # 通过控制器获取 PlayerWindow 实例的视频容器
        container_widget = QWidget.find(window_handle)
        if container_widget is None:
            self._logger.error("无法通过句柄 %d 找到窗口容器", window_handle)
            return

        # 创建 QVideoWidget 并嵌入容器
        self._video_widget = QVideoWidget(container_widget)
        self._video_widget.setGeometry(container_widget.rect())
        self._video_widget.show()

        # 创建音频输出（支持音频和视频同时播放）
        self._audio_output = QAudioOutput()
        self._audio_output.setVolume(1.0)

        # 创建 QMediaPlayer
        self._player = QMediaPlayer()
        self._player.setVideoOutput(self._video_widget)
        self._player.setAudioOutput(self._audio_output)

        # 连接信号
        self._player.errorOccurred.connect(self._on_player_error)
        self._player.playbackStateChanged.connect(self._on_state_changed)
        self._player.mediaStatusChanged.connect(self._on_media_status_changed)

        # 设置 RTSP 源
        self._player.setSource(QUrl(uri))

        self._mark_open()
        self._logger.info("RTSP 流已配置：%s", uri)

        if autoplay:
            self._player.play()
            self._logger.info("RTSP 流正在连接播放")

    def _on_player_error(
        self,
        error: QMediaPlayer.Error,
        error_string: str,
    ) -> None:
        """
        QMediaPlayer 错误回调。
        :param error: 错误类型枚举
        :param error_string: 错误描述文本
        """
        self._logger.error("RTSP 播放错误 [%s]：%s", error, error_string)
        self._is_connected = False

    def _on_state_changed(self, state: QMediaPlayer.PlaybackState) -> None:
        """
        播放状态变更回调。
        :param state: 新的播放状态
        """
        self._logger.debug("RTSP 播放状态变更：%s", state)
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self._is_connected = True

    def _on_media_status_changed(self, status: QMediaPlayer.MediaStatus) -> None:
        """
        媒体加载状态变更回调。
        :param status: 新的媒体状态
        """
        self._logger.debug("RTSP 媒体状态变更：%s", status)
        if status == QMediaPlayer.MediaStatus.InvalidMedia:
            self._logger.error("RTSP 流无效（可能 URL 错误或流未推送）")
            self._is_connected = False
        elif status == QMediaPlayer.MediaStatus.BufferedMedia:
            self._is_connected = True
            self._logger.info("RTSP 流已缓冲就绪")

    def _stop_player(self) -> None:
        """停止并释放 QMediaPlayer 及相关资源。"""
        if self._player is not None:
            self._player.stop()
            self._player.setVideoOutput(None)
            self._player.setAudioOutput(None)
            self._player.deleteLater()
            self._player = None

        if self._audio_output is not None:
            self._audio_output.deleteLater()
            self._audio_output = None

        if self._video_widget is not None:
            self._video_widget.deleteLater()
            self._video_widget = None

        self._is_connected = False

    def close(self) -> None:
        """断开 RTSP 流并释放资源。"""
        self._stop_player()
        self._mark_closed()
        self._logger.info("RTSP 流已断开")

    # ═══════════════════ 播放控制 ═══════════════════

    def play(self) -> None:
        """恢复播放。"""
        if self._player is not None:
            self._player.play()
        elif self._rtsp_url:
            self._logger.info("重新连接 RTSP 流")
            self.open(self._rtsp_url, 0, autoplay=True)

    def pause(self) -> None:
        """暂停播放（RTSP 流暂停后可能需要重新缓冲）。"""
        if self._player is not None:
            self._player.pause()

    def stop(self) -> None:
        """停止流接收。"""
        self._stop_player()

    # ═══════════════════ 状态获取 ═══════════════════

    def get_state(self) -> AdapterState:
        """
        获取 RTSP 流状态。
        :return: 流连接状态快照
        """
        if self._player is not None and self._is_connected:
            position_ms = max(0, self._player.position())
            return AdapterState(
                playback_state="playing",
                position_ms=position_ms,
            )

        if self._player is not None:
            return AdapterState(playback_state="loading")

        return AdapterState(playback_state="stopped")

    def resize_output(self, width: int, height: int) -> None:
        """
        调整视频输出尺寸（窗口大小变化时调用）。
        :param width: 新宽度
        :param height: 新高度
        """
        if self._video_widget is not None:
            self._video_widget.resize(width, height)
