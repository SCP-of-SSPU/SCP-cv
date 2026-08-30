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
import time

from django.conf import settings

from scp_cv.player.preheat_types import PreheatedStreamSource

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
        self._parking_widget: object | None = None
        self._ready_at = 0.0
        self._claimed = False

    def start(self) -> None:
        """
        启动低缓存预连接，绑定到隐藏停车窗口等待前台认领。
        :return: None
        """
        from scp_cv.player.adapters import srt_stream

        if srt_stream.vlc is None:
            logger.debug("libVLC 不可用，跳过直播源预热：source_id=%d", self.source_id)
            return
        instance_args = _stream_instance_args()
        self._instance = srt_stream.vlc.Instance(instance_args)
        if self._instance is None:
            return
        self._player = self._instance.media_player_new()
        if self._player is None:
            return
        self._bind_parking_window()
        self._media = self._instance.media_new(self.uri)
        for option in _stream_media_options():
            self._media.add_option(option)
        self._player.set_media(self._media)
        audio_set_mute = getattr(self._player, "audio_set_mute", None)
        if callable(audio_set_mute):
            audio_set_mute(True)
        self._player.play()
        self._ready_at = time.monotonic()
        logger.info("直播源已开始低缓存预连接：source_id=%d", self.source_id)

    @property
    def is_ready(self) -> bool:
        """
        判断预热资源是否已建立。
        :return: True 表示可被前台认领
        """
        return self._instance is not None and self._player is not None and self._media is not None

    def matches(self, source_id: int, uri: str) -> bool:
        """
        判断预热资源是否匹配请求的直播源。
        :param source_id: 媒体源 ID
        :param uri: 直播 URI
        :return: True 表示可认领
        """
        return self.source_id == source_id and self.uri == uri

    def is_stale(self) -> bool:
        """
        判断预热资源是否已过期。
        :return: True 表示应丢弃
        """
        ttl_seconds = float(getattr(settings, "STREAM_PREHEAT_TTL_SECONDS", 60.0))
        return self._ready_at > 0 and time.monotonic() - self._ready_at > ttl_seconds

    def refresh(self) -> bool:
        """在 TTL 到期前续热；连接失效时后台重建。"""
        if not self.is_ready:
            return False
        player = self._player
        try:
            state = player.get_state() if player is not None and hasattr(player, "get_state") else None
            if state is not None and str(state).lower().endswith("error"):
                raise RuntimeError("libVLC 预热连接已进入错误状态")
            self._ready_at = time.monotonic()
            return True
        except Exception as refresh_error:
            logger.info("直播预热连接失效，后台重建：source_id=%d, error=%s", self.source_id, refresh_error)
            self.close()
            self._claimed = False
            self.start()
            return self.is_ready

    def claim(self) -> PreheatedStreamSource | None:
        """
        将 libVLC 资源交给前台适配器。
        :return: 可认领直播资源；资源不可用时返回 None
        """
        if self._claimed or not self.is_ready:
            return None
        assert self._instance is not None
        assert self._player is not None
        assert self._media is not None
        self._claimed = True
        claimed = PreheatedStreamSource(
            source_id=self.source_id,
            uri=self.uri,
            instance=self._instance,
            player=self._player,
            media=self._media,
            ready_at=self._ready_at,
        )
        self._instance = None
        self._player = None
        self._media = None
        self._close_parking_widget()
        logger.info("直播源预热资源已被前台认领：source_id=%d", self.source_id)
        return claimed

    def close(self) -> None:
        """
        关闭后台预连接资源。
        :return: None
        """
        for resource_name, method_owner, method_name in (
            ("player", self._player, "stop"),
            ("player", self._player, "release"),
            ("media", self._media, "release"),
            ("instance", self._instance, "release"),
        ):
            if method_owner is None:
                continue
            method = getattr(method_owner, method_name, None)
            if callable(method):
                try:
                    method()
                except Exception as close_error:
                    logger.warning(
                        "直播预热资源释放步骤失败：source_id=%d resource=%s "
                        "stage=%s error=%s",
                        self.source_id,
                        resource_name,
                        method_name,
                        close_error,
                    )
        self._player = None
        self._media = None
        self._instance = None
        self._ready_at = 0.0
        self._close_parking_widget()

    def _bind_parking_window(self) -> None:
        """
        将预热播放器绑定到隐藏 QWidget，避免 libVLC 创建可见窗口。
        :return: None
        """
        if self._player is None:
            return
        set_hwnd = getattr(self._player, "set_hwnd", None)
        if not callable(set_hwnd):
            return
        try:
            from PySide6.QtWidgets import QApplication, QWidget

            if QApplication.instance() is None:
                return
            parking_widget = QWidget()
            parking_widget.resize(1, 1)
            parking_widget.move(-32000, -32000)
            parking_widget.hide()
            set_hwnd(int(parking_widget.winId()))
            self._parking_widget = parking_widget
        except Exception as bind_error:
            logger.debug("直播预热停车窗口绑定失败：%s", bind_error)

    def _close_parking_widget(self) -> None:
        """
        关闭隐藏停车窗口。
        :return: None
        """
        widget = self._parking_widget
        self._parking_widget = None
        if widget is not None:
            try:
                widget.close()
                widget.deleteLater()
            except Exception:
                pass


