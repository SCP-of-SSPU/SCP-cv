#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
数据库迁移回归测试。
@Project : SCP-cv
@File : test_migrations.py
@Author : Qintsg
@Date : 2026-05-09
'''
from __future__ import annotations

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor


@pytest.mark.django_db(transaction=True)
def test_scenario_targets_json_migration_avoids_related_name_collision() -> None:
    """
    验证 0016 可把旧 ScenarioTarget 行迁移到 Scenario.targets JSONField。
    :return: None
    """
    migrate_from = [("playback", "0015_alter_deviceendpoint_address")]
    migrate_to = [("playback", "0016_delete_deviceendpoint_alter_scenariotarget_options_and_more")]
    executor = MigrationExecutor(connection)

    try:
        executor.migrate(migrate_from)
        old_apps = executor.loader.project_state(migrate_from).apps
        MediaSource = old_apps.get_model("playback", "MediaSource")
        Scenario = old_apps.get_model("playback", "Scenario")
        ScenarioTarget = old_apps.get_model("playback", "ScenarioTarget")

        media_source = MediaSource.objects.create(
            name="测试视频",
            source_type="video",
            uri="D:/media/demo.mp4",
        )
        scenario = Scenario.objects.create(name="课前准备")
        ScenarioTarget.objects.create(
            scenario=scenario,
            window_id=1,
            source_state="set",
            source=media_source,
            autoplay=False,
            resume=True,
        )
        ScenarioTarget.objects.create(
            scenario=scenario,
            window_id=2,
            source_state="empty",
            autoplay=True,
            resume=False,
        )

        executor = MigrationExecutor(connection)
        executor.migrate(migrate_to)
        new_apps = executor.loader.project_state(migrate_to).apps
        MigratedScenario = new_apps.get_model("playback", "Scenario")

        migrated_scenario = MigratedScenario.objects.get(pk=scenario.pk)
        assert migrated_scenario.targets == [
            {
                "window_id": 1,
                "source_state": "set",
                "source_id": media_source.pk,
                "autoplay": False,
                "resume": True,
            },
            {
                "window_id": 2,
                "source_state": "empty",
                "source_id": None,
                "autoplay": True,
                "resume": False,
            },
        ]
    finally:
        final_executor = MigrationExecutor(connection)
        final_executor.migrate(final_executor.loader.graph.leaf_nodes())


@pytest.mark.django_db(transaction=True)
def test_media_source_preheat_migration_preserves_legacy_non_web_semantics() -> None:
    """
    验证 0022 不会把旧版本中无效默认的非网页 keep_alive=True 变成启动预热。
    :return: None
    """
    migrate_from = [("playback", "0021_add_wps_ppt_backend")]
    migrate_to = [("playback", "0022_alter_mediasource_keep_alive")]
    executor = MigrationExecutor(connection)

    try:
        executor.migrate(migrate_from)
        old_apps = executor.loader.project_state(migrate_from).apps
        MediaSource = old_apps.get_model("playback", "MediaSource")

        video_source = MediaSource.objects.create(
            name="历史视频",
            source_type="video",
            uri="D:/media/demo.mp4",
            keep_alive=True,
        )
        web_source = MediaSource.objects.create(
            name="历史网页",
            source_type="web",
            uri="http://example.local",
            keep_alive=True,
        )

        executor = MigrationExecutor(connection)
        executor.migrate(migrate_to)
        new_apps = executor.loader.project_state(migrate_to).apps
        MigratedMediaSource = new_apps.get_model("playback", "MediaSource")

        assert MigratedMediaSource.objects.get(pk=video_source.pk).keep_alive is False
        assert MigratedMediaSource.objects.get(pk=web_source.pk).keep_alive is True
    finally:
        final_executor = MigrationExecutor(connection)
        final_executor.migrate(final_executor.loader.graph.leaf_nodes())


@pytest.mark.django_db(transaction=True)
def test_control_command_migration_imports_non_empty_legacy_slots() -> None:
    """验证 0026 会把窗口和背景音频的非空旧指令导入持久化队列。"""
    migrate_from = [("playback", "0025_remove_ppt_backend_fields")]
    migrate_to = [("playback", "0026_control_command_queue")]
    executor = MigrationExecutor(connection)

    try:
        executor.migrate(migrate_from)
        old_apps = executor.loader.project_state(migrate_from).apps
        PlaybackSession = old_apps.get_model("playback", "PlaybackSession")
        BackgroundAudioState = old_apps.get_model("playback", "BackgroundAudioState")

        PlaybackSession.objects.create(
            window_id=1,
            pending_command="next",
            command_args={"target_index": 7},
        )
        PlaybackSession.objects.create(window_id=2, pending_command="", command_args={})
        BackgroundAudioState.objects.create(
            pk=1,
            pending_command="play",
            command_args={"resume": True},
        )

        executor = MigrationExecutor(connection)
        executor.migrate(migrate_to)
        new_apps = executor.loader.project_state(migrate_to).apps
        ControlCommand = new_apps.get_model("playback", "ControlCommand")

        imported = list(
            ControlCommand.objects.order_by("id").values(
                "target",
                "command",
                "arguments",
                "status",
            )
        )
        assert imported == [
            {
                "target": "window:1",
                "command": "next",
                "arguments": {"target_index": 7},
                "status": "pending",
            },
            {
                "target": "background_audio",
                "command": "play",
                "arguments": {"resume": True},
                "status": "pending",
            },
        ]
    finally:
        final_executor = MigrationExecutor(connection)
        final_executor.migrate(final_executor.loader.graph.leaf_nodes())
