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
def test_display_splice_data_is_normalized_before_legacy_fields_are_removed() -> None:
    """0029 应先将历史拼接会话归一为 single，再删除旧字段。"""
    migrate_from = [("playback", "0028_backgroundaudiocommandrecord_and_more")]
    migrate_to = [("playback", "0029_remove_playbacksession_is_spliced_and_more")]
    executor = MigrationExecutor(connection)
    try:
        executor.migrate(migrate_from)
        old_apps = executor.loader.project_state(migrate_from).apps
        OldSession = old_apps.get_model("playback", "PlaybackSession")
        session = OldSession.objects.create(
            window_id=1,
            display_mode="left_right_splice",
            is_spliced=True,
            spliced_display_label="HDMI-1 + HDMI-2",
        )

        executor = MigrationExecutor(connection)
        executor.migrate(migrate_to)
        new_apps = executor.loader.project_state(migrate_to).apps
        NewSession = new_apps.get_model("playback", "PlaybackSession")
        assert NewSession.objects.get(pk=session.pk).display_mode == "single"
        assert not any(
            field.name in {"is_spliced", "spliced_display_label"}
            for field in NewSession._meta.fields
        )
    finally:
        final_executor = MigrationExecutor(connection)
        final_executor.migrate(final_executor.loader.graph.leaf_nodes())


@pytest.mark.django_db(transaction=True)
def test_command_queue_migration_preserves_legacy_background_command() -> None:
    """0028 应把升级前的背景音频单槽命令转入 pending 队列。"""
    migrate_from = [("playback", "0027_alter_mediasource_source_type")]
    migrate_to = [("playback", "0028_backgroundaudiocommandrecord_and_more")]
    executor = MigrationExecutor(connection)
    try:
        executor.migrate(migrate_from)
        old_apps = executor.loader.project_state(migrate_from).apps
        OldState = old_apps.get_model("playback", "BackgroundAudioState")
        state = OldState.objects.create(
            pending_command="pause",
            command_args={"reason": "legacy"},
        )

        executor = MigrationExecutor(connection)
        executor.migrate(migrate_to)
        new_apps = executor.loader.project_state(migrate_to).apps
        CommandRecord = new_apps.get_model("playback", "BackgroundAudioCommandRecord")
        record = CommandRecord.objects.get(state_id=state.pk)
        assert record.command == "pause"
        assert record.command_args == {"reason": "legacy"}
        assert record.status == "pending"
    finally:
        final_executor = MigrationExecutor(connection)
        final_executor.migrate(final_executor.loader.graph.leaf_nodes())