def _stream_instance_args() -> tuple[str, ...]:
    """
    返回直播预热 libVLC 实例参数。
    :return: libVLC instance args
    """
    args = [
        "--no-video-title-show",
        "--no-snapshot-preview",
        f"--network-caching={int(getattr(settings, 'STREAM_PREHEAT_NETWORK_CACHING_MS', 100))}",
        f"--live-caching={int(getattr(settings, 'STREAM_PREHEAT_LIVE_CACHING_MS', 100))}",
        f"--clock-jitter={int(getattr(settings, 'STREAM_VLC_CLOCK_JITTER', 0))}",
        f"--clock-synchro={int(getattr(settings, 'STREAM_VLC_CLOCK_SYNCHRO', 0))}",
    ]
    if bool(getattr(settings, "STREAM_VLC_DROP_LATE_FRAMES", True)):
        args.append("--drop-late-frames")
    if bool(getattr(settings, "STREAM_VLC_SKIP_FRAMES", True)):
        args.append("--skip-frames")
    return tuple(args)


def _rtsp_transport_options() -> tuple[str, ...]:
    """
    根据配置生成 RTSP 传输方式参数。
    :return: libVLC media options
    """
    transport = str(getattr(settings, "MEDIAMTX_RTSP_READ_TRANSPORT", "tcp") or "").strip().lower()
    if transport == "tcp":
        return (":rtsp-tcp",)
    if transport == "udp":
        return (":rtsp-udp",)
    return ()


def _stream_media_options() -> tuple[str, ...]:
    """
    返回直播预连接媒体级低缓存参数。
    :return: libVLC media options
    """
    return (
        f":network-caching={int(getattr(settings, 'STREAM_PREHEAT_NETWORK_CACHING_MS', 100))}",
        f":live-caching={int(getattr(settings, 'STREAM_PREHEAT_LIVE_CACHING_MS', 100))}",
        f":clock-jitter={int(getattr(settings, 'STREAM_VLC_CLOCK_JITTER', 0))}",
        f":clock-synchro={int(getattr(settings, 'STREAM_VLC_CLOCK_SYNCHRO', 0))}",
        *([":drop-late-frames"] if bool(getattr(settings, "STREAM_VLC_DROP_LATE_FRAMES", True)) else []),
        *([":skip-frames"] if bool(getattr(settings, "STREAM_VLC_SKIP_FRAMES", True)) else []),
        *_rtsp_transport_options(),
    )


__all__ = ["StreamPreheatHandle"]
