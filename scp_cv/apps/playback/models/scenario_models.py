#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
预案模型：Scenario（预案主表）与 ScenarioTarget（四窗口目标配置）。
@Project : SCP-cv
@File : models/scenario_models.py
@Author : Qintsg
@Date : 2026-04-29
'''
from __future__ import annotations

from django.db import models

from .enums import BigScreenMode, SourceState
from .media import MediaSource


class Scenario(models.Model):
    """
    预案模型：预定义大屏/TV 的播放配置快照。
    激活时按三态语义应用各窗口内容，支持置顶排序。
    """

    # ── 基本信息 ──
    name = models.CharField(
        max_length=100,
        verbose_name="预案名称",
    )
    description = models.TextField(
        blank=True,
        default="",
        verbose_name="描述",
    )

    # ── 排序（置顶优先） ──
    sort_order = models.IntegerField(
        default=0,
        verbose_name="排序权重",
        help_text="数值越大越靠前，支持置顶",
    )

    # ── 大屏模式 ──
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

    # ── 音量 ──
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

    # ── 时间戳 ──
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


class ScenarioTarget(models.Model):
    """
    预案中的单个窗口目标配置。
    通过 source_state 三态语义决定激活时行为：
    - unset：激活时不改变该窗口
    - empty：激活时关闭该窗口（黑屏）
    - set：激活时打开绑定的媒体源
    """

    scenario = models.ForeignKey(
        Scenario,
        on_delete=models.CASCADE,
        related_name="targets",
        verbose_name="所属预案",
    )
    window_id = models.PositiveSmallIntegerField(
        verbose_name="窗口编号",
        help_text="1-4 对应四个输出窗口",
    )
    source_state = models.CharField(
        max_length=8,
        choices=SourceState.choices,
        default=SourceState.UNSET,
        verbose_name="内容状态",
    )
    source = models.ForeignKey(
        MediaSource,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="scenario_targets",
        verbose_name="绑定媒体源",
        help_text="仅当 source_state=set 时生效",
    )
    autoplay = models.BooleanField(
        default=True,
        verbose_name="自动播放",
        help_text="仅当 source_state=set 时生效",
    )
    resume = models.BooleanField(
        default=True,
        verbose_name="保留进度",
        help_text="相同源已打开时保留当前进度，否则从头播放",
    )

    class Meta:
        ordering = ["window_id"]
        unique_together = [("scenario", "window_id")]
        verbose_name = "预案窗口目标"
        verbose_name_plural = "预案窗口目标"

    def __str__(self) -> str:
        state_label = self.get_source_state_display()
        if self.source_state == SourceState.SET and self.source:
            return f"窗口{self.window_id}: {self.source.name}"
        return f"窗口{self.window_id}: {state_label}"
