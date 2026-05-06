#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
预案模型：Scenario（预案主表）。
@Project : SCP-cv
@File : models/scenario_models.py
@Author : Qintsg
@Date : 2026-04-29
'''
from __future__ import annotations

from django.db import models

from .enums import BigScreenMode, SourceState


class Scenario(models.Model):
    """
    预案模型：预定义大屏/TV 的播放配置快照。
    激活时按三态语义应用各窗口内容，支持置顶排序。
    """

    name = models.CharField(
        max_length=100,
        verbose_name="预案名称",
    )
    description = models.TextField(
        blank=True,
        default="",
        verbose_name="描述",
    )
    sort_order = models.IntegerField(
        default=0,
        verbose_name="排序权重",
        help_text="数值越大越靠前，支持置顶",
    )
    big_screen_mode_state = models.CharField(
        max_length=8,
        choices=SourceState.choices,
        default=SourceState.UNSET,
        verbose_name="大屏模式状态",
    )
    big_screen_mode = models.CharField(
        max_length=8,
        choices=BigScreenMode.choices,
        default=BigScreenMode.SINGLE,
        blank=True,
        verbose_name="大屏模式",
        help_text="仅当 big_screen_mode_state=set 时生效",
    )
    volume_state = models.CharField(
        max_length=8,
        choices=SourceState.choices,
        default=SourceState.UNSET,
        verbose_name="音量状态",
    )
    volume_level = models.IntegerField(
        default=100,
        verbose_name="音量等级（0-100）",
        help_text="仅当 volume_state=set 时生效",
    )
    targets = models.JSONField(
        default=list,
        blank=True,
        verbose_name="窗口目标配置",
        help_text="四窗口目标列表，元素包含 window_id、source_state、source_id、autoplay、resume",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="创建时间",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="更新时间",
    )

    class Meta:
        ordering = ["-sort_order", "-updated_at"]
        verbose_name = "预案"
        verbose_name_plural = "预案"

    def __str__(self) -> str:
        return self.name


__all__ = ["Scenario"]
