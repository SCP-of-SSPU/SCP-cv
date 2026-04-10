#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
播放器显示窗口：唯一窗口，支持全屏/无边框/置顶/跨屏拼接。
负责渲染 PPT 页面图片、叠加媒体播放、SRT 流显示。
@Project : SCP-cv
@File : window.py
@Author : Qintsg
@Date : 2026-04-10
'''
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

# ═══ 配置 libmpv DLL 搜索路径（必须在 import mpv 之前） ═══
_MPV_DLL_DIR = Path(__file__).resolve().parents[2] / 'tools' / 'third_party' / 'mpv'
if _MPV_DLL_DIR.is_dir():
    os.environ['PATH'] = str(_MPV_DLL_DIR) + os.pathsep + os.environ.get('PATH', '')
    # Python 3.8+ 需要显式添加 DLL 搜索目录
    os.add_dll_directory(str(_MPV_DLL_DIR))

import mpv  # noqa: E402  — 必须在 DLL 路径配置之后导入

from PySide6.QtCore import QRect, Qt, QUrl, Signal, Slot
from PySide6.QtGui import QPixmap
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QGraphicsOpacityEffect,
    QLabel,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)


class PlayerWindow(QWidget):
    """
    统一播放窗口。全程只创建一个实例。
    职责：
    - 全屏/无边框/置顶（正常模式）或可调窗口（DEBUG 模式）
    - 跨显示器定位（单屏或左右拼接）
    - PPT 页面图片底图渲染
    - 页面内嵌媒体叠加播放（视频/音频）
    - SRT 流画面（通过 QMediaPlayer + QVideoWidget）
    """

    # 信号：外部可监听窗口关闭
    window_closed = Signal()

    def __init__(
        self,
        debug_mode: bool = False,
        parent: Optional[QWidget] = None,
    ) -> None:
        """
        初始化播放器窗口。
        :param debug_mode: True 时不强制全屏/置顶，方便调试
        :param parent: 父 widget
        """
        super().__init__(parent)
        self._debug_mode = debug_mode

        # ═══ 窗口属性 ═══
        self.setWindowTitle("SCP-cv 播放器")
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)

        if not debug_mode:
            # 正常模式：无边框 + 置顶
            self.setWindowFlags(
                Qt.WindowType.FramelessWindowHint
                | Qt.WindowType.WindowStaysOnTopHint
            )
        else:
            # DEBUG 模式：普通窗口，可移动/缩放
            self.setWindowFlags(Qt.WindowType.Window)

        # ═══ 布局：使用 stacked layout 叠加图片层和媒体层 ═══
        self._stacked_layout = QStackedLayout()
        self._stacked_layout.setStackingMode(QStackedLayout.StackingMode.StackAll)

        # 底层：PPT 页面图片 / 黑屏背景
        self._background_label = QLabel()
        self._background_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._background_label.setStyleSheet("background-color: #000000;")
        self._background_label.setScaledContents(False)
        self._stacked_layout.addWidget(self._background_label)

        # 上层：视频叠加 widget（本地媒体/PPT 内嵌视频使用）
        self._video_widget = QVideoWidget()
        self._video_widget.setStyleSheet("background: transparent;")
        self._stacked_layout.addWidget(self._video_widget)

        # 顶层：mpv 流播放容器（SRT 直连低延迟播放）
        self._mpv_container = QWidget()
        self._mpv_container.setAttribute(
            Qt.WidgetAttribute.WA_NativeWindow, True,
        )
        self._mpv_container.setStyleSheet("background-color: #000000;")
        self._mpv_container.hide()
        self._stacked_layout.addWidget(self._mpv_container)

        # 主 layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addLayout(self._stacked_layout)

        # ═══ 媒体播放器 ═══
        self._media_player = QMediaPlayer(self)
        self._audio_output = QAudioOutput(self)
        self._media_player.setAudioOutput(self._audio_output)
        self._media_player.setVideoOutput(self._video_widget)

        # 当前状态追踪
        self._current_page_pixmap: Optional[QPixmap] = None

        # mpv 播放器实例（延迟初始化，确保窗口句柄有效）
        self._mpv_player: Optional[mpv.MPV] = None

        logger.info(
            "播放器窗口已初始化（debug=%s）",
            "开" if debug_mode else "关",
        )

    # ═══════════════════ 窗口定位 ═══════════════════

    def position_on_display(self, geometry: QRect) -> None:
        """
        将窗口定位到指定的屏幕矩形区域（单屏或拼接区域）。
        :param geometry: QRect，屏幕或拼接的绝对坐标矩形
        """
        self.setGeometry(geometry)
        if not self._debug_mode:
            self.showFullScreen()
        else:
            self.show()
        logger.info(
            "窗口定位到 (%d, %d) %dx%d",
            geometry.x(), geometry.y(),
            geometry.width(), geometry.height(),
        )

    def position_single_display(self, display_x: int, display_y: int,
                                display_width: int, display_height: int) -> None:
        """
        定位到单个显示器。
        :param display_x: 显示器左上角 x
        :param display_y: 显示器左上角 y
        :param display_width: 显示器宽度
        :param display_height: 显示器高度
        """
        rect = QRect(display_x, display_y, display_width, display_height)
        self.position_on_display(rect)

    def position_spliced_display(
        self,
        left_x: int, left_y: int, left_width: int, left_height: int,
        right_width: int, right_height: int,
    ) -> None:
        """
        定位到左右拼接区域。窗口覆盖两个显示器的并集矩形。
        :param left_x: 左显示器 x
        :param left_y: 左显示器 y
        :param left_width: 左显示器宽度
        :param left_height: 左显示器高度
        :param right_width: 右显示器宽度
        :param right_height: 右显示器高度
        """
        total_width = left_width + right_width
        total_height = max(left_height, right_height)
        rect = QRect(left_x, left_y, total_width, total_height)
        self.position_on_display(rect)

    # ═══════════════════ PPT 页面图片渲染 ═══════════════════

    @Slot(str)
    def show_page_image(self, image_path: str) -> None:
        """
        在底层显示 PPT 页面的 PNG 图片。
        :param image_path: 图片文件绝对路径
        """
        # 停止前一个媒体（如果有）
        self._stop_media()

        path = Path(image_path)
        if not path.exists():
            logger.warning("页面图片不存在：%s", image_path)
            self._show_black_screen()
            return

        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            logger.warning("无法加载页面图片：%s", image_path)
            self._show_black_screen()
            return

        self._current_page_pixmap = pixmap
        self._render_current_pixmap()

        # 确保背景层可见，视频层透明
        self._stacked_layout.setCurrentWidget(self._background_label)
        self._video_widget.hide()
        self._background_label.show()

        logger.info("显示页面图片：%s", path.name)

    def _render_current_pixmap(self) -> None:
        """按窗口尺寸缩放并居中显示当前 pixmap。"""
        if self._current_page_pixmap is None:
            return
        scaled_pixmap = self._current_page_pixmap.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._background_label.setPixmap(scaled_pixmap)

    def _show_black_screen(self) -> None:
        """清空底层显示为纯黑背景。"""
        self._background_label.clear()
        self._current_page_pixmap = None

    # ═══════════════════ 媒体播放（视频/音频叠加） ═══════════════════

    @Slot(str)
    def play_media(self, media_path: str) -> None:
        """
        播放指定媒体文件（叠加在 PPT 页面图片上层）。
        :param media_path: 媒体文件绝对路径
        """
        path = Path(media_path)
        if not path.exists():
            logger.warning("媒体文件不存在：%s", media_path)
            return

        self._media_player.setSource(QUrl.fromLocalFile(str(path)))
        self._video_widget.show()
        self._media_player.play()
        logger.info("开始播放媒体：%s", path.name)

    @Slot()
    def pause_media(self) -> None:
        """暂停当前媒体播放。"""
        if self._media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self._media_player.pause()
            logger.info("媒体已暂停")

    @Slot()
    def resume_media(self) -> None:
        """恢复当前媒体播放。"""
        if self._media_player.playbackState() == QMediaPlayer.PlaybackState.PausedState:
            self._media_player.play()
            logger.info("媒体已恢复")

    @Slot()
    def _stop_media(self) -> None:
        """停止当前媒体播放并隐藏视频层。"""
        self._media_player.stop()
        self._media_player.setSource(QUrl())
        self._video_widget.hide()

    # ═══════════════════ SRT 流播放（mpv 低延迟） ═══════════════════

    def _ensure_mpv_player(self) -> mpv.MPV:
        """
        确保 mpv 播放器实例存在并返回。
        延迟初始化以保证原生窗口句柄已分配。
        :return: mpv.MPV 实例
        """
        if self._mpv_player is not None:
            return self._mpv_player

        window_id = str(int(self._mpv_container.winId()))
        self._mpv_player = mpv.MPV(
            wid=window_id,
            vo='gpu',
            # 低延迟 profile：禁用缓冲、插值，最小化延迟
            profile='low-latency',
            untimed=True,
            cache='no',
            # FFmpeg demuxer 低延迟参数
            demuxer_lavf_o='fflags=+nobuffer+fastseek',
            log_handler=self._on_mpv_log,
            loglevel='warn',
        )
        logger.info("mpv 播放器已初始化（wid=%s）", window_id)
        return self._mpv_player

    def _on_mpv_log(self, loglevel: str, component: str, message: str) -> None:
        """
        mpv 日志回调，转发到 Python logging。
        :param loglevel: mpv 日志级别（fatal/error/warn/info/v/debug/trace）
        :param component: mpv 组件名
        :param message: 日志消息
        """
        _MPV_LEVEL_MAP = {
            'fatal': logging.CRITICAL,
            'error': logging.ERROR,
            'warn': logging.WARNING,
            'info': logging.INFO,
            'v': logging.DEBUG,
            'debug': logging.DEBUG,
            'trace': logging.DEBUG,
        }
        py_level = _MPV_LEVEL_MAP.get(loglevel, logging.INFO)
        logger.log(py_level, "[mpv/%s] %s", component, message.strip())

    @Slot(str)
    def play_srt_stream(self, stream_url: str) -> None:
        """
        使用 mpv 低延迟播放 SRT 流。
        跳过 QMediaPlayer 的不可控缓冲层，直接 SRT 读取，
        典型延迟从 2-5s 降低到 200-500ms。
        :param stream_url: SRT 流地址（如 srt://host:port?streamid=read:xxx）
        """
        # 停止本地媒体（若有）
        self._stop_media()
        self._show_black_screen()

        # 切换到 mpv 容器
        self._background_label.hide()
        self._video_widget.hide()
        self._mpv_container.show()
        self._stacked_layout.setCurrentWidget(self._mpv_container)

        player = self._ensure_mpv_player()
        player.play(stream_url)
        logger.info("开始播放 SRT 流（mpv 低延迟）：%s", stream_url)

    def _stop_mpv(self) -> None:
        """停止 mpv 流播放并隐藏容器。"""
        if self._mpv_player is not None:
            try:
                self._mpv_player.command('stop')
            except Exception as mpv_stop_error:
                logger.warning("mpv stop 异常：%s", mpv_stop_error)
        self._mpv_container.hide()

    @Slot()
    def stop_stream(self) -> None:
        """停止 SRT 流播放。"""
        self._stop_mpv()
        self._background_label.show()
        self._show_black_screen()
        logger.info("SRT 流已停止")

    # ═══════════════════ 全局控制 ═══════════════════

    @Slot()
    def stop_all(self) -> None:
        """停止所有内容（本地媒体 + mpv 流）并显示黑屏。"""
        self._stop_media()
        self._stop_mpv()
        self._show_black_screen()
        self._background_label.show()
        logger.info("播放器已全部停止")

    @Slot()
    def hide_window(self) -> None:
        """隐藏窗口但不销毁。"""
        self.hide()

    # ═══════════════════ 事件处理 ═══════════════════

    def resizeEvent(self, event: object) -> None:
        """窗口尺寸变化时重新缩放底层图片。"""
        super().resizeEvent(event)
        self._render_current_pixmap()

    def closeEvent(self, event: object) -> None:
        """窗口关闭时停止所有媒体并释放 mpv 资源。"""
        self.stop_all()
        # 销毁 mpv 实例，释放 GPU 资源
        if self._mpv_player is not None:
            try:
                self._mpv_player.terminate()
            except Exception as mpv_term_error:
                logger.warning("mpv terminate 异常：%s", mpv_term_error)
            self._mpv_player = None
        self.window_closed.emit()
        super().closeEvent(event)

    def keyPressEvent(self, event: object) -> None:
        """按 Escape 退出全屏或关闭窗口。"""
        from PySide6.QtCore import Qt as QtKey
        if hasattr(event, 'key') and event.key() == QtKey.Key.Key_Escape:
            if self._debug_mode:
                self.close()
            else:
                # 正常模式下 Esc 不关闭，仅日志记录
                logger.info("正常模式下按下 Escape，忽略")
        else:
            super().keyPressEvent(event)
