#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
持久化控制命令模型：为播放窗口和背景音频保存有序、可确认的控制指令。
@Project : SCP-cv
@File : models/control_command.py
@Author : Qintsg
@Date : 2026-07-11
'''
from __future__ import annotations

import uuid

from django.db import models


class ControlCommandTarget(models.TextChoices):
    """控制指令的独立消费通道。"""

    WINDOW_1 = "window:1", "窗口 1"
    WINDOW_2 = "window:2", "窗口 2"
    WINDOW_3 = "window:3", "窗口 3"
    WINDOW_4 = "window:4", "窗口 4"
    BACKGROUND_AUDIO = "background_audio", "背景音频"


class ControlCommandStatus(models.TextChoices):
    """控制指令从入队到完成的生命周期。"""

    PENDING = "pending", "待领取"
    EXECUTING = "executing", "执行中"
    SUCCEEDED = "succeeded", "已成功"
    FAILED = "failed", "已失败"
    CANCELLED = "cancelled", "已取消"


class ControlCommand(models.Model):
    """一个目标通道中的单条、持久化控制指令。"""

    target = models.CharField(
        max_length=32,
        choices=ControlCommandTarget.choices,
        verbose_name="控制目标",
    )
    command = models.CharField(max_length=64, verbose_name="控制指令")
    arguments = models.JSONField(default=dict, blank=True, verbose_name="指令参数")
    status = models.CharField(
        max_length=16,
        choices=ControlCommandStatus.choices,
        default=ControlCommandStatus.PENDING,
        verbose_name="执行状态",
    )
    batch_id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        db_index=True,
        verbose_name="批次编号",
    )
    consumer_id = models.CharField(
        max_length=128,
        blank=True,
        default="",
        verbose_name="消费者编号",
    )
    consumer_pid = models.PositiveBigIntegerField(
        null=True,
        blank=True,
        verbose_name="消费者进程 PID",
    )
    consumer_process_started_at = models.FloatField(
        null=True,
        blank=True,
        verbose_name="消费者进程创建时间",
    )
    consumer_heartbeat_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="消费者心跳时间",
    )
    cancel_requested = models.BooleanField(default=False, verbose_name="请求取消")
    error_message = models.TextField(blank=True, default="", verbose_name="错误说明")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    started_at = models.DateTimeField(null=True, blank=True, verbose_name="开始时间")
    finished_at = models.DateTimeField(null=True, blank=True, verbose_name="完成时间")

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["target"],
                condition=models.Q(status=ControlCommandStatus.EXECUTING),
                name="ctrlcmd_one_executing_target",
            ),
        ]
        indexes = [
            models.Index(
                fields=["target", "status", "id"],
                name="ctrlcmd_target_status_id",
            ),
        ]
        verbose_name = "控制指令"
        verbose_name_plural = "控制指令"


__all__ = ["ControlCommand", "ControlCommandStatus", "ControlCommandTarget"]
