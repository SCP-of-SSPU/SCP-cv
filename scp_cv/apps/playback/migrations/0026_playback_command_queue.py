#!/user/bin/env python
# -*- coding: UTF-8 -*-
"""新增可靠的播放指令队列。"""

from __future__ import annotations

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("playback", "0025_remove_ppt_backend_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="playbacksession",
            name="player_last_seen_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="播放器最后心跳"),
        ),
        migrations.CreateModel(
            name="PlaybackCommandRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("command", models.CharField(choices=[("", "无"), ("open", "打开源"), ("play", "播放"), ("pause", "暂停"), ("stop", "停止"), ("close", "关闭"), ("seek", "跳转"), ("next", "下一页/下一项"), ("prev", "上一页/上一项"), ("goto", "跳转到指定页"), ("set_loop", "设置循环播放"), ("set_volume", "设置音量"), ("set_mute", "设置静音"), ("ppt_media", "控制 PPT 当前页媒体"), ("reset_ppt", "重置 PPT 放映"), ("show_id", "显示窗口 ID")], max_length=32, verbose_name="播放指令")),
                ("command_args", models.JSONField(blank=True, default=dict, verbose_name="指令参数")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="创建时间")),
                ("session", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="command_queue", to="playback.playbacksession", verbose_name="播放会话")),
            ],
            options={
                "verbose_name": "播放指令队列项",
                "verbose_name_plural": "播放指令队列项",
                "ordering": ["id"],
            },
        ),
        migrations.AddIndex(
            model_name="playbackcommandrecord",
            index=models.Index(fields=["session", "id"], name="playback_cmd_session_idx"),
        ),
    ]
