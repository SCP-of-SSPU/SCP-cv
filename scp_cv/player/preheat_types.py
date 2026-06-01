#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
播放器预热资源类型定义。
@Project : SCP-cv
@File : preheat_types.py
@Author : Qintsg
@Date : 2026-05-28
'''
from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer


@dataclass
class PreheatedVideoSource:
    """
    已完成初步加载的视频资源。

    :param source_id: 媒体源 ID
    :param uri: 视频路径
    :param player: 已设置 source 的播放器
    :param audio_output: 播放器音频输出
    """

    source_id: int
    uri: str
    player: QMediaPlayer
    audio_output: QAudioOutput


@dataclass
class PreheatedAudioSource:
    """
    已完成初步加载的背景音频资源。

    :param source_id: 媒体源 ID
    :param uri: 音频路径
    :param player: 已设置 source 的播放器
    :param audio_output: 播放器音频输出
    """

    source_id: int
    uri: str
    player: QMediaPlayer
    audio_output: QAudioOutput


@dataclass
class PreheatedStreamSource:
    """
    已建立连接并可被前台认领的直播资源。

    :param source_id: 媒体源 ID
    :param uri: 直播流 URI
    :param instance: libVLC 实例
    :param player: libVLC 播放器
    :param media: libVLC 媒体对象
    :param ready_at: 预热完成时间戳
    """

    source_id: int
    uri: str
    instance: object
    player: object
    media: object
    ready_at: float


@dataclass
class PreheatedPptApplication:
    """
    已启动的 PowerPoint/WPS COM 应用。

    :param backend: PPT 后端名称
    :param app: COM Application 对象
    :param prog_id: 命中的 COM ProgID
    :param source_id: 已预打开的媒体源 ID；0 表示仅预热应用
    :param uri: 已预打开的文件路径
    :param presentation: 已预打开的 Presentation COM 对象
    """

    backend: str
    app: object
    prog_id: str
    source_id: int = 0
    uri: str = ""
    presentation: object | None = None


__all__ = [
    "PreheatedAudioSource",
    "PreheatedPptApplication",
    "PreheatedStreamSource",
    "PreheatedVideoSource",
]
