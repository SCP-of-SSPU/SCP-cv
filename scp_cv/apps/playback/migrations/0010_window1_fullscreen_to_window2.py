#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
增加窗口 1 跨窗口 2 显示区域的持久化状态。
@Project : SCP-cv
@File : 0010_window1_fullscreen_to_window2.py
@Author : Qintsg
@Date : 2026-04-27
'''
from django.db import migrations, models


class Migration(migrations.Migration):
    """
    为播放会话与预案增加窗口 1 填充窗口 2 的状态字段。
    :return: Django migration 定义
    """

    dependencies = [
        ("playback", "0009_remove_scenario_is_splice_mode"),
    ]

    operations = [
        migrations.AddField(
            model_name="playbacksession",
            name="window1_fullscreen_to_window2",
            field=models.BooleanField(
                default=False,
                help_text="启用后窗口 1 跨窗口 1/2 显示区域，窗口 2 隐藏",
                verbose_name="窗口 1 填充窗口 2",
            ),
        ),
        migrations.AddField(
            model_name="scenario",
            name="window1_fullscreen_to_window2",
            field=models.BooleanField(
                default=False,
                help_text="激活预案时恢复窗口 1 跨窗口 1/2 区域显示的布局状态",
                verbose_name="窗口 1 填充窗口 2",
            ),
        ),
    ]
