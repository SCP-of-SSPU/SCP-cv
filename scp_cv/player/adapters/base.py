#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
媒体源适配器基类，定义所有适配器的统一接口。
所有具体适配器（PPT、视频、WebRTC 流）均继承此 ABC。
@Project : SCP-cv
@File : base.py
@Author : Qintsg
@Date : 2026-04-15
'''
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class AdapterState:
    """
    适配器统一状态快照，供 PlayerManager 上报 DB。
    适用于翻页型（PPT）和时间线型（视频/音频）两种模式。
    """

    # 播放状态（对应 PlaybackState 枚举值）
    playback_state: str = "idle"

    # ── 翻页型源状态（PPT / 图片集） ──
    current_slide: int = 0
    total_slides: int = 0

    # ── 时间线型源状态（视频 / 音频） ──
    position_ms: int = 0
    duration_ms: int = 0

    # ── 错误信息（异常时填入） ──
    error_message: str = ""


class SourceAdapter(ABC):
    """
    媒体源适配器抽象基类。

    每种可播放内容类型对应一个子类实现：
    - PptSourceAdapter：PowerPoint COM 放映
    - VideoSourceAdapter：QMediaPlayer 本地视频
    - WebRTCStreamAdapter / RtspStreamAdapter：RTSP 流播放

    生命周期：open → play/pause/stop → close
    适配器实例由 PlayerManager 创建和管理。
    """

    def __init__(self, adapter_name: str = "base") -> None:
        """
        初始化基类。
        :param adapter_name: 适配器标识名（用于日志）
        """
        self._adapter_name = adapter_name
        self._is_open = False
        self._logger = logging.getLogger(f"{__name__}.{adapter_name}")

    @property
    def adapter_name(self) -> str:
        """适配器标识名。"""
        return self._adapter_name

    @property
    def is_open(self) -> bool:
        """资源是否已打开。"""
        return self._is_open

    # ═══════════════════ 生命周期 ═══════════════════

    @abstractmethod
    def open(self, uri: str, window_handle: int, autoplay: bool = True) -> None:
        """
        打开媒体源并准备播放。
        :param uri: 资源地址（文件路径 / URL / 流标识符）
        :param window_handle: 渲染目标窗口的原生句柄
        :param autoplay: 是否打开后自动开始播放
        """

    @abstractmethod
    def close(self) -> None:
        """关闭源并释放所有资源。子类必须在最终调用 super().close()。"""

    # ═══════════════════ 播放控制 ═══════════════════

    @abstractmethod
    def play(self) -> None:
        """开始或恢复播放。"""

    @abstractmethod
    def pause(self) -> None:
        """暂停播放。"""

    @abstractmethod
    def stop(self) -> None:
        """停止播放（不释放资源，可重新 play）。"""

    # ═══════════════════ 导航控制 ═══════════════════

    def next_item(self) -> None:
        """
        下一项（翻页型源重写）。
        默认实现：不支持的源类型忽略操作。
        """
        self._logger.debug("适配器 %s 不支持 next_item", self._adapter_name)

    def prev_item(self) -> None:
        """
        上一项（翻页型源重写）。
        默认实现：不支持的源类型忽略操作。
        """
        self._logger.debug("适配器 %s 不支持 prev_item", self._adapter_name)

    def goto_item(self, index: int) -> None:
        """
        跳转到指定项（翻页型源重写，从 1 开始计数）。
        :param index: 目标页码（1-based）
        """
        self._logger.debug("适配器 %s 不支持 goto_item", self._adapter_name)

    def seek(self, position_ms: int) -> None:
        """
        跳转到指定时间位置（时间线型源重写）。
        :param position_ms: 目标位置（毫秒）
        """
        self._logger.debug("适配器 %s 不支持 seek", self._adapter_name)

    def set_loop(self, enabled: bool) -> None:
        """
        设置循环播放（时间线型源重写）。
        默认实现：不支持的源类型忽略操作。
        :param enabled: 是否启用循环播放
        """
        self._logger.debug("适配器 %s 不支持 set_loop", self._adapter_name)

    def set_volume(self, volume: int) -> None:
        """
        设置播放音量（带音频输出的源重写）。
        :param volume: 音量等级（0-100）
        """
        self._logger.debug("适配器 %s 不支持 set_volume", self._adapter_name)

    def set_mute(self, muted: bool) -> None:
        """
        设置静音状态（带音频输出的源重写）。
        :param muted: 是否静音
        """
        self._logger.debug("适配器 %s 不支持 set_mute", self._adapter_name)

    # ═══════════════════ 状态获取 ═══════════════════

    @abstractmethod
    def get_state(self) -> AdapterState:
        """
        获取当前播放状态快照。
        :return: AdapterState 实例
        """

    # ═══════════════════ 基类辅助 ═══════════════════

    def _mark_open(self) -> None:
        """标记适配器为已打开状态。子类在 open() 成功后调用。"""
        self._is_open = True

    def _mark_closed(self) -> None:
        """标记适配器为已关闭状态。子类在 close() 中调用。"""
        self._is_open = False
