#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
删除 PPT 后端选择字段，PPT 统一使用 Microsoft PowerPoint。
@Project : SCP-cv
@File : 0025_remove_ppt_backend_fields.py
@Author : Qintsg
@Date : 2026-06-08
'''
from __future__ import annotations

from django.db import migrations


class Migration(migrations.Migration):
    """删除历史 PPT 后端选择字段。"""

    dependencies = [
        ("playback", "0024_default_powerpoint_ppt_backend"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="mediasource",
            name="ppt_backend",
        ),
        migrations.RemoveField(
            model_name="playbacksession",
            name="ppt_backend",
        ),
    ]
