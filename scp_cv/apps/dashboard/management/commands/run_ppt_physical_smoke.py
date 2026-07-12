#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
Django 管理命令：运行 PowerPoint Broker 四窗口并发物理冒烟。
@Project : SCP-cv
@File : run_ppt_physical_smoke.py
@Author : Qintsg
@Date : 2026-07-11
'''
from __future__ import annotations

import argparse
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from scp_cv.apps.dashboard.management import ppt_smoke_runtime
from scp_cv.services.ppt_physical_smoke import (
    DEFAULT_PPT_SMOKE_ITERATIONS,
    PptPhysicalSmokeError,
    run_ppt_concurrency_smoke_test,
)


class Command(BaseCommand):
    """对唯一 Broker 执行三轮四窗口 PowerPoint 物理冒烟。"""

    help = "运行 PowerPoint Broker 四窗口并发打开、翻页和关闭物理冒烟"

    def add_arguments(self, parser: object) -> None:
        """添加 PPT 路径、父 HWND、轮数和 Broker 超时参数。"""
        parser.add_argument(
            "--ppt",
            required=True,
            help="至少包含五页的本地 PowerPoint 文件路径",
        )
        for window_id in range(1, 5):
            parser.add_argument(
                f"--window{window_id}-hwnd",
                type=_parse_hwnd,
                default=0,
                help=(
                    f"窗口 {window_id} 播放容器的原生 HWND；"
                    "四项全不填时创建临时宿主窗口"
                ),
            )
        parser.add_argument(
            "--iterations",
            type=int,
            default=DEFAULT_PPT_SMOKE_ITERATIONS,
            help=f"重复轮数（默认 {DEFAULT_PPT_SMOKE_ITERATIONS}，有效范围 1-10）",
        )
        parser.add_argument(
            "--broker-timeout",
            type=float,
            default=120.0,
            help="单次 Broker 调用超时秒数（默认 120）",
        )

    def handle(self, **options: object) -> None:
        """
        连接既有 Broker，执行冒烟，并以 CommandError 表达非零失败。
        :param options: Django 命令行参数
        :return: None
        """
        ppt_path = Path(str(options.get("ppt", ""))).expanduser().resolve()
        iterations = int(options.get("iterations", DEFAULT_PPT_SMOKE_ITERATIONS))
        broker_timeout = float(options.get("broker_timeout", 120.0))
        if broker_timeout <= 0:
            raise CommandError("--broker-timeout 必须大于 0")
        explicit_parents = _explicit_parent_hwnds(options)

        try:
            broker = ppt_smoke_runtime.connect_ppt_broker(broker_timeout)
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
            if explicit_parents is None:
                result = ppt_smoke_runtime.run_with_temporary_ppt_hosts(
                    lambda parent_hwnds: run_ppt_concurrency_smoke_test(
                        broker,
                        ppt_path,
                        parent_hwnds,
                        iterations=iterations,
                    )
                )
            else:
                result = run_ppt_concurrency_smoke_test(
                    broker,
                    ppt_path,
                    explicit_parents,
                    iterations=iterations,
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
            iteration = failed_round.get("iteration", "未知")
            error_message = failed_round.get("error_message", "未知错误")
            raise CommandError(
                f"并发 PPT 物理冒烟失败（第 {iteration} 轮）：{error_message}。"
                "请确认已安装 Microsoft PowerPoint、Broker 运行在交互桌面、"
                "PPT 至少五页，并检查四个父 HWND 是否仍有效。"
            )
        self.stdout.write(
            self.style.SUCCESS(
                "并发 PPT 物理冒烟通过："
                f"{result.get('iterations_completed', 0)}/"
                f"{result.get('iterations_requested', iterations)} 轮"
            )
        )


def _explicit_parent_hwnds(options: dict[str, object]) -> dict[int, int] | None:
    """解析四个可选父 HWND；禁止只提供其中一部分。"""
    parent_hwnds = {
        window_id: int(options.get(f"window{window_id}_hwnd", 0) or 0)
        for window_id in range(1, 5)
    }
    configured = [window_id for window_id, hwnd in parent_hwnds.items() if hwnd > 0]
    if not configured:
        return None
    if len(configured) != 4:
        missing = sorted(set(range(1, 5)) - set(configured))
        raise CommandError(
            "父 HWND 必须四项全部提供或全部省略；"
            f"缺少窗口：{missing}"
        )
    return parent_hwnds


def _parse_hwnd(value: str) -> int:
    """接受十进制或 0x 前缀十六进制 HWND。"""
    try:
        hwnd = int(value, 0)
    except ValueError as parse_error:
        raise argparse.ArgumentTypeError(f"无效 HWND：{value}") from parse_error
    if hwnd <= 0:
        raise argparse.ArgumentTypeError("HWND 必须大于 0")
    return hwnd


__all__ = ["Command"]
