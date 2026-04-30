#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
全局运行状态模型（RuntimeState）：大屏模式、系统音量等全局状态单例。
@Project : SCP-cv
@File : models/runtime.py
@Author : Qintsg
@Date : 2026-04-29
'''
from __future__ import annotations

from django.db import models

from .enums import BigScreenMode


class RuntimeState(models.Model):
    """
    全局运行状态单例，记录当前大屏模式等全局状态。
    通过 id=1 强制单例约束。
    """

    id = models.AutoField(primary_key=True)
    big_screen_mode = models.CharField(
        max_length=8,
        choices=BigScreenMode.choices,
        default=BigScreenMode.SINGLE,
        verbose_name="当前大屏模式",
    )
    volume_level = models.IntegerField(
        default=100,
        verbose_name="系统音量（0-100）",
    )
    volume_muted = models.BooleanField(
        default=False,
        verbose_name="系统是否静音",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="最后更新",
    )

    class Meta:
        verbose_name = "运行状态"
        verbose_name_plural = "运行状态"

    def __str__(self) -> str:
        muted_label = "静音" if self.volume_muted else "未静音"
        return f"大屏: {self.get_big_screen_mode_display()}, 音量: {self.volume_level}, {muted_label}"

    @classmethod
    def get_instance(cls) -> "RuntimeState":
        """获取或创建全局单例。"""
        instance, _ = cls.objects.get_or_create(pk=1)
        return instance
