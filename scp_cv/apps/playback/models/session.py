#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
播放会话模型（PlaybackSession）：每窗口一个独立实例，维护播放状态与指令分发。
@Project : SCP-cv
@File : models/session.py
@Author : Qintsg
@Date : 2026-04-29
'''
from __future__ import annotations

from django.db import models

from .enums import PlaybackCommand, PlaybackMode, PlaybackState
from .media import MediaSource


class PlaybackSession(models.Model):
    """
    播放会话模型，每个输出窗口维护一个独立实例。
    通过 window_id（1-4）区分不同窗口的播放状态与指令。
    播放器进程通过轮询本表驱动播放行为。
    """

    # ── 窗口标识（1-4） ──
    window_id = models.PositiveSmallIntegerField(
        unique=True,
        verbose_name="窗口编号",
        help_text="输出窗口编号，1-4 对应四个输出显示器",
    )

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
    error_message = models.TextField(
        blank=True,
        default="",
        verbose_name="播放错误说明",
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

    # ── 音频与循环 ──
    volume = models.IntegerField(
        default=100,
        verbose_name="音量（0-100）",
    )
    is_muted = models.BooleanField(
        default=False,
        verbose_name="是否静音",
    )
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
    player_last_seen_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="播放器最后心跳",
    )

    # ── 时间戳 ──
    last_updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="最后更新",
    )

    class Meta:
        ordering = ["window_id"]
        verbose_name = "播放会话"
        verbose_name_plural = "播放会话"

    def __str__(self) -> str:
        source_label = self.media_source.name if self.media_source else "无"
        return f"窗口{self.window_id} / {source_label} / {self.get_playback_state_display()}"


class PlaybackCommandRecord(models.Model):
    """按写入顺序持久化的播放器指令，避免单槽 pending_command 丢失操作。"""

    session = models.ForeignKey(
        PlaybackSession,
        on_delete=models.CASCADE,
        related_name="command_queue",
        verbose_name="播放会话",
    )
    command = models.CharField(
        max_length=32,
        choices=PlaybackCommand.choices,
        verbose_name="播放指令",
    )
    command_args = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="指令参数",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    status = models.CharField(
        max_length=16,
        choices=(("pending", "待领取"), ("processing", "处理中")),
        default="pending",
        db_index=True,
        verbose_name="处理状态",
    )
    claimed_by = models.CharField(max_length=128, blank=True, default="", verbose_name="领取消费者")
    claimed_at = models.DateTimeField(null=True, blank=True, verbose_name="领取时间")
    attempt_count = models.PositiveIntegerField(default=0, verbose_name="尝试次数")
    last_error = models.TextField(blank=True, default="", verbose_name="最后错误")

    class Meta:
        ordering = ["id"]
        indexes = [
            models.Index(fields=["session", "id"], name="playback_cmd_session_idx"),
            models.Index(fields=["session", "status", "id"], name="playback_cmd_status_idx"),
        ]
        verbose_name = "播放指令队列项"
        verbose_name_plural = "播放指令队列项"
