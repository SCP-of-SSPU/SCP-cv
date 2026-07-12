#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
新增持久化控制命令队列。
@Project : SCP-cv
@File : 0026_control_command_queue.py
@Author : Qintsg
@Date : 2026-07-11
'''
from __future__ import annotations

import uuid

from django.apps.registry import Apps
from django.db import migrations, models
from django.db.backends.base.schema import BaseDatabaseSchemaEditor


def import_legacy_commands(
    apps: Apps,
    schema_editor: BaseDatabaseSchemaEditor,
) -> None:
    """把迁移时仍未消费的旧单槽指令追加到新队列。"""
    database_alias = schema_editor.connection.alias
    ControlCommand = apps.get_model("playback", "ControlCommand")
    PlaybackSession = apps.get_model("playback", "PlaybackSession")
    BackgroundAudioState = apps.get_model("playback", "BackgroundAudioState")

    sessions = (
        PlaybackSession.objects.using(database_alias)
        .exclude(pending_command="")
        .order_by("window_id")
    )
    for session in sessions.iterator():
        ControlCommand.objects.using(database_alias).create(
            target=f"window:{session.window_id}",
            command=session.pending_command,
            arguments=session.command_args or {},
        )

    audio_states = (
        BackgroundAudioState.objects.using(database_alias)
        .exclude(pending_command="")
        .order_by("pk")
    )
    for state in audio_states.iterator():
        ControlCommand.objects.using(database_alias).create(
            target="background_audio",
            command=state.pending_command,
            arguments=state.command_args or {},
        )


class Migration(migrations.Migration):
    """创建有序、可确认的控制命令表。"""

    dependencies = [
        ("playback", "0025_remove_ppt_backend_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="ControlCommand",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "target",
                    models.CharField(
                        choices=[
                            ("window:1", "窗口 1"),
                            ("window:2", "窗口 2"),
                            ("window:3", "窗口 3"),
                            ("window:4", "窗口 4"),
                            ("background_audio", "背景音频"),
                        ],
                        max_length=32,
                        verbose_name="控制目标",
                    ),
                ),
                ("command", models.CharField(max_length=64, verbose_name="控制指令")),
                (
                    "arguments",
                    models.JSONField(blank=True, default=dict, verbose_name="指令参数"),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "待领取"),
                            ("executing", "执行中"),
                            ("succeeded", "已成功"),
                            ("failed", "已失败"),
                            ("cancelled", "已取消"),
                        ],
                        default="pending",
                        max_length=16,
                        verbose_name="执行状态",
                    ),
                ),
                (
                    "batch_id",
                    models.UUIDField(
                        db_index=True,
                        default=uuid.uuid4,
                        editable=False,
                        verbose_name="批次编号",
                    ),
                ),
                (
                    "consumer_id",
                    models.CharField(
                        blank=True,
                        default="",
                        max_length=128,
                        verbose_name="消费者编号",
                    ),
                ),
                (
                    "consumer_pid",
                    models.PositiveBigIntegerField(
                        blank=True,
                        null=True,
                        verbose_name="消费者进程 PID",
                    ),
                ),
                (
                    "consumer_process_started_at",
                    models.FloatField(
                        blank=True,
                        null=True,
                        verbose_name="消费者进程创建时间",
                    ),
                ),
                (
                    "consumer_heartbeat_at",
                    models.DateTimeField(
                        blank=True,
                        null=True,
                        verbose_name="消费者心跳时间",
                    ),
                ),
                (
                    "cancel_requested",
                    models.BooleanField(default=False, verbose_name="请求取消"),
                ),
                (
                    "error_message",
                    models.TextField(blank=True, default="", verbose_name="错误说明"),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="创建时间")),
                (
                    "started_at",
                    models.DateTimeField(blank=True, null=True, verbose_name="开始时间"),
                ),
                (
                    "finished_at",
                    models.DateTimeField(blank=True, null=True, verbose_name="完成时间"),
                ),
            ],
            options={
                "verbose_name": "控制指令",
                "verbose_name_plural": "控制指令",
                "ordering": ["id"],
                "constraints": [
                    models.UniqueConstraint(
                        condition=models.Q(("status", "executing")),
                        fields=("target",),
                        name="ctrlcmd_one_executing_target",
                    ),
                ],
                "indexes": [
                    models.Index(
                        fields=["target", "status", "id"],
                        name="ctrlcmd_target_status_id",
                    ),
                ],
            },
        ),
        migrations.RunPython(import_legacy_commands, migrations.RunPython.noop),
    ]
