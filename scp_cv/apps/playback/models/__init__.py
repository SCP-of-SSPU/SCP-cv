#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
播放系统数据模型的 __init__ 入口，重新导出所有模型以保持向后兼容。
@Project : SCP-cv
@File : models/__init__.py
@Author : Qintsg
@Date : 2026-04-29
'''
from __future__ import annotations

from .enums import (
    BackgroundAudioCommand,
    BigScreenMode,
    DeviceType,
    PlaybackCommand,
    PlaybackMode,
    PlaybackState,
    SourceState,
    SourceType,
)
from .background_audio import BackgroundAudioPlaylistItem, BackgroundAudioState
from .media import MediaFolder, MediaSource, PptResource
from .session import PlaybackSession
from .scenario_models import Scenario
from .runtime import RuntimeState

__all__ = [
    "BackgroundAudioCommand",
    "BackgroundAudioPlaylistItem",
    "BackgroundAudioState",
    "BigScreenMode",
    "DeviceType",
    "MediaFolder",
    "MediaSource",
    "PlaybackCommand",
    "PlaybackMode",
    "PlaybackSession",
    "PlaybackState",
    "PptResource",
    "RuntimeState",
    "Scenario",
    "ScenarioTarget",
    "SourceState",
    "SourceType",
]
