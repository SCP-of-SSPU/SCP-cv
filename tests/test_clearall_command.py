#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
clearall 管理命令测试。
@Project : SCP-cv
@File : test_clearall_command.py
@Author : Qintsg
@Date : 2026-05-27
'''
from __future__ import annotations

from pathlib import Path
from typing import Any

from scp_cv.apps.dashboard.management.commands import clearall


def test_clearall_rebuilds_database_and_clears_runtime_dirs(
    monkeypatch: Any, tmp_path: Path
) -> None:
    """
    clearall 应删除 SQLite 文件、清空 media/logs，并执行 migrate 后播种固定数据。
    :param monkeypatch: pytest monkeypatch fixture
    :param tmp_path: pytest 临时目录 fixture
    :return: None
    """
    database_path = tmp_path / "db.sqlite3"
    media_root = tmp_path / "media"
    log_root = tmp_path / "logs"
    app_log_dir = log_root / "app"
    migrate_calls: list[dict[str, object]] = []
    seed_calls: list[object] = []
    close_calls: list[str] = []
    shutdown_calls: list[str] = []

    for database_file in clearall._sqlite_database_paths(database_path):
        database_file.write_text("database", encoding="utf-8")
    media_root.mkdir()
    (media_root / "uploads").mkdir()
    (media_root / "uploads" / "video.mp4").write_text("video", encoding="utf-8")
    (media_root / "ppt_previews").mkdir()
    log_root.mkdir()
    (log_root / ".gitkeep").write_text("", encoding="utf-8")
    (log_root / "old.log").write_text("old", encoding="utf-8")
    (log_root / "runall").mkdir()
    (log_root / "runall" / "django.log").write_text("django", encoding="utf-8")

    def fake_call_command(command_name: str, **kwargs: object) -> None:
        """
        记录迁移调用，避免测试真实重建 pytest 数据库。
        :param command_name: 管理命令名称
        :param kwargs: 管理命令参数
        :return: None
        """
        migrate_calls.append({"command_name": command_name, **kwargs})

    fake_user_model = object()
    monkeypatch.setattr(clearall.settings, "DATABASES", {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": database_path,
        }
    })
    monkeypatch.setattr(clearall.settings, "MEDIA_ROOT", media_root)
    monkeypatch.setattr(clearall.settings, "LOG_DIR", log_root)
    monkeypatch.setattr(clearall.settings, "APP_LOG_DIR", app_log_dir)
    monkeypatch.setattr(clearall.connections, "close_all", lambda: close_calls.append("close"))
    monkeypatch.setattr(clearall.logging, "shutdown", lambda: shutdown_calls.append("shutdown"))
    monkeypatch.setattr(clearall, "call_command", fake_call_command)
    monkeypatch.setattr(clearall, "get_user_model", lambda: fake_user_model)
    monkeypatch.setattr(
        clearall,
        "create_default_admin_from_config",
        lambda user_model: seed_calls.append(user_model),
    )

    clearall.Command().handle(verbosity=0)

    assert close_calls == ["close"]
    assert shutdown_calls == ["shutdown"]
    assert all(not database_file.exists() for database_file in clearall._sqlite_database_paths(database_path))
    assert media_root.exists()
    assert list(media_root.iterdir()) == []
    assert sorted(child.name for child in log_root.iterdir()) == [".gitkeep", "app"]
    assert app_log_dir.exists()
    assert migrate_calls == [{"command_name": "migrate", "interactive": False, "verbosity": 0}]
    assert seed_calls == [fake_user_model]


def test_clear_directory_preserves_gitkeep(tmp_path: Path) -> None:
    """
    清理日志目录时应保留 .gitkeep 占位文件。
    :param tmp_path: pytest 临时目录 fixture
    :return: None
    """
    (tmp_path / ".gitkeep").write_text("", encoding="utf-8")
    (tmp_path / "old.log").write_text("old", encoding="utf-8")
    (tmp_path / "nested").mkdir()

    deleted_count = clearall._clear_directory(tmp_path, preserve_names=frozenset({".gitkeep"}))

    assert deleted_count == 2
    assert sorted(child.name for child in tmp_path.iterdir()) == [".gitkeep"]
