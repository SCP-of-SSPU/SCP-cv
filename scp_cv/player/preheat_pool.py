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
from scp_cv.player.preheat_types import PreheatedPptApplication, PreheatedVideoSource
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
        self._streams: dict[int, StreamPreheatHandle] = {}
        self._ppt_apps = PptApplicationPreheater()
        self._libreoffice_bridge: object | None = None
        self._libreoffice_bridge_ready_at = 0.0

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
            elif source_type in {SourceType.VIDEO, SourceType.AUDIO}:
                self._preheat_video(source_id, uri, force)
            elif str(source_type).endswith("_stream"):
                self._preheat_stream(source_id, uri, force)
            elif source_type == SourceType.PPT:
                self.preheat_ppt_backend(ppt_backend)
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
        if str(source_type).endswith("_stream"):
            self.stop_stream_preheat(source_id)

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

    def preheat_ppt_backend(self, backend: str) -> None:
        """
        预热指定 PPT 后端应用。
        :param backend: PPT 后端
        :return: None
        """
        if backend == PPT_BACKEND_LIBREOFFICE:
            self._preheat_libreoffice_bridge()
        elif backend in {PPT_BACKEND_POWERPOINT, PPT_BACKEND_WPS}:
            self._ppt_apps.preheat(backend)

    def take_ppt_application(self, backend: str) -> PreheatedPptApplication | None:
        """
        取出 PowerPoint/WPS 预热应用。
        :param backend: PPT 后端
        :return: 预热应用或 None
        """
        return self._ppt_apps.take(backend)

    def return_ppt_application(self, item: PreheatedPptApplication) -> None:
        """
        归还 PowerPoint/WPS 应用到预热池。
        :param item: 预热应用
        :return: None
        """
        self._ppt_apps.return_item(item)

    def take_libreoffice_bridge(self) -> object | None:
        """
        取出预热 LibreOffice bridge。
        :return: LibreOfficeBridgeClient 或 None
        """
        bridge = self._libreoffice_bridge
        if bridge is not None and self._libreoffice_bridge_is_stale():
            self._close_bridge(bridge)
            self._libreoffice_bridge = None
            self._libreoffice_bridge_ready_at = 0.0
            logger.info("LibreOffice bridge 预热已过期，丢弃后改为前台冷启动")
            return None
        self._libreoffice_bridge = None
        self._libreoffice_bridge_ready_at = 0.0
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
        for stream in list(self._streams.values()):
            stream.close()
        self._streams.clear()
        self._ppt_apps.close_all()
        if self._libreoffice_bridge is not None:
            self._close_bridge(self._libreoffice_bridge)
            self._libreoffice_bridge = None
            self._libreoffice_bridge_ready_at = 0.0

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

    def _preheat_stream(self, source_id: int, uri: str, force: bool) -> None:
        """
        启动直播源低缓存预连接。
        :param source_id: 媒体源 ID
        :param uri: 直播流 URI
        :param force: 是否强制重连
        :return: None
        """
        if not force and source_id in self._streams:
            return
        self.stop_stream_preheat(source_id)
        handle = StreamPreheatHandle(source_id, uri)
        handle.start()
        self._streams[source_id] = handle

    def _preheat_libreoffice_bridge(self) -> None:
        """
        预启动 LibreOffice bridge。
        :return: None
        """
        if self._libreoffice_bridge is not None:
            return
        from scp_cv.player.adapters.ppt_libreoffice_bridge import LibreOfficeBridgeClient

        bridge = LibreOfficeBridgeClient(logger)
        bridge.preheat()
        self._libreoffice_bridge = bridge
        self._libreoffice_bridge_ready_at = time.monotonic()
        logger.info("LibreOffice bridge 已预热")

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
