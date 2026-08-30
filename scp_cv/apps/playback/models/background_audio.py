#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
背景音频模型：全局背景音乐播放器状态与播放列表。
@Project : SCP-cv
@File : models/background_audio.py
@Author : Qintsg
@Date : 2026-05-31
'''
from __future__ import annotations

from django.db import models

from .enums import BackgroundAudioCommand, PlaybackState
from .media import MediaSource


class BackgroundAudioState(models.Model):
    """
    背景音频全局状态单例。
    播放器进程轮询 pending_command，执行后回写播放状态和进度。
    """

    id = models.AutoField(primary_key=True)
    current_source = models.ForeignKey(
        MediaSource,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="background_audio_states",
        verbose_name="当前音频源",
    )
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
    position_ms = models.BigIntegerField(
        default=0,
        verbose_name="当前位置(ms)",
    )
    duration_ms = models.BigIntegerField(
        default=0,
        verbose_name="总时长(ms)",
    )
    volume = models.IntegerField(
        default=70,
        verbose_name="音量（0-100）",
    )
    is_muted = models.BooleanField(
        default=False,
        verbose_name="是否静音",
    )
    loop_enabled = models.BooleanField(
        default=True,
        verbose_name="列表循环播放",
    )
    pending_command = models.CharField(
        max_length=32,
        choices=BackgroundAudioCommand.choices,
        default=BackgroundAudioCommand.NONE,
        blank=True,
        verbose_name="待执行指令",
    )
    command_args = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="指令参数",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="最后更新",
    )

    class Meta:
        verbose_name = "背景音频状态"
        verbose_name_plural = "背景音频状态"

    def __str__(self) -> str:
        source_name = self.current_source.name if self.current_source else "无"
        return f"背景音频 / {source_name} / {self.get_playback_state_display()}"

    @classmethod
    def get_instance(cls) -> "BackgroundAudioState":
        """获取或创建背景音频全局单例。"""
        instance, _ = cls.objects.get_or_create(pk=1)
        return instance


class BackgroundAudioCommandRecord(models.Model):
    """背景音频的持久有序命令队列。"""

    state = models.ForeignKey(
        BackgroundAudioState,
        on_delete=models.CASCADE,
        related_name="command_queue",
        verbose_name="背景音频状态",
    )
    command = models.CharField(max_length=32, choices=BackgroundAudioCommand.choices, verbose_name="播放指令")
    command_args = models.JSONField(default=dict, blank=True, verbose_name="指令参数")
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
            models.Index(fields=["state", "id"], name="bg_audio_cmd_state_idx"),
            models.Index(fields=["state", "status", "id"], name="bg_audio_cmd_status_idx"),
        ]
        verbose_name = "背景音频指令队列项"
        verbose_name_plural = "背景音频指令队列项"


class BackgroundAudioPlaylistItem(models.Model):
    """
    背景音频播放列表项。
    仅允许绑定 audio 类型 MediaSource；具体校验由服务层负责。
    """

    source = models.ForeignKey(
        MediaSource,
        on_delete=models.CASCADE,
        related_name="background_audio_playlist_items",
        verbose_name="音频源",
    )
    sort_order = models.IntegerField(
        default=0,
        verbose_name="排序权重",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="创建时间",
    )

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "背景音频播放列表项"
        verbose_name_plural = "背景音频播放列表项"

    def __str__(self) -> str:
        return f"{self.sort_order}. {self.source.name}"


__all__ = ["BackgroundAudioCommandRecord", "BackgroundAudioPlaylistItem", "BackgroundAudioState"]
