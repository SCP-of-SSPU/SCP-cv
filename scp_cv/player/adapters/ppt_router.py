#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PPT 适配器路由层，按本次打开指令显式选择 PPT 放映后端。
@Project : SCP-cv
@File : ppt_router.py
@Author : Qintsg
@Date : 2026-05-26
'''
from __future__ import annotations

from typing import Optional

from scp_cv.player.adapters.base import AdapterState, SourceAdapter
from scp_cv.ppt_backend import (
    DEFAULT_PPT_BACKEND,
    PPT_BACKEND_LIBREOFFICE,
    PPT_BACKEND_POWERPOINT,
    PPT_BACKEND_WPS,
    normalize_ppt_backend,
)


class PptSourceAdapter(SourceAdapter):
    """
    PPT 后端路由适配器。

    后端必须由媒体源默认值或本次打开请求显式提供；不会进行 auto 兜底。
    """

    def __init__(self, ppt_backend: str = DEFAULT_PPT_BACKEND) -> None:
        """
        初始化 PPT 路由适配器。
        :param ppt_backend: 本次放映使用的 PPT 后端
        :return: None
        """
        super().__init__(adapter_name="ppt-router")
        self._delegate: Optional[SourceAdapter] = None
        self._active_backend = ""
        self._configured_backend = normalize_ppt_backend(ppt_backend)

    @property
    def active_backend(self) -> str:
        """
        当前实际使用的 PPT 后端。
        :return: libreoffice、powerpoint、wps 或空字符串
        """
        return self._active_backend

    @property
    def configured_backend(self) -> str:
        """
        当前指定的 PPT 后端。
        :return: libreoffice、powerpoint 或 wps
        """
        return self._configured_backend

    def open(self, uri: str, window_handle: int, autoplay: bool = True) -> None:
        """
        按配置打开 PPT 后端。
        :param uri: PPT 文件绝对路径
        :param window_handle: PySide 播放器容器 HWND
        :param autoplay: 是否自动开始播放
        :return: None
        """
        self._open_with_backend(self._configured_backend, uri, window_handle, autoplay)

    def close(self) -> None:
        """
        关闭当前 PPT 后端。
        :return: None
        """
        self._close_delegate()
        self._mark_closed()

    def play(self) -> None:
        """
        开始或恢复播放。
        :return: None
        """
        if self._delegate is not None:
            self._delegate.play()

    def pause(self) -> None:
        """
        暂停播放。
        :return: None
        """
        if self._delegate is not None:
            self._delegate.pause()

    def stop(self) -> None:
        """
        停止播放。
        :return: None
        """
        if self._delegate is not None:
            self._delegate.stop()

    def next_item(self) -> None:
        """
        下一页或下一动画。
        :return: None
        """
        if self._delegate is not None:
            self._delegate.next_item()

    def prev_item(self) -> None:
        """
        上一页或上一动画。
        :return: None
        """
        if self._delegate is not None:
            self._delegate.prev_item()

    def goto_item(self, index: int) -> None:
        """
        跳转到指定页。
        :param index: 目标页码，1-based
        :return: None
        """
        if self._delegate is not None:
            self._delegate.goto_item(index)

    def seek(self, position_ms: int) -> None:
        """
        转发 seek 操作。
        :param position_ms: 目标位置毫秒数
        :return: None
        """
        if self._delegate is not None:
            self._delegate.seek(position_ms)

    def control_media(self, media_id: str, action: str, media_index: int = 0) -> None:
        """
        转发当前页媒体控制。
        :param media_id: 媒体对象标识
        :param action: 控制动作
        :param media_index: 当前页媒体序号
        :return: None
        """
        if self._delegate is not None:
            self._delegate.control_media(media_id, action, media_index)

    def set_volume(self, volume: int) -> None:
        """
        转发音量设置。
        :param volume: 音量 0-100
        :return: None
        """
        if self._delegate is not None:
            self._delegate.set_volume(volume)

    def set_mute(self, muted: bool) -> None:
        """
        转发静音设置。
        :param muted: 是否静音
        :return: None
        """
        if self._delegate is not None:
            self._delegate.set_mute(muted)

    def get_state(self) -> AdapterState:
        """
        获取当前后端状态。
        :return: AdapterState 状态快照
        """
        if self._delegate is None:
            return AdapterState(playback_state="idle")
        return self._delegate.get_state()

    def _open_with_backend(
        self,
        backend: str,
        uri: str,
        window_handle: int,
        autoplay: bool,
    ) -> None:
        """
        创建并打开指定 PPT 后端。
        :param backend: 后端名称
        :param uri: PPT 文件绝对路径
        :param window_handle: PySide 播放器容器 HWND
        :param autoplay: 是否自动开始播放
        :return: None
        """
        adapter = create_ppt_backend_adapter(backend)
        try:
            adapter.open(uri, window_handle, autoplay)
        except Exception:
            try:
                adapter.close()
            except Exception:
                pass
            raise
        self._delegate = adapter
        self._active_backend = backend
        self._mark_open()
        self._logger.info("PPT 后端已启用：%s", backend)

    def _close_delegate(self) -> None:
        """
        关闭并清空当前委托适配器。
        :return: None
        """
        if self._delegate is not None:
            try:
                self._delegate.close()
            finally:
                self._delegate = None
        self._active_backend = ""


def create_ppt_backend_adapter(backend: str) -> SourceAdapter:
    """
    创建指定 PPT 后端适配器。
    :param backend: 后端名称
    :return: PPT 后端适配器
    :raises ValueError: 后端名称不受支持时
    """
    if backend == PPT_BACKEND_LIBREOFFICE:
        from scp_cv.player.adapters.ppt_libreoffice import LibreOfficePptSourceAdapter

        return LibreOfficePptSourceAdapter()
    if backend == PPT_BACKEND_POWERPOINT:
        from scp_cv.player.adapters.ppt import PptSourceAdapter as PowerPointPptSourceAdapter

        return PowerPointPptSourceAdapter()
    if backend == PPT_BACKEND_WPS:
        from scp_cv.player.adapters.ppt_wps import WpsPptSourceAdapter

        return WpsPptSourceAdapter()
    raise ValueError(f"不支持的 PPT 后端：{backend}")


__all__ = [
    "PPT_BACKEND_LIBREOFFICE",
    "PPT_BACKEND_POWERPOINT",
    "PPT_BACKEND_WPS",
    "PptSourceAdapter",
    "create_ppt_backend_adapter",
]
