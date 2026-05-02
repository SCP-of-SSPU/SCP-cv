#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
播放系统枚举常量：源类型、显示模式、播放状态、控制指令、预案三态、设备类型。
@Project : SCP-cv
@File : models/enums.py
@Author : Qintsg
@Date : 2026-04-29
'''
from __future__ import annotations

from django.db import models


class SourceType(models.TextChoices):
    """统一媒体源类型枚举，覆盖所有可播放内容。"""

    PPT = "ppt", "PPT 演示文稿"
    VIDEO = "video", "视频"
    AUDIO = "audio", "音频"
    IMAGE = "image", "图片"
    WEB = "web", "网页"
    CUSTOM_STREAM = "custom_stream", "自定义流"
    RTSP_STREAM = "rtsp_stream", "RTSP 流"
    SRT_STREAM = "srt_stream", "SRT 流"


class PlaybackMode(models.TextChoices):
    """播放目标布局。"""

    SINGLE = "single", "单屏"
    LEFT_RIGHT_SPLICE = "left_right_splice", "左右拼接"


class BigScreenMode(models.TextChoices):
    """大屏显示状态：single 仅窗口 1，double 窗口 1+2 左右各半。"""

    SINGLE = "single", "单屏"
    DOUBLE = "double", "双屏"


class PlaybackState(models.TextChoices):
    """播放会话状态。"""

    IDLE = "idle", "待机"
    LOADING = "loading", "加载中"
    PLAYING = "playing", "播放中"
    PAUSED = "paused", "暂停"
    STOPPED = "stopped", "已停止"
    ERROR = "error", "异常"


class PlaybackCommand(models.TextChoices):
    """播放控制指令枚举，由 Django 写入、播放器轮询消费。"""

    NONE = "", "无"
    OPEN = "open", "打开源"
    PLAY = "play", "播放"
    PAUSE = "pause", "暂停"
    STOP = "stop", "停止"
    CLOSE = "close", "关闭"
    SEEK = "seek", "跳转"
    NEXT = "next", "下一页/下一项"
    PREV = "prev", "上一页/上一项"
    GOTO = "goto", "跳转到指定页"
    SET_LOOP = "set_loop", "设置循环播放"
    SET_VOLUME = "set_volume", "设置音量"
    SET_MUTE = "set_mute", "设置静音"
    PPT_MEDIA = "ppt_media", "控制 PPT 当前页媒体"
    SHOW_ID = "show_id", "显示窗口 ID"


class SourceState(models.TextChoices):
    """预案中窗口内容的三态语义。"""

    UNSET = "unset", "未设置（保持原有）"
    EMPTY = "empty", "清空（黑屏）"
    SET = "set", "已设置（使用绑定源）"


class DeviceType(models.TextChoices):
    """设备类型枚举，用于电源控制卡片。"""

    SPLICE_SCREEN = "splice_screen", "拼接屏"
    TV_LEFT = "tv_left", "电视左"
    TV_RIGHT = "tv_right", "电视右"
