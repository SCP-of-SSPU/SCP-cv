#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
移除预案中的窗口 1+2 拼接模式字段。
@Project : SCP-cv
@File : 0009_remove_scenario_is_splice_mode.py
@Author : Qintsg
@Date : 2026-04-27
'''
from django.db import migrations


class Migration(migrations.Migration):
    """删除已下线的窗口 1+2 拼接模式配置。"""

    dependencies = [
        ("playback", "0008_scenario_model"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="scenario",
            name="is_splice_mode",
        ),
    ]
