#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
Django 管理命令：按媒体源 ID 运行 PowerPoint 四窗口并发物理冒烟。
@Project : SCP-cv
@File : ppt_smoke.py
@Author : Qintsg
@Date : 2026-07-11
'''
from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from scp_cv.apps.dashboard.management import ppt_smoke_runtime
from scp_cv.apps.playback.models import MediaSource, SourceType
from scp_cv.services.ppt_physical_smoke import (
    DEFAULT_PPT_SMOKE_ITERATIONS,
    PptPhysicalSmokeError,
    run_ppt_concurrency_smoke_test,
)
from scp_cv.services.ppt_physical_smoke_validation import normalize_iterations


class Command(BaseCommand):
    """通过已登记 PPT 媒体源执行四窗口 Broker 冒烟。"""

    help = "按 PPT 媒体源 ID 运行四窗口并发打开、翻页、关闭和重开冒烟"

    def add_arguments(self, parser: object) -> None:
        """添加窗口、媒体源、轮数和 Broker 调用超时。"""
        parser.add_argument(
            "--windows",
            default="1,2,3,4",
            help="逗号分隔的窗口编号；并发 PPT 冒烟必须完整指定 1,2,3,4",
        )
        parser.add_argument(
            "--source-ids",
            required=True,
            help="一个 PPT source id（四窗复用）或按窗口顺序给出四个逗号分隔 ID",
        )
        parser.add_argument(
            "--iterations",
            type=int,
            default=DEFAULT_PPT_SMOKE_ITERATIONS,
            help=f"重复轮数（默认 {DEFAULT_PPT_SMOKE_ITERATIONS}，有效范围 1-10）",
        )
        parser.add_argument(
            "--timeout",
            type=float,
            default=120.0,
            help="单次 Broker 调用超时秒数（默认 120）",
        )

    def handle(self, **options: object) -> None:
        """解析媒体源并在临时原生宿主窗口中执行冒烟。"""
        windows = _parse_windows(str(options.get("windows", "")))
        source_ids = _parse_source_ids(
            str(options.get("source_ids", "")),
            window_count=len(windows),
        )
        timeout_seconds = float(options.get("timeout", 120.0))
        if timeout_seconds <= 0:
            raise CommandError("--timeout 必须大于 0")
        try:
            iterations = normalize_iterations(
                int(options.get("iterations", DEFAULT_PPT_SMOKE_ITERATIONS))
            )
        except PptPhysicalSmokeError as iteration_error:
            raise CommandError(str(iteration_error)) from iteration_error
        ppt_paths = _resolve_ppt_paths(windows, source_ids)
        assigned_ids = source_ids * len(windows) if len(source_ids) == 1 else source_ids
        source_id_map = dict(zip(windows, assigned_ids, strict=True))
        try:
            broker = ppt_smoke_runtime.connect_ppt_broker(timeout_seconds)
        except Exception as connect_error:
            raise CommandError(
                "无法连接 PowerPoint Broker；请先启动 runall 或运行 "
                "`uv run python manage.py run_ppt_broker`。"
                f"原始错误：{connect_error}"
            ) from connect_error

        self.stdout.write(
            self.style.WARNING(
                "并发 PPT 物理冒烟将替换 Broker 中窗口 1-4 的现有 PPT 会话；"
                "请勿在现场播放期间执行。"
            )
        )
        try:
            result = ppt_smoke_runtime.run_with_temporary_ppt_hosts(
                lambda parent_hwnds: run_ppt_concurrency_smoke_test(
                    broker,
                    ppt_paths,
                    parent_hwnds,
                    iterations=iterations,
                    source_ids=source_id_map,
                )
            )
        except CommandError:
            raise
        except PptPhysicalSmokeError as smoke_error:
            raise CommandError(str(smoke_error)) from smoke_error

        self.stdout.write(json.dumps(result, ensure_ascii=False, indent=2))
        if not bool(result.get("success", False)):
            failed_round = next(
                (
                    item
                    for item in result.get("rounds", [])
                    if isinstance(item, dict) and item.get("status") != "ok"
                ),
                {},
            )
            raise CommandError(
                "并发 PPT 物理冒烟失败"
                f"（第 {failed_round.get('iteration', '未知')} 轮）："
                f"{failed_round.get('error_message', '未知错误')}"
            )
        self.stdout.write(
            self.style.SUCCESS(
                "并发 PPT 物理冒烟通过："
                f"{result.get('iterations_completed', 0)}/"
                f"{result.get('iterations_requested', iterations)} 轮"
            )
        )


def _parse_windows(value: str) -> tuple[int, ...]:
    """解析并要求窗口集合恰为 1-4。"""
    try:
        windows = tuple(int(item.strip()) for item in value.split(",") if item.strip())
    except ValueError as parse_error:
        raise CommandError("--windows 必须是逗号分隔的整数窗口编号") from parse_error
    if windows != (1, 2, 3, 4):
        raise CommandError("--windows 必须按顺序完整指定 1,2,3,4")
    return windows


def _parse_source_ids(value: str, *, window_count: int) -> tuple[int, ...]:
    """解析一个共享 ID 或与窗口等长的正整数 ID 列表。"""
    items = [item.strip() for item in value.split(",")]
    if any(not item for item in items):
        raise CommandError("--source-ids 不能包含空项")
    try:
        source_ids = tuple(int(item) for item in items)
    except ValueError as parse_error:
        raise CommandError("--source-ids 必须是逗号分隔的整数媒体源 ID") from parse_error
    if not source_ids or any(source_id <= 0 for source_id in source_ids):
        raise CommandError("--source-ids 必须包含正整数媒体源 ID")
    if len(source_ids) not in {1, window_count}:
        raise CommandError(
            "--source-ids 必须提供一个四窗共用 ID，或按 --windows 顺序提供四个 ID"
        )
    return source_ids


def _resolve_ppt_paths(
    windows: tuple[int, ...],
    source_ids: tuple[int, ...],
) -> dict[int, Path]:
    """校验媒体源存在、可用且为 PPT，并返回逐窗绝对路径。"""
    assigned_ids = source_ids * len(windows) if len(source_ids) == 1 else source_ids
    sources = MediaSource.objects.in_bulk(set(assigned_ids))
    missing = sorted(set(assigned_ids) - set(sources))
    if missing:
        raise CommandError(f"找不到 PPT 媒体源 ID：{missing}")
    invalid_types = sorted(
        source_id
        for source_id in set(assigned_ids)
        if sources[source_id].source_type != SourceType.PPT
    )
    if invalid_types:
        raise CommandError(f"以下媒体源不是 PPT 类型：{invalid_types}")
    unavailable = sorted(
        source_id
        for source_id in set(assigned_ids)
        if not sources[source_id].is_available
    )
    if unavailable:
        raise CommandError(f"以下 PPT 媒体源当前不可用：{unavailable}")
    resolved_paths: dict[int, Path] = {}
    for window_id, source_id in zip(windows, assigned_ids, strict=True):
        resolved_path = Path(sources[source_id].uri).expanduser().resolve()
        if not resolved_path.is_file():
            raise CommandError(
                f"PPT 媒体源 {source_id} 的文件不存在：{resolved_path}"
            )
        resolved_paths[window_id] = resolved_path
    return resolved_paths


__all__ = ["Command"]
