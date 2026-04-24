#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
验证 QMediaPlayer FFmpeg 后端是否支持直接播放 SRT 流。
运行方式：python tools/verify_srt_playback.py
需要先启动 MediaMTX 和 OBS 推流。
@Project : SCP-cv
@File : verify_srt_playback.py
@Author : Qintsg
@Date : 2026-04-17
'''
from __future__ import annotations

import os
import sys

# 强制使用 FFmpeg 后端
os.environ["QT_MEDIA_BACKEND"] = "ffmpeg"

from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import QApplication, QMainWindow

# SRT 拉流地址（MediaMTX 监听 8890 端口）
# 注意：read 模式的 streamid 语法
SRT_READ_URL = "srt://127.0.0.1:8890?streamid=read:test&latency=30000"
RTSP_URL = "rtsp://127.0.0.1:8554/test"


class TestWindow(QMainWindow):
    """验证 SRT 播放窗口"""

    def __init__(self, url: str) -> None:
        super().__init__()
        self.setWindowTitle(f"SRT/RTSP 播放验证 - {url}")
        self.resize(960, 540)

        self._video_widget = QVideoWidget(self)
        self.setCentralWidget(self._video_widget)

        self._audio = QAudioOutput()
        self._audio.setVolume(1.0)

        self._player = QMediaPlayer()
        self._player.setVideoOutput(self._video_widget)
        self._player.setAudioOutput(self._audio)
        self._player.errorOccurred.connect(self._on_error)
        self._player.mediaStatusChanged.connect(self._on_status)
        self._player.playbackStateChanged.connect(self._on_state)

        self._player.setSource(QUrl(url))
        self._player.play()
        print(f"[INFO] 正在尝试播放：{url}")

    def _on_error(
        self,
        error: QMediaPlayer.Error,
        message: str,
    ) -> None:
        print(f"[ERROR] {error}: {message}")

    def _on_status(self, status: QMediaPlayer.MediaStatus) -> None:
        print(f"[STATUS] {status}")

    def _on_state(self, state: QMediaPlayer.PlaybackState) -> None:
        print(f"[STATE] {state}")


def main() -> None:
    """验证入口：先尝试 SRT，失败则回退到 RTSP"""
    app = QApplication(sys.argv)

    # 通过命令行参数选择协议
    if "--rtsp" in sys.argv:
        url = RTSP_URL
        print("[INFO] 使用 RTSP 协议")
    else:
        url = SRT_READ_URL
        print("[INFO] 使用 SRT 协议（若失败请加 --rtsp 参数对比）")

    window = TestWindow(url)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
