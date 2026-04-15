#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
播放系统数据模型：统一媒体源（MediaSource）与播放会话（PlaybackSession）。
MediaSource 统一管理所有可播放源（PPT、视频、RTSP 流等），
PlaybackSession 维护当前播放状态与指令分发。
@Project : SCP-cv
@File : models.py
@Author : Qintsg
@Date : 2026-04-14
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


class MediaSource(models.Model):
    """
    统一媒体源模型，所有可播放内容的注册表。
    文件型源（PPT/视频/图片等）通过上传或本地路径录入；
    RTSP 流型源由 MediaMTX 自动发现后同步创建。
    """

    source_type = models.CharField(
        max_length=24,
        choices=SourceType.choices,
        db_index=True,
        verbose_name="源类型",
    )
    name = models.CharField(
        max_length=255,
        verbose_name="显示名称",
    )
    uri = models.CharField(
        max_length=1024,
        verbose_name="资源地址",
        help_text="文件绝对路径、URL 或流标识符",
    )
    uploaded_file = models.FileField(
        upload_to="uploads/%Y%m%d/",
        blank=True,
        verbose_name="上传文件",
        help_text="通过 Web 上传的文件存储路径",
    )
    # 仅 RTSP_STREAM 类型使用，关联自动发现的流记录
    stream_identifier = models.CharField(
        max_length=255,
        blank=True,
        db_index=True,
        verbose_name="流标识符",
        help_text="RTSP 流的 MediaMTX 路径标识",
    )
    is_available = models.BooleanField(
        default=True,
        verbose_name="是否可用",
        help_text="文件是否存在 / 流是否在线",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="创建时间",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "媒体源"
        verbose_name_plural = "媒体源"

    def __str__(self) -> str:
        return f"[{self.get_source_type_display()}] {self.name}"


class PlaybackSession(models.Model):
    """
    统一播放会话，系统只维护一个实例。
    记录当前播放的源、状态、显示配置、以及待执行的控制指令。
    播放器进程通过轮询本表驱动播放行为。
    """

    # ── 当前播放源 ──
    media_source = models.ForeignKey(
        MediaSource,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="playback_sessions",
        verbose_name="当前媒体源",
    )

    # ── 播放状态 ──
    playback_state = models.CharField(
        max_length=16,
        choices=PlaybackState.choices,
        default=PlaybackState.IDLE,
        verbose_name="播放状态",
    )

    # ── 显示配置（由启动器 GUI 写入） ──
    display_mode = models.CharField(
        max_length=24,
        choices=PlaybackMode.choices,
        default=PlaybackMode.SINGLE,
        verbose_name="显示模式",
    )
    target_display_label = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="目标显示器",
    )
    spliced_display_label = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="拼接显示器组",
    )
    is_spliced = models.BooleanField(
        default=False,
        verbose_name="是否拼接",
    )

    # ── PPT / 翻页型源状态 ──
    current_slide = models.IntegerField(
        default=0,
        verbose_name="当前页码",
    )
    total_slides = models.IntegerField(
        default=0,
        verbose_name="总页数",
    )

    # ── 时间线型源状态（视频/音频） ──
    position_ms = models.BigIntegerField(
        default=0,
        verbose_name="当前位置(ms)",
    )
    duration_ms = models.BigIntegerField(
        default=0,
        verbose_name="总时长(ms)",
    )

    # ── 循环播放设置 ──
    loop_enabled = models.BooleanField(
        default=False,
        verbose_name="循环播放",
        help_text="视频/音频播放完毕后是否自动重头播放",
    )

    # ── 控制指令分发（Django 写入 → 播放器消费） ──
    pending_command = models.CharField(
        max_length=32,
        choices=PlaybackCommand.choices,
        default=PlaybackCommand.NONE,
        blank=True,
        verbose_name="待执行指令",
    )
    command_args = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="指令参数",
    )

    # ── 时间戳 ──
    last_updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="最后更新",
    )

    class Meta:
        ordering = ["-last_updated_at"]
        verbose_name = "播放会话"
        verbose_name_plural = "播放会话"

    def __str__(self) -> str:
        source_label = self.media_source.name if self.media_source else "无"
        return f"{source_label} / {self.get_playback_state_display()}"
