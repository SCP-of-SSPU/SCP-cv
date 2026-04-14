#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
pytest 全局 fixtures，提供数据库访问和常用测试对象。
@Project : SCP-cv
@File : conftest.py
@Author : Qintsg
@Date : 2026-04-14
'''
from __future__ import annotations

import pytest

from scp_cv.apps.playback.models import MediaSource, PlaybackSession, SourceType


@pytest.fixture
def media_source_ppt(db) -> MediaSource:
    """
    创建一个 PPT 类型的 MediaSource 测试对象。
    :return: 已持久化的 PPT 媒体源
    """
    return MediaSource.objects.create(
        source_type=SourceType.PPT,
        name="测试演示文稿",
        uri="C:/测试/演示.pptx",
        is_available=True,
    )


@pytest.fixture
def media_source_video(db) -> MediaSource:
    """
    创建一个 VIDEO 类型的 MediaSource 测试对象。
    :return: 已持久化的视频媒体源
    """
    return MediaSource.objects.create(
        source_type=SourceType.VIDEO,
        name="测试视频",
        uri="C:/测试/视频.mp4",
        is_available=True,
    )


@pytest.fixture
def media_source_unavailable(db) -> MediaSource:
    """
    创建一个不可用的 MediaSource 测试对象。
    :return: is_available=False 的媒体源
    """
    return MediaSource.objects.create(
        source_type=SourceType.VIDEO,
        name="不可用视频",
        uri="C:/不存在/文件.mp4",
        is_available=False,
    )


@pytest.fixture
def playback_session(db) -> PlaybackSession:
    """
    创建一个空的 PlaybackSession 测试对象。
    :return: 已持久化的播放会话（IDLE 状态）
    """
    return PlaybackSession.objects.create()
