#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
背景音频适配器：使用 Qt Multimedia 播放本机音频输出。
@Project : SCP-cv
@File : adapters/background_audio.py
@Author : Qintsg
@Date : 2026-05-31
'''
from __future__ import annotations

import os
from collections.abc import Callable
from typing import Optional

from PySide6.QtCore import QUrl, Slot
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer

from scp_cv.player.adapters.base import AdapterState, SourceAdapter
from scp_cv.player.preheat_types import PreheatedAudioSource


class BackgroundAudioAdapter(SourceAdapter):
    """
    后台背景音频播放适配器。
    不绑定 PlayerWindow，也不创建视频输出，只输出到本机默认音频设备。
    """

    def __init__(self, finished_callback: Callable[[], None] | None = None) -> None:
        super().__init__(adapter_name="background_audio")
        self._media_player: Optional[QMediaPlayer] = None
        self._audio_output: Optional[QAudioOutput] = None
        self._duration_ms = 0
        self._has_error = False
        self._error_message = ""
        self._finished_callback = finished_callback
        self._finished_notified = False
        self._uri = ""
        self._volume = 70
        self._muted = False

    @property
    def current_uri(self) -> str:
        """
        当前打开的背景音频 URI。
        :return: URI；未打开时返回空字符串
        """
        return self._uri

    def open(
        self,
        uri: str,
        window_handle: int = 0,
        autoplay: bool = True,
        preheated_audio: PreheatedAudioSource | None = None,
    ) -> None:
        """
        打开音频文件并准备播放。

        :param uri: 音频文件绝对路径或 URL
        :param window_handle: 背景音频不使用窗口句柄
        :param autoplay: 是否打开后自动播放
        :param preheated_audio: 已预热的背景音频资源
        :return: None
        """
        if not _is_remote_uri(uri) and not os.path.isfile(uri):
            raise FileNotFoundError(f"音频文件不存在：{uri}")

        self.close()
        self._has_error = False
        self._error_message = ""
        self._duration_ms = 0
        self._finished_notified = False
        self._uri = uri

        if preheated_audio is not None:
            self._audio_output = preheated_audio.audio_output
            self._media_player = preheated_audio.player
        else:
            self._audio_output = QAudioOutput()
            self._audio_output.setVolume(0.7)
            self._media_player = QMediaPlayer()
            self._media_player.setAudioOutput(self._audio_output)
            self._media_player.setSource(_url_for_uri(uri))
        self._media_player.durationChanged.connect(self._on_duration_changed)
        self._media_player.errorOccurred.connect(self._on_error)
        self._media_player.mediaStatusChanged.connect(self._on_media_status_changed)
        self._duration_ms = max(0, int(self._media_player.duration()))
        if autoplay:
            self._media_player.play()
        self._mark_open()
        self._logger.info("背景音频已打开：%s", uri)

    def close(self) -> None:
        """关闭音频并释放 Qt 资源。"""
        if self._media_player is not None:
            self._media_player.stop()
            self._media_player.setAudioOutput(None)
            self._media_player.deleteLater()
            self._media_player = None
        if self._audio_output is not None:
            self._audio_output.deleteLater()
            self._audio_output = None
        self._duration_ms = 0
        self._has_error = False
        self._error_message = ""
        self._finished_notified = False
        self._uri = ""
        self._mark_closed()

    def play(self) -> None:
        """开始或恢复播放。"""
        if self._media_player is not None:
            self._finished_notified = False
            self._media_player.play()

    def restart_current_source(self, autoplay: bool = True) -> None:
        """
        原地重启当前音频源，避免循环同源时销毁重建 QMediaPlayer 后无声。
        :param autoplay: 是否立即播放
        :return: None
        """
        if self._media_player is None:
            return
        self._finished_notified = False
        self._media_player.setPosition(0)
        self.set_volume(self._volume)
        self.set_mute(self._muted)
        if autoplay:
            self._media_player.play()
        else:
            self._media_player.pause()

    def pause(self) -> None:
        """暂停播放。"""
        if self._media_player is not None:
            self._media_player.pause()

    def stop(self) -> None:
        """停止播放并回到开头。"""
        if self._media_player is not None:
            self._media_player.stop()
            self._media_player.setPosition(0)

    def seek(self, position_ms: int) -> None:
        """
        跳转到指定时间位置。

        :param position_ms: 目标位置毫秒
        :return: None
        """
        if self._media_player is not None:
            clamped_position = max(0, min(int(position_ms), self._duration_ms or int(position_ms)))
            self._media_player.setPosition(clamped_position)

    def set_volume(self, volume: int) -> None:
        """
        设置音频音量。

        :param volume: 音量等级（0-100）
        :return: None
        """
        if self._audio_output is not None:
            self._volume = max(0, min(100, int(volume)))
            self._audio_output.setVolume(self._volume / 100)

    def set_mute(self, muted: bool) -> None:
        """
        设置静音状态。

        :param muted: 是否静音
        :return: None
        """
        if self._audio_output is not None:
            self._muted = bool(muted)
            self._audio_output.setMuted(self._muted)

    def get_state(self) -> AdapterState:
        """
        获取背景音频播放状态。

        :return: AdapterState 快照
        """
        if self._has_error:
            return AdapterState(playback_state="error", error_message=self._error_message)
        if self._media_player is None:
            return AdapterState(playback_state="idle")
        state_map = {
            QMediaPlayer.PlaybackState.StoppedState: "stopped",
            QMediaPlayer.PlaybackState.PlayingState: "playing",
            QMediaPlayer.PlaybackState.PausedState: "paused",
        }
        return AdapterState(
            playback_state=state_map.get(self._media_player.playbackState(), "idle"),
            position_ms=self._media_player.position(),
            duration_ms=self._duration_ms,
        )

    @Slot(int)
    def _on_duration_changed(self, duration_ms: int) -> None:
        """
        媒体时长变更回调。

        :param duration_ms: 总时长毫秒
        :return: None
        """
        self._duration_ms = duration_ms

    @Slot(QMediaPlayer.Error, str)
    def _on_error(self, error: QMediaPlayer.Error, error_string: str) -> None:
        """
        播放器错误回调。

        :param error: Qt 错误码
        :param error_string: 错误说明
        :return: None
        """
        if error != QMediaPlayer.Error.NoError:
            self._has_error = True
            self._error_message = error_string
            self._logger.error("背景音频播放器错误：%s", error_string)

    @Slot(QMediaPlayer.MediaStatus)
    def _on_media_status_changed(self, status: QMediaPlayer.MediaStatus) -> None:
        """
        媒体状态变更回调，用于通知服务层推进播放列表。

        :param status: Qt 媒体状态
        :return: None
        """
        if status != QMediaPlayer.MediaStatus.EndOfMedia or self._finished_notified:
            return
        self._finished_notified = True
        if self._finished_callback is not None:
            self._finished_callback()


def _is_remote_uri(uri: str) -> bool:
    """
    判断 URI 是否为远程资源。

    :param uri: 资源地址
    :return: True 表示远程资源
    """
    return uri.lower().startswith(("http://", "https://", "file://"))


def _url_for_uri(uri: str) -> QUrl:
    """
    将本地路径或 URL 转换为 QUrl。

    :param uri: 资源地址
    :return: QUrl 实例
    """
    if uri.lower().startswith(("http://", "https://", "file://")):
        return QUrl(uri)
    return QUrl.fromLocalFile(uri)
