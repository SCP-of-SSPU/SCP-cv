#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
删除窗口 1 填充窗口 2 布局字段。
@Project : SCP-cv
@File : 0011_remove_window1_fullscreen_to_window2.py
@Author : Qintsg
@Date : 2026-04-28
'''
from __future__ import annotations

from django.db import migrations


class Migration(migrations.Migration):
    """移除已废弃的窗口 1 全屏填充窗口 2 状态字段。"""

    dependencies = [
        ("playback", "0010_window1_fullscreen_to_window2"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="playbacksession",
            name="window1_fullscreen_to_window2",
        ),
        migrations.RemoveField(
            model_name="scenario",
            name="window1_fullscreen_to_window2",
        ),
    ]
