#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
播放器统一预热池，按媒体类型分发预热、认领和释放逻辑。
@Project : SCP-cv
@File : preheat_pool.py
@Author : Qintsg
@Date : 2026-05-28
'''
from __future__ import annotations

import logging
import time
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QPixmap
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer

from scp_cv.apps.playback.models import SourceType
from scp_cv.player.preheat_ppt import PptApplicationPreheater
from scp_cv.player.preheat_stream import StreamPreheatHandle
from scp_cv.player.preheat_types import PreheatedAudioSource, PreheatedPptApplication, PreheatedStreamSource, PreheatedVideoSource
from scp_cv.player.web_preheat import WebPreheatPool
from scp_cv.ppt_backend import PPT_BACKEND_LIBREOFFICE, PPT_BACKEND_POWERPOINT, PPT_BACKEND_WPS

logger = logging.getLogger(__name__)
_LIBREOFFICE_BRIDGE_TTL_SECONDS = 60.0


class PlayerPreheatPool:
    """播放器统一预热池。"""

    def __init__(self) -> None:
        """
        初始化各类型预热容器。
        :return: None
        """
        self.web_pool = WebPreheatPool()
        self._images: dict[int, tuple[str, QPixmap]] = {}
        self._videos: dict[int, PreheatedVideoSource] = {}
        self._audios: dict[int, PreheatedAudioSource] = {}
        self._streams: dict[int, StreamPreheatHandle] = {}
        self._ppt_apps = PptApplicationPreheater()
        self._libreoffice_bridge: object | None = None
        self._libreoffice_bridge_ready_at = 0.0
        self._libreoffice_bridge_source_id = 0
        self._libreoffice_bridge_uri = ""

    def preheat_source(
        self,
        source_id: int,
        source_type: str,
        uri: str,
        ppt_backend: str = "",
        force: bool = False,
    ) -> None:
        """
        按媒体类型预热指定源。
        :param source_id: 媒体源 ID
        :param source_type: 媒体源类型
        :param uri: 媒体 URI
        :param ppt_backend: PPT 后端
        :param force: 是否强制重新预热
        :return: None
        """
        if source_id <= 0 or not uri:
            return
        try:
            if source_type == SourceType.WEB:
                self.web_pool.preheat_source(source_id, uri, force=force)
            elif source_type == SourceType.IMAGE:
                self._preheat_image(source_id, uri, force)
            elif source_type == SourceType.VIDEO:
                self._preheat_video(source_id, uri, force)
            elif source_type == SourceType.AUDIO:
                self._preheat_audio(source_id, uri, force)
            elif str(source_type).endswith("_stream"):
                self._preheat_stream(source_id, uri, force)
            elif source_type == SourceType.PPT:
                self.preheat_ppt_backend(ppt_backend, source_id, uri)
        except Exception as preheat_error:
            logger.warning(
                "媒体源预热失败：source_id=%d, type=%s, error=%s",
                source_id,
                source_type,
                preheat_error,
            )

    def before_open(self, source_id: int, source_type: str) -> None:
        """
        前台打开前释放会与前台竞争的后台预热资源。
        :param source_id: 媒体源 ID
        :param source_type: 媒体源类型
        :return: None
        """
        if source_type == SourceType.AUDIO:
            return

    def take_image(self, source_id: int, uri: str) -> QPixmap | None:
        """
        取出已预热图片。
        :param source_id: 媒体源 ID
        :param uri: 图片路径
        :return: QPixmap 或 None
        """
        item = self._images.pop(source_id, None)
        if item is None:
            return None
        cached_uri, pixmap = item
        if cached_uri != uri or pixmap.isNull():
            return None
        return pixmap

    def take_video(self, source_id: int, uri: str) -> PreheatedVideoSource | None:
        """
        取出已预热视频播放器。
        :param source_id: 媒体源 ID
        :param uri: 视频路径
        :return: 已预热视频或 None
        """
        item = self._videos.pop(source_id, None)
        if item is None:
            return None
        if item.uri != uri:
            self._dispose_video(item)
            return None
        return item

    def take_audio(self, source_id: int, uri: str) -> PreheatedAudioSource | None:
        """
        取出已预热背景音频播放器。
        :param source_id: 媒体源 ID
        :param uri: 音频路径
        :return: 已预热音频或 None
        """
        item = self._audios.pop(source_id, None)
        if item is None:
            return None
        if item.uri != uri:
            self._dispose_audio(item)
            return None
        return item

    def take_stream(self, source_id: int, uri: str) -> PreheatedStreamSource | None:
        """
        认领已预热直播连接。
        :param source_id: 媒体源 ID
        :param uri: 直播 URI
        :return: 可复用直播资源或 None
        """
        handle = self._streams.pop(source_id, None)
        if handle is None:
            return None
        if handle.is_stale() or not handle.matches(source_id, uri):
            handle.close()
            return None
        claimed = handle.claim()
        if claimed is None:
            handle.close()
            return None
        return claimed

    def preheat_ppt_backend(self, backend: str, source_id: int = 0, uri: str = "") -> None:
        """
        预热指定 PPT 后端应用。
        :param backend: PPT 后端
        :param source_id: 可选媒体源 ID，用于文件级预热
        :param uri: 可选 PPT 文件路径，用于文件级预热
        :return: None
        """
        if backend == PPT_BACKEND_LIBREOFFICE:
            self._preheat_libreoffice_bridge(source_id, uri)
        elif backend in {PPT_BACKEND_POWERPOINT, PPT_BACKEND_WPS}:
            if source_id > 0 and uri:
                self._ppt_apps.preheat_source(backend, source_id, uri)
            else:
                self._ppt_apps.preheat(backend)

    def take_ppt_application(self, backend: str, source_id: int = 0, uri: str = "") -> PreheatedPptApplication | None:
        """
        取出 PowerPoint/WPS 预热应用。
        :param backend: PPT 后端
        :param source_id: 可选媒体源 ID，用于取文件级预热项
        :param uri: 可选 PPT 文件路径，用于取文件级预热项
        :return: 预热应用或 None
        """
        return self._ppt_apps.take(backend, source_id, uri)

    def return_ppt_application(self, item: PreheatedPptApplication) -> None:
        """
        归还 PowerPoint/WPS 应用到预热池。
        :param item: 预热应用
        :return: None
        """
        self._ppt_apps.return_item(item)

    def take_libreoffice_bridge(self, source_id: int = 0, uri: str = "") -> object | None:
        """
        取出预热 LibreOffice bridge。
        :param source_id: 可选媒体源 ID，用于取文件级预热项
        :param uri: 可选 PPT 文件路径，用于取文件级预热项
        :return: LibreOfficeBridgeClient 或 None
        """
        bridge = self._libreoffice_bridge
        bridge_source_id = int(getattr(self, "_libreoffice_bridge_source_id", 0) or 0)
        bridge_uri = str(getattr(self, "_libreoffice_bridge_uri", "") or "")
        if bridge is not None and self._libreoffice_bridge_is_stale():
            self._close_bridge(bridge)
            self._libreoffice_bridge = None
            self._libreoffice_bridge_ready_at = 0.0
            self._libreoffice_bridge_source_id = 0
            self._libreoffice_bridge_uri = ""
            logger.info("LibreOffice bridge 预热已过期，丢弃后改为前台冷启动")
            return None
        if bridge is not None and source_id > 0 and bridge_source_id > 0:
            if bridge_source_id != source_id or bridge_uri != uri:
                self._close_bridge(bridge)
                self._libreoffice_bridge = None
                self._libreoffice_bridge_ready_at = 0.0
                self._libreoffice_bridge_source_id = 0
                self._libreoffice_bridge_uri = ""
                return None
        self._libreoffice_bridge = None
        self._libreoffice_bridge_ready_at = 0.0
        self._libreoffice_bridge_source_id = 0
        self._libreoffice_bridge_uri = ""
        return bridge

    def return_libreoffice_bridge(self, bridge: object) -> None:
        """
        归还 LibreOffice bridge 到预热池。
        :param bridge: LibreOfficeBridgeClient
        :return: None
        """
        if self._libreoffice_bridge is not None and self._libreoffice_bridge is not bridge:
            self._close_bridge(self._libreoffice_bridge)
        self._libreoffice_bridge = bridge
        self._libreoffice_bridge_ready_at = time.monotonic()
        self._libreoffice_bridge_source_id = 0
        self._libreoffice_bridge_uri = ""

    def stop_stream_preheat(self, source_id: int) -> None:
        """
        停止指定直播源后台预连接。
        :param source_id: 媒体源 ID
        :return: None
        """
        handle = self._streams.pop(source_id, None)
        if handle is not None:
            handle.close()

    def close_all(self) -> None:
        """
        关闭全部预热资源。
        :return: None
        """
        self.web_pool.close_all()
        self._images.clear()
        for video in list(self._videos.values()):
            self._dispose_video(video)
        self._videos.clear()
        for audio in list(self._audios.values()):
            self._dispose_audio(audio)
        self._audios.clear()
        for stream in list(self._streams.values()):
            stream.close()
        self._streams.clear()
        self._ppt_apps.close_all()
        if self._libreoffice_bridge is not None:
            self._close_bridge(self._libreoffice_bridge)
            self._libreoffice_bridge = None
            self._libreoffice_bridge_ready_at = 0.0
            self._libreoffice_bridge_source_id = 0
            self._libreoffice_bridge_uri = ""

    def _preheat_image(self, source_id: int, uri: str, force: bool) -> None:
        """
        预加载图片到内存。
        :param source_id: 媒体源 ID
        :param uri: 图片路径
        :param force: 是否强制重载
        :return: None
        """
        if not force and source_id in self._images and self._images[source_id][0] == uri:
            return
        if not Path(uri).is_file():
            return
        pixmap = QPixmap(uri)
        if pixmap.isNull():
            return
        self._images[source_id] = (uri, pixmap)
        logger.info("图片源已预热到内存：source_id=%d", source_id)

    def _preheat_video(self, source_id: int, uri: str, force: bool) -> None:
        """
        创建后台 QMediaPlayer 并设置视频源。
        :param source_id: 媒体源 ID
        :param uri: 视频路径
        :param force: 是否强制重载
        :return: None
        """
        if not force and source_id in self._videos and self._videos[source_id].uri == uri:
            return
        old_item = self._videos.pop(source_id, None)
        if old_item is not None:
            self._dispose_video(old_item)
        if not Path(uri).is_file():
            return
        audio_output = QAudioOutput()
        player = QMediaPlayer()
        player.setAudioOutput(audio_output)
        player.setSource(QUrl.fromLocalFile(uri))
        self._videos[source_id] = PreheatedVideoSource(source_id, uri, player, audio_output)
        logger.info("视频源已完成初步加载：source_id=%d", source_id)

    def _preheat_audio(self, source_id: int, uri: str, force: bool) -> None:
        """
        创建后台 QMediaPlayer 并设置背景音频源。
        :param source_id: 媒体源 ID
        :param uri: 音频路径
        :param force: 是否强制重载
        :return: None
        """
        if not force and source_id in self._audios and self._audios[source_id].uri == uri:
            return
        old_item = self._audios.pop(source_id, None)
        if old_item is not None:
            self._dispose_audio(old_item)
        if not Path(uri).is_file():
            return
        audio_output = QAudioOutput()
        audio_output.setMuted(True)
        player = QMediaPlayer()
        player.setAudioOutput(audio_output)
        player.setSource(QUrl.fromLocalFile(uri))
        self._audios[source_id] = PreheatedAudioSource(source_id, uri, player, audio_output)
        logger.info("背景音频源已完成初步加载：source_id=%d", source_id)

    def _preheat_stream(self, source_id: int, uri: str, force: bool) -> None:
        """
        启动直播源低缓存预连接。
        :param source_id: 媒体源 ID
        :param uri: 直播流 URI
        :param force: 是否强制重连
        :return: None
        """
        existing = self._streams.get(source_id)
        if not force and existing is not None and existing.matches(source_id, uri) and not existing.is_stale():
            return
        self.stop_stream_preheat(source_id)
        handle = StreamPreheatHandle(source_id, uri)
        handle.start()
        self._streams[source_id] = handle

    def _preheat_libreoffice_bridge(self, source_id: int = 0, uri: str = "") -> None:
        """
        预启动 LibreOffice bridge。
        :param source_id: 可选媒体源 ID，用于文件级预热
        :param uri: 可选 PPT 文件路径，用于文件级预热
        :return: None
        """
        if self._libreoffice_bridge is not None and (
            source_id <= 0
            or (self._libreoffice_bridge_source_id == source_id and self._libreoffice_bridge_uri == uri)
        ):
            return
        from scp_cv.player.adapters.ppt_libreoffice_bridge import LibreOfficeBridgeClient

        if self._libreoffice_bridge is not None:
            self._close_bridge(self._libreoffice_bridge)
        bridge = LibreOfficeBridgeClient(logger)
        try:
            if source_id > 0 and uri:
                bridge.open(uri, autoplay=False)
            else:
                bridge.preheat()
        except Exception as preheat_error:
            bridge.close()
            logger.warning("LibreOffice 文件级预热失败：source_id=%d, error=%s", source_id, preheat_error)
            return
        self._libreoffice_bridge = bridge
        self._libreoffice_bridge_ready_at = time.monotonic()
        self._libreoffice_bridge_source_id = source_id if uri else 0
        self._libreoffice_bridge_uri = uri if source_id > 0 else ""
        logger.info("LibreOffice bridge 已预热：source_id=%d", source_id)

    def _libreoffice_bridge_is_stale(self) -> bool:
        """
        判断预热 LibreOffice bridge 是否已陈旧。
        :return: True 表示应丢弃并由前台冷启动
        """
        if self._libreoffice_bridge_ready_at <= 0:
            return False
        return time.monotonic() - self._libreoffice_bridge_ready_at > _LIBREOFFICE_BRIDGE_TTL_SECONDS

    @staticmethod
    def _dispose_video(video: PreheatedVideoSource) -> None:
        """
        释放预热视频资源。
        :param video: 已预热视频
        :return: None
        """
        video.player.stop()
        video.player.setVideoOutput(None)
        video.player.setAudioOutput(None)
        video.player.deleteLater()
        video.audio_output.deleteLater()

    @staticmethod
    def _dispose_audio(audio: PreheatedAudioSource) -> None:
        """
        释放预热音频资源。
        :param audio: 已预热音频
        :return: None
        """
        audio.player.stop()
        audio.player.setAudioOutput(None)
        audio.player.deleteLater()
        audio.audio_output.deleteLater()

    @staticmethod
    def _close_bridge(bridge: object) -> None:
        """
        关闭 LibreOffice bridge。
        :param bridge: bridge 客户端
        :return: None
        """
        close = getattr(bridge, "close", None)
        if callable(close):
            close()


__all__ = ["PlayerPreheatPool"]
