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
