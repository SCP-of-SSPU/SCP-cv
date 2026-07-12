#!/user/bin/env python
# -*- coding: UTF-8 -*-
"""
run_player 的 PowerPoint Broker 生命周期管理。
集中既有 Broker 连接、独立 Broker 所有权和退出升级逻辑，管理命令只提供进程创建缝隙。
@Project : SCP-cv
@File : run_player_ppt_broker.py
@Author : Qintsg
@Date : 2026-07-11
"""

from __future__ import annotations

import subprocess

from django.core.management.base import CommandError


class RunPlayerPptBrokerLifecycle:
    """封装 run_player 所依赖的 PowerPoint Broker 完整生命周期。"""

    _ppt_broker_client: object | None
    _owned_ppt_broker_process: object | None

    def _spawn_ppt_broker_process(self) -> object:
        """创建独立 Broker 子进程；由管理命令提供可替换实现。"""
        raise NotImplementedError

    def _prepare_ppt_broker(self, only_window_id: int) -> None:
        """
        连接既有 PowerPoint Broker，必要时为独立播放器拉起一个实例。
        :param only_window_id: 大于 0 表示 runall/父播放器管理的独立窗口进程
        :return: None
        """
        if only_window_id > 0:
            from scp_cv.player.ppt_broker import PptBrokerClient, wait_for_broker

            try:
                broker_health = wait_for_broker(timeout_seconds=5.0)
            except TimeoutError as readiness_error:
                raise CommandError(
                    f"--only-window {only_window_id} 无法连接 PowerPoint Broker；"
                    "请先运行 manage.py run_ppt_broker。"
                ) from readiness_error
            self.stdout.write(  # type: ignore[attr-defined]
                self.style.SUCCESS(  # type: ignore[attr-defined]
                    "PowerPoint Broker 已连接"
                    f"（pid={broker_health.pid}, generation={broker_health.generation}）"
                )
            )
            self._ppt_broker_client = PptBrokerClient()
            return

        from scp_cv.player.ppt_broker import connect_or_start

        broker_client = connect_or_start(
            start=self._spawn_ppt_broker_process,
            timeout_seconds=15.0,
        )
        self._ppt_broker_client = broker_client
        self._owned_ppt_broker_process = getattr(
            broker_client,
            "started_process",
            None,
        )

    def _cleanup_owned_ppt_broker(self) -> None:
        """
        关闭当前 run_player 自己拉起的 Broker；复用实例不受影响。
        :return: None
        """
        broker_client = self._ppt_broker_client
        broker_process = self._owned_ppt_broker_process
        self._ppt_broker_client = None
        self._owned_ppt_broker_process = None
        if broker_process is None:
            return

        try:
            shutdown = getattr(broker_client, "shutdown", None)
            if callable(shutdown):
                shutdown()
        except Exception as shutdown_error:
            self.stdout.write(  # type: ignore[attr-defined]
                self.style.WARNING(  # type: ignore[attr-defined]
                    f"PowerPoint Broker 优雅关闭失败：{shutdown_error}"
                )
            )

        poll = getattr(broker_process, "poll")
        if poll() is not None:
            return
        try:
            broker_process.wait(timeout=5)
            return
        except subprocess.TimeoutExpired:
            broker_process.terminate()
        try:
            broker_process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            broker_process.kill()
            broker_process.wait(timeout=3)
