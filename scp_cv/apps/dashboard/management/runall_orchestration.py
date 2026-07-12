#!/user/bin/env python
# -*- coding: UTF-8 -*-
"""
runall 受管进程与 PowerPoint Broker 编排。
集中子进程登记、健康监控和反序清理，管理命令只负责解析启动方案。
@Project : SCP-cv
@File : runall_orchestration.py
@Author : Qintsg
@Date : 2026-07-11
"""

from __future__ import annotations

import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from django.conf import settings
from psutil import Error as PsutilError

from scp_cv.player.ppt_broker.contracts import BrokerHealth


@dataclass
class ManagedProcess:
    """被 runall 编排的子进程记录。"""

    name: str
    process: subprocess.Popen[bytes]
    required: bool = True
    log_handle: BinaryIO | None = None


class RunallProcessOrchestration:
    """封装 runall 子进程与 PowerPoint Broker 的完整生命周期。"""

    _processes: list[ManagedProcess]
    _process_log_dir: Path
    _shutting_down: bool
    _request_shutdown_reason: str
    _ppt_broker_client: object | None
    _ppt_broker_health: BrokerHealth | None

    def _start_player(
        self,
        poll_interval: float,
        headless: bool = False,
        window_assignments: dict[int, int] | None = None,
        gpu_id: int = -1,
    ) -> None:
        """
        启动 PySide 播放器子进程，避免 Qt 主循环阻塞 runall 监控。
        :param poll_interval: 轮询间隔秒数
        :param headless: 是否跳过播放器启动器
        :param window_assignments: 窗口编号到显示器 ID 的显式映射
        :param gpu_id: GPU ID；小于 0 表示使用系统默认 GPU
        :return: None
        """
        if headless:
            self._start_headless_player_processes(
                poll_interval,
                window_assignments or {},
                gpu_id,
            )
            return
        player_command = [
            sys.executable,
            "manage.py",
            "run_player",
            "--poll-interval",
            str(poll_interval),
        ]
        if settings.DEBUG:
            player_command.append("--dev")
        self._spawn("PySide 播放器", player_command, required=True)

    def _start_headless_player_processes(
        self,
        poll_interval: float,
        window_assignments: dict[int, int],
        gpu_id: int = -1,
    ) -> None:
        """
        为每个输出窗口启动独立播放器进程，隔离各窗口的 Qt/渲染生命周期。
        :param poll_interval: 轮询间隔秒数
        :param window_assignments: 窗口编号到显示器 ID 的显式映射
        :param gpu_id: GPU ID；小于 0 表示使用系统默认 GPU
        :return: None
        """
        target_window_ids = sorted(window_assignments.keys() or [1, 2, 3, 4])
        background_audio_owner = target_window_ids[0] if target_window_ids else 1
        for window_id in target_window_ids:
            player_command = [
                sys.executable,
                "manage.py",
                "run_player",
                "--poll-interval",
                str(poll_interval),
                "--headless",
                "--only-window",
                str(window_id),
            ]
            if settings.DEBUG:
                player_command.append("--dev")
            display_id = int(window_assignments.get(window_id, 0) or 0)
            if display_id > 0:
                player_command.extend([f"--window{window_id}", str(display_id)])
            if gpu_id >= 0:
                player_command.extend(["--gpu", str(gpu_id)])
            if window_id != background_audio_owner:
                player_command.append("--disable-background-audio")
            self._spawn(f"PySide 播放器 {window_id}", player_command, required=True)

    def _start_ppt_broker(self) -> None:
        """
        在播放器之前启动唯一 PowerPoint Broker。
        :return: None
        """
        self._spawn(
            "PowerPoint Broker",
            [sys.executable, "manage.py", "run_ppt_broker"],
            required=True,
        )

    def _prepare_ppt_broker(self) -> BrokerHealth:
        """
        复用当前 Windows Session 中的健康 Broker，否则启动并等待自有实例。
        :return: BrokerHealth 普通数据快照
        """
        from scp_cv.player.ppt_broker import PptBrokerClient

        try:
            client = PptBrokerClient(timeout_seconds=0.5)
        except (OSError, RuntimeError) as configuration_error:
            self.stderr.write(
                self.style.ERROR(
                    f"PowerPoint Broker 启动失败：{configuration_error}"
                )
            )
            self._cleanup_processes()
            sys.exit(1)

        try:
            broker_health = client.health()
        except Exception:
            broker_health = None
        if broker_health is not None and broker_health.ready:
            client.timeout_seconds = 2.0
            self._ppt_broker_client = client
            self._ppt_broker_health = broker_health
            self.stdout.write(
                self.style.SUCCESS(
                    "复用已有 PowerPoint Broker"
                    f"（pid={broker_health.pid}, generation={broker_health.generation}）"
                )
            )
            return broker_health

        self._start_ppt_broker()
        broker_health = self._wait_for_ppt_broker()
        client.timeout_seconds = 2.0
        self._ppt_broker_client = client
        self._ppt_broker_health = broker_health
        return broker_health

    def _wait_for_ppt_broker(self) -> BrokerHealth:
        """
        等待 PowerPoint Broker 命名管道可用。
        :return: BrokerHealth 普通数据快照
        """
        from scp_cv.player.ppt_broker import wait_for_broker

        try:
            broker_health = wait_for_broker(timeout_seconds=15.0)
        except TimeoutError as readiness_error:
            self.stderr.write(
                self.style.ERROR(f"PowerPoint Broker 等待超时：{readiness_error}")
            )
            self._cleanup_processes()
            sys.exit(1)
        except (OSError, RuntimeError) as startup_error:
            self.stderr.write(
                self.style.ERROR(f"PowerPoint Broker 启动失败：{startup_error}")
            )
            self._cleanup_processes()
            sys.exit(1)
        self.stdout.write(
            self.style.SUCCESS(
                "PowerPoint Broker 已就绪"
                f"（pid={broker_health.pid}, generation={broker_health.generation}）"
            )
        )
        return broker_health

    def _spawn(
        self,
        name: str,
        command_args: list[str],
        cwd: Path | None = None,
        required: bool = True,
        extra_env: dict[str, str] | None = None,
        env_remove_prefixes: tuple[str, ...] = (),
    ) -> None:
        """
        启动子进程并继承控制台输出，避免 PIPE 缓冲区导致阻塞。
        :param name: 服务名称
        :param command_args: 命令参数列表
        :param cwd: 工作目录
        :param required: 是否关键服务
        :param extra_env: 追加传给子进程的环境变量
        :param env_remove_prefixes: 传递前从父进程环境移除的变量名前缀
        :return: None
        """
        log_handle: BinaryIO | None = None
        try:
            log_handle = self._open_runall_process_log(self._process_log_dir, name)
            process = self._spawn_runall_process(
                command_args,
                log_handle=log_handle,
                cwd=cwd,
                extra_env=extra_env,
                env_remove_prefixes=env_remove_prefixes,
            )
        except OSError as start_error:
            if log_handle is not None:
                log_handle.close()
            message = f"{name} 启动失败：{start_error}"
            if required:
                self.stderr.write(self.style.ERROR(message))
                self._cleanup_processes()
                sys.exit(1)
            self.stderr.write(self.style.WARNING(message))
            return
        self._processes.append(
            ManagedProcess(
                name=name, process=process, required=required, log_handle=log_handle
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"{name} 已启动（pid={process.pid}，日志={log_handle.name}）"
            )
        )

    def _wait_for_port(self, name: str, host: str, port: int, required: bool) -> None:
        """
        轮询端口可连接状态，用于启动健康检查。
        :param name: 服务名称
        :param host: 主机
        :param port: 端口
        :param required: 是否关键服务
        :return: None
        """
        if self._wait_for_runall_port(host, port):
            self.stdout.write(self.style.SUCCESS(f"{name} 端口已就绪：{host}:{port}"))
            return
        message = f"{name} 端口等待超时：{host}:{port}"
        if required:
            self.stderr.write(self.style.ERROR(message))
            self._cleanup_processes()
            sys.exit(1)
        self.stderr.write(self.style.WARNING(message))

    def _monitor_processes(self) -> None:
        """监控关键子进程，任一关键进程退出时清理所有服务。"""
        try:
            while not self._shutting_down:
                shutdown_reason = self._consume_shutdown_request()
                if shutdown_reason:
                    self.stdout.write(self.style.WARNING(shutdown_reason))
                    self._request_shutdown_reason = shutdown_reason
                    self._cleanup_processes()
                    return
                if not self._ppt_broker_is_healthy():
                    self.stdout.write(
                        self.style.WARNING(
                            "PowerPoint Broker 已断开或被替换，按关键进程退出处理"
                        )
                    )
                    self._cleanup_processes()
                    return
                for managed_process in list(self._processes):
                    exit_code = managed_process.process.poll()
                    if exit_code is None:
                        continue
                    self.stdout.write(
                        self.style.WARNING(
                            f"{managed_process.name} 已退出（pid={managed_process.process.pid}, code={exit_code}）"
                        )
                    )
                    if managed_process.log_handle is not None:
                        managed_process.log_handle.close()
                    self._processes.remove(managed_process)
                    if managed_process.required:
                        self._cleanup_processes()
                        return
                time.sleep(0.5)
        except KeyboardInterrupt:
            self._cleanup_processes()

    def _cleanup_processes(self) -> None:
        """按启动反序终止所有仍在运行的子进程。"""
        if self._shutting_down:
            return
        self._shutting_down = True
        for managed_process in reversed(self._processes):
            process = managed_process.process
            if process.poll() is not None:
                continue
            try:
                self.stdout.write(
                    f"正在停止 {managed_process.name}（pid={process.pid}）…"
                )
                if managed_process.name == "PowerPoint Broker":
                    self._stop_ppt_broker(managed_process)
                else:
                    self._terminate_runall_process_tree(process.pid)
                self.stdout.write(self.style.SUCCESS(f"{managed_process.name} 已停止"))
            except PsutilError as process_error:
                self.stdout.write(
                    self.style.WARNING(
                        f"{managed_process.name} 停止异常：{process_error}"
                    )
                )
            finally:
                if managed_process.log_handle is not None:
                    managed_process.log_handle.close()
        self._processes.clear()
        self._ppt_broker_client = None
        self._ppt_broker_health = None

    def _ppt_broker_is_healthy(self) -> bool:
        """确认当前关键 Broker 仍是启动/复用时的同一代实例。"""
        client = self._ppt_broker_client
        expected = self._ppt_broker_health
        if client is None or expected is None:
            return True
        try:
            current = client.health()  # type: ignore[attr-defined]
        except Exception:
            return False
        return bool(
            current.ready
            and current.pid == expected.pid
            and current.generation == expected.generation
        )

    def _stop_ppt_broker(self, managed_process: ManagedProcess) -> None:
        """
        先请求 Broker 在 STA 中释放会话和自有 PowerPoint，再停止 Broker 进程。

        Broker 进程不得走递归进程树清理；若优雅退出失败，只终止当前
        ``Popen`` 持有的 Python 进程句柄，无法确认归属的 POWERPNT.EXE 保留。
        :param managed_process: runall 启动的 Broker 子进程
        :return: None
        """
        from scp_cv.player.ppt_broker import PptBrokerClient

        process = managed_process.process
        try:
            PptBrokerClient(timeout_seconds=15.0).shutdown()
        except Exception as shutdown_error:
            self.stdout.write(
                self.style.WARNING(
                    "PowerPoint Broker 优雅关闭请求失败；"
                    "将仅停止 Broker 进程并保留无法确认归属的 PowerPoint："
                    f"{shutdown_error}"
                )
            )

        if process.poll() is not None:
            return
        try:
            process.wait(timeout=15)
            return
        except subprocess.TimeoutExpired:
            self.stdout.write(
                self.style.WARNING(
                    "PowerPoint Broker 未在 15 秒内退出；"
                    "仅终止 Broker 进程，PowerPoint 将按安全策略保留"
                )
            )

        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=3)
