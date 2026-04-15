#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
视频源适配器，通过 QMediaPlayer 播放本地视频文件。
视频输出到 QVideoWidget 并嵌入 PlayerWindow 的渲染容器。
@Project : SCP-cv
@File : video.py
@Author : Qintsg
@Date : 2026-04-15
'''
from __future__ import annotations

import logging
import os
from typing import Optional

from PySide6.QtCore import QUrl, Slot
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import QWidget

from scp_cv.player.adapters.base import AdapterState, SourceAdapter

logger = logging.getLogger(__name__)


class VideoSourceAdapter(SourceAdapter):
    """
    本地视频文件播放适配器。

    使用 Qt 6 的 QMediaPlayer 渲染视频，输出到 QVideoWidget。
    支持播放 / 暂停 / 停止 / 跳转 / 循环播放等时间线操作。

    与 PlayerWindow 的集成：
    - QVideoWidget 作为子 widget 嵌入到播放器窗口的视频容器中
    - 窗口大小变化时自动跟随
    """

    def __init__(self) -> None:
        super().__init__(adapter_name="video")
        self._media_player: Optional[QMediaPlayer] = None
        self._audio_output: Optional[QAudioOutput] = None
        self._video_widget: Optional[QVideoWidget] = None
        self._duration_ms: int = 0
        self._file_path: str = ""
        self._has_error: bool = False
        self._error_message: str = ""
        self._loop_enabled: bool = False

    def open(self, uri: str, window_handle: int, autoplay: bool = True) -> None:
        """
        打开视频文件并准备播放。
        创建 QMediaPlayer 和 QVideoWidget，嵌入目标窗口。
        :param uri: 视频文件绝对路径
        :param window_handle: 渲染目标窗口的原生句柄
        :param autoplay: 是否自动开始播放
        """
        if not os.path.isfile(uri):
            raise FileNotFoundError(f"视频文件不存在：{uri}")

        self._file_path = uri
        self._has_error = False
        self._error_message = ""

        # 查找目标窗口的视频容器
        parent_widget = self._find_widget_by_handle(window_handle)

        # 创建视频输出组件
        self._video_widget = QVideoWidget(parent_widget)
        if parent_widget is not None:
            self._video_widget.setGeometry(parent_widget.rect())
            self._video_widget.show()

        # 创建音频输出
        self._audio_output = QAudioOutput()
        self._audio_output.setVolume(1.0)

        # 创建播放器
        self._media_player = QMediaPlayer()
        self._media_player.setVideoOutput(self._video_widget)
        self._media_player.setAudioOutput(self._audio_output)

        # 连接信号
        self._media_player.durationChanged.connect(self._on_duration_changed)
        self._media_player.errorOccurred.connect(self._on_error)
        self._media_player.mediaStatusChanged.connect(self._on_media_status_changed)

        # 设置源
        self._media_player.setSource(QUrl.fromLocalFile(uri))

        if autoplay:
            self._media_player.play()

        self._mark_open()
        self._logger.info("视频已打开：%s", uri)

    @staticmethod
    def _find_widget_by_handle(window_handle: int) -> Optional[QWidget]:
        """
        通过原生窗口句柄查找对应的 QWidget。
        :param window_handle: 原生窗口句柄
        :return: 对应的 QWidget，找不到返回 None
        """
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            return None

        for widget in app.allWidgets():
            if int(widget.winId()) == window_handle:
                return widget
        return None

    def close(self) -> None:
        """关闭视频并释放资源。"""
        if self._media_player is not None:
            self._media_player.stop()
            self._media_player.setVideoOutput(None)
            self._media_player.setAudioOutput(None)
            self._media_player.deleteLater()
            self._media_player = None

        if self._audio_output is not None:
            self._audio_output.deleteLater()
            self._audio_output = None

        if self._video_widget is not None:
            self._video_widget.hide()
            self._video_widget.deleteLater()
            self._video_widget = None

        self._duration_ms = 0
        self._has_error = False
        self._error_message = ""
        self._loop_enabled = False
        self._mark_closed()
        self._logger.info("视频已关闭")

    # ═══════════════════ 播放控制 ═══════════════════

    def play(self) -> None:
        """开始/恢复播放。"""
        if self._media_player is not None:
            self._media_player.play()

    def pause(self) -> None:
        """暂停播放。"""
        if self._media_player is not None:
            self._media_player.pause()

    def stop(self) -> None:
        """停止播放（不释放资源）。"""
        if self._media_player is not None:
            self._media_player.stop()

    # ═══════════════════ 时间线导航 ═══════════════════

    def seek(self, position_ms: int) -> None:
        """
        跳转到指定时间位置。
        :param position_ms: 目标位置（毫秒）
        """
        if self._media_player is not None:
            clamped_position = max(0, min(position_ms, self._duration_ms))
            self._media_player.setPosition(clamped_position)
            self._logger.debug("视频跳转到 %d ms", clamped_position)

    def set_loop(self, enabled: bool) -> None:
        """
        设置循环播放。开启后视频播放完毕会自动从头开始。
        :param enabled: 是否启用循环播放
        """
        self._loop_enabled = enabled
        self._logger.info("循环播放已%s", "开启" if enabled else "关闭")

    # ═══════════════════ 状态获取 ═══════════════════

    def get_state(self) -> AdapterState:
        """
        获取视频播放状态。
        :return: 包含播放位置和总时长的状态快照
        """
        if self._has_error:
            return AdapterState(
                playback_state="error",
                error_message=self._error_message,
            )

        if self._media_player is None:
            return AdapterState(playback_state="idle")

        # QMediaPlayer.PlaybackState 枚举映射
        qt_state = self._media_player.playbackState()
        state_map = {
            QMediaPlayer.PlaybackState.StoppedState: "stopped",
            QMediaPlayer.PlaybackState.PlayingState: "playing",
            QMediaPlayer.PlaybackState.PausedState: "paused",
        }
        playback_state = state_map.get(qt_state, "idle")

        return AdapterState(
            playback_state=playback_state,
            position_ms=self._media_player.position(),
            duration_ms=self._duration_ms,
        )

    # ═══════════════════ 信号处理 ═══════════════════

    @Slot(int)
    def _on_duration_changed(self, duration_ms: int) -> None:
        """
        媒体时长变更回调。
        :param duration_ms: 总时长（毫秒）
        """
        self._duration_ms = duration_ms
        self._logger.debug("视频时长：%d ms", duration_ms)

    @Slot(QMediaPlayer.Error, str)
    def _on_error(self, error: QMediaPlayer.Error, error_string: str) -> None:
        """
        播放器错误回调。
        :param error: 错误码
        :param error_string: 错误描述
        """
        if error != QMediaPlayer.Error.NoError:
            self._has_error = True
            self._error_message = error_string
            self._logger.error("视频播放器错误：%s", error_string)

    @Slot(QMediaPlayer.MediaStatus)
    def _on_media_status_changed(self, status: QMediaPlayer.MediaStatus) -> None:
        """
        媒体状态变更回调，用于实现循环播放。
        当媒体播放到末尾且循环模式开启时，自动从头播放。
        :param status: 新的媒体状态
        """
        if (status == QMediaPlayer.MediaStatus.EndOfMedia
                and self._loop_enabled
                and self._media_player is not None):
            self._logger.info("视频播放完毕，循环模式已开启，重新播放")
            self._media_player.setPosition(0)
            self._media_player.play()
