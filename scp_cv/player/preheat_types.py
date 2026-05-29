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
class PreheatedPptApplication:
    """
    已启动的 PowerPoint/WPS COM 应用。

    :param backend: PPT 后端名称
    :param app: COM Application 对象
    :param prog_id: 命中的 COM ProgID
    """

    backend: str
    app: object
    prog_id: str


__all__ = [
    "PreheatedPptApplication",
    "PreheatedVideoSource",
]
