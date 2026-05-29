#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
直播流低缓存预连接资源。
@Project : SCP-cv
@File : preheat_stream.py
@Author : Qintsg
@Date : 2026-05-28
'''
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class StreamPreheatHandle:
    """直播流低缓存后台预连接句柄。"""

    def __init__(self, source_id: int, uri: str) -> None:
        """
        初始化直播流预热句柄。
        :param source_id: 媒体源 ID
        :param uri: 直播流 URI
        :return: None
        """
        self.source_id = source_id
        self.uri = uri
        self._instance: object | None = None
        self._player: object | None = None
        self._media: object | None = None

    def start(self) -> None:
        """
        启动低缓存预连接，不绑定视频输出，避免占用前台渲染资源。
        :return: None
        """
        from scp_cv.player.adapters import srt_stream

        if srt_stream.vlc is None:
            logger.debug("libVLC 不可用，跳过直播源预热：source_id=%d", self.source_id)
            return
        instance_args = [
            "--no-video",
            "--no-audio",
            "--network-caching=100",
            "--live-caching=100",
            "--clock-jitter=0",
            "--clock-synchro=0",
            "--drop-late-frames",
            "--skip-frames",
        ]
        self._instance = srt_stream.vlc.Instance(instance_args)
        if self._instance is None:
            return
        self._player = self._instance.media_player_new()
        if self._player is None:
            return
        self._media = self._instance.media_new(self.uri)
        for option in _stream_media_options():
            self._media.add_option(option)
        self._player.set_media(self._media)
        self._player.play()
        logger.info("直播源已开始低缓存预连接：source_id=%d", self.source_id)

    def close(self) -> None:
        """
        关闭后台预连接资源。
        :return: None
        """
        for method_owner, method_name in (
            (self._player, "stop"),
            (self._player, "release"),
            (self._media, "release"),
            (self._instance, "release"),
        ):
            if method_owner is None:
                continue
            method = getattr(method_owner, method_name, None)
            if callable(method):
                try:
                    method()
                except Exception:
                    pass
        self._player = None
        self._media = None
        self._instance = None


def _stream_media_options() -> tuple[str, ...]:
    """
    返回直播预连接媒体级低缓存参数。
    :return: libVLC media options
    """
    return (
        ":network-caching=100",
        ":live-caching=100",
        ":clock-jitter=0",
        ":clock-synchro=0",
        ":drop-late-frames",
        ":skip-frames",
    )


__all__ = ["StreamPreheatHandle"]
