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
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QPixmap
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer

from scp_cv.apps.playback.models import SourceType
from scp_cv.player.preheat_ppt import PptApplicationPreheater
from scp_cv.player.preheat_stream import StreamPreheatHandle
from scp_cv.player.preheat_types import PreheatedAudioSource, PreheatedPptApplication, PreheatedStreamSource, PreheatedVideoSource
from scp_cv.player.web_preheat import WebPreheatPool

logger = logging.getLogger(__name__)


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
        # PPT COM 工作线程；注入后 PPT 预热在该线程后台执行，不阻塞主线程。
        self._ppt_com_worker: object | None = None

    def attach_ppt_com_worker(self, com_worker: object | None) -> None:
        """
        注入共享 PPT COM 工作线程。
        :param com_worker: PptComWorker 实例；None 表示内联执行
        :return: None
        """
        self._ppt_com_worker = com_worker

    def preheat_source(
        self,
        source_id: int,
        source_type: str,
        uri: str,
        force: bool = False,
    ) -> None:
        """
        按媒体类型预热指定源。
        :param source_id: 媒体源 ID
        :param source_type: 媒体源类型
        :param uri: 媒体 URI
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
                self.preheat_ppt_source(source_id, uri)
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

    def preheat_ppt_source(self, source_id: int = 0, uri: str = "") -> None:
        """
        预热 PowerPoint 应用或指定 PPT 文件。
        注入 COM 工作线程时在后台执行，避免冷启动阻塞主线程。
        :param source_id: 可选媒体源 ID，用于文件级预热
        :param uri: 可选 PPT 文件路径，用于文件级预热
        :return: None
        """
        if source_id > 0 and uri:
            preheat_job = lambda: self._ppt_apps.preheat_source(source_id, uri)  # noqa: E731
            description = f"预热 PPT 文件 source_id={source_id}"
        else:
            preheat_job = self._ppt_apps.preheat
            description = "预热 PowerPoint 应用"
        # getattr 兜底：测试可能绕过 __init__ 构造预热池实例
        worker = getattr(self, "_ppt_com_worker", None)
        if worker is None or getattr(worker, "is_current_thread", False):
            preheat_job()
            return
        # 预热走低优先级：前台打开/关闭等指令可插队，不被预热队列挡住
        worker.submit(description, preheat_job, low_priority=True)

    def take_ppt_application(self, source_id: int = 0, uri: str = "") -> PreheatedPptApplication | None:
        """
        取出 PowerPoint 预热应用。
        :param source_id: 可选媒体源 ID，用于取文件级预热项
        :param uri: 可选 PPT 文件路径，用于取文件级预热项
        :return: 预热应用或 None
        """
        return self._ppt_apps.take(source_id, uri)

    def return_ppt_application(self, item: PreheatedPptApplication) -> None:
        """
        归还 PowerPoint 应用到预热池。
        :param item: 预热应用
        :return: None
        """
        self._ppt_apps.return_item(item)

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
        self._close_ppt_preheats()

    def _close_ppt_preheats(self) -> None:
        """
        关闭 PPT 预热资源；COM 对象属于工作线程时同步等待其在该线程释放。
        :return: None
        """
        worker = getattr(self, "_ppt_com_worker", None)
        if worker is None or getattr(worker, "is_current_thread", False):
            self._ppt_apps.close_all()
            return
        # 先丢弃排队中的预热任务，避免池关闭后旧预热再拉起新 PowerPoint
        discard_low_priority = getattr(worker, "discard_low_priority_jobs", None)
        if callable(discard_low_priority):
            discard_low_priority()
        try:
            worker.submit_and_wait(
                "关闭 PPT 预热资源",
                self._ppt_apps.close_all,
                timeout_seconds=10.0,
            )
        except Exception as close_error:
            logger.warning("关闭 PPT 预热资源失败：%s", close_error)

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

__all__ = ["PlayerPreheatPool"]
