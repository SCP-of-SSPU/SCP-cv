#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
已废弃的设备模型占位模块，仅用于兼容旧迁移导入。
@Project : SCP-cv
@File : models/device.py
@Author : Qintsg
@Date : 2026-05-06
'''
from __future__ import annotations

from django.db import models


class DeviceEndpoint(models.Model):
    """兼容旧迁移保留的占位模型，不再参与运行时业务。"""

    class Meta:
        managed = False
        db_table = "playback_deviceendpoint"
        verbose_name = "设备端点（旧）"
        verbose_name_plural = "设备端点（旧）"

    def __str__(self) -> str:
        return "deprecated-device-endpoint"
