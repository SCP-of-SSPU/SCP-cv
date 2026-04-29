#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
设备开关机占位模型（DeviceEndpoint）：记录可控制的物理设备占位信息。
@Project : SCP-cv
@File : models/device.py
@Author : Qintsg
@Date : 2026-04-29
'''
from __future__ import annotations

from django.db import models

from .enums import DeviceType


class DeviceEndpoint(models.Model):
    """
    设备端点占位模型，记录可控制的物理设备。
    当前仅用于前端 UI 占位，实际控制逻辑待后续实现。
    """

    name = models.CharField(
        max_length=100,
        verbose_name="设备名称",
    )
    device_type = models.CharField(
        max_length=24,
        choices=DeviceType.choices,
        unique=True,
        verbose_name="设备类型",
    )
    is_powered_on = models.BooleanField(
        default=False,
        verbose_name="是否开机",
    )
    address = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="设备地址",
        help_text="IP 或串口地址，待后续实现",
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="扩展信息",
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
        ordering = ["device_type"]
        verbose_name = "设备端点"
        verbose_name_plural = "设备端点"

    def __str__(self) -> str:
        power_label = "开机" if self.is_powered_on else "关机"
        return f"{self.name}（{power_label})"
