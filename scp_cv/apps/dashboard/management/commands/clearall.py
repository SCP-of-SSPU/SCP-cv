#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
Django 管理命令：清除运行时数据并重建数据库。
@Project : SCP-cv
@File : clearall.py
@Author : Qintsg
@Date : 2026-05-27
'''
from __future__ import annotations

from pathlib import Path
import logging
import shutil

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import connections

from scp_cv.bootstrap_config import create_default_admin_from_config


SQLITE_SIDECAR_SUFFIXES = ("-journal", "-wal", "-shm")


class Command(BaseCommand):
    """清除本机运行时数据，重新创建 SQLite 数据库。"""

    help = "清除数据库、media 和 logs 运行时数据，并按 config.toml 重建固定数据"

    def handle(self, **options: object) -> None:
        """
        执行清除和重建流程。
        :param options: Django 管理命令参数
        :return: None
        """
        database_path = _sqlite_database_path()
        database_paths = _sqlite_database_paths(database_path)
        media_root = Path(settings.MEDIA_ROOT)
        log_root = Path(settings.LOG_DIR)
        app_log_dir = Path(getattr(settings, "APP_LOG_DIR", log_root / "app"))
        verbosity = int(options.get("verbosity", 1) or 0)

        self.stdout.write(self.style.WARNING("clearall 将删除数据库、media/ 和 logs/ 运行时数据"))
        connections.close_all()
        logging.shutdown()

        deleted_database_count = _delete_existing_files(database_paths)
        deleted_media_count = _clear_directory(media_root, preserve_names=frozenset())
        deleted_log_count = _clear_directory(log_root, preserve_names=frozenset({".gitkeep"}))
        _ensure_runtime_directories(media_root, log_root, app_log_dir)

        call_command("migrate", interactive=False, verbosity=verbosity)
        create_default_admin_from_config(get_user_model())

        self.stdout.write(
            self.style.SUCCESS(
                "clearall 完成："
                f"删除数据库文件 {deleted_database_count} 个，"
                f"清除 media 项 {deleted_media_count} 个，"
                f"清除 logs 项 {deleted_log_count} 个，并已重建数据库"
            )
        )


def _sqlite_database_path() -> Path:
    """
    返回默认 SQLite 数据库路径，非 SQLite 配置直接拒绝执行。
    :return: SQLite 数据库路径
    """
    database_config = settings.DATABASES.get("default", {})
    engine = str(database_config.get("ENGINE", ""))
    if engine != "django.db.backends.sqlite3":
        raise CommandError("clearall 仅支持当前项目默认的 SQLite 数据库")
    database_name = database_config.get("NAME")
    if not database_name:
        raise CommandError("未配置默认 SQLite 数据库路径")
    return Path(database_name)


def _sqlite_database_paths(database_path: Path) -> list[Path]:
    """
    返回 SQLite 主数据库和附属 journal/WAL/SHM 文件路径。
    :param database_path: SQLite 主数据库路径
    :return: 待删除数据库文件路径列表
    """
    return [database_path, *(Path(f"{database_path}{suffix}") for suffix in SQLITE_SIDECAR_SUFFIXES)]


def _delete_existing_files(paths: list[Path]) -> int:
    """
    删除存在的文件。
    :param paths: 待删除路径列表
    :return: 实际删除的文件数量
    """
    deleted_count = 0
    for path in paths:
        if not path.exists():
            continue
        if not path.is_file():
            raise CommandError(f"数据库路径不是文件：{path}")
        try:
            path.unlink()
        except OSError as unlink_error:
            raise CommandError(f"删除数据库文件失败，请先停止正在运行的服务：{path}") from unlink_error
        deleted_count += 1
    return deleted_count


def _clear_directory(directory: Path, preserve_names: frozenset[str]) -> int:
    """
    清空目录下全部子项，可按文件名保留少量占位文件。
    :param directory: 待清空目录
    :param preserve_names: 需要保留的直接子项名称集合
    :return: 实际删除的子项数量
    """
    if not directory.exists():
        directory.mkdir(parents=True, exist_ok=True)
        return 0
    if not directory.is_dir():
        raise CommandError(f"运行时路径不是目录：{directory}")

    deleted_count = 0
    for child in directory.iterdir():
        if child.name in preserve_names:
            continue
        try:
            if child.is_dir() and not child.is_symlink():
                shutil.rmtree(child)
            else:
                child.unlink()
        except OSError as remove_error:
            raise CommandError(f"删除运行时文件失败，请先停止正在运行的服务：{child}") from remove_error
        deleted_count += 1
    return deleted_count


def _ensure_runtime_directories(media_root: Path, log_root: Path, app_log_dir: Path) -> None:
    """
    重新创建运行时目录结构和日志占位文件。
    :param media_root: 媒体目录
    :param log_root: 日志根目录
    :param app_log_dir: Django 应用日志目录
    :return: None
    """
    media_root.mkdir(parents=True, exist_ok=True)
    log_root.mkdir(parents=True, exist_ok=True)
    app_log_dir.mkdir(parents=True, exist_ok=True)
    (log_root / ".gitkeep").touch(exist_ok=True)
