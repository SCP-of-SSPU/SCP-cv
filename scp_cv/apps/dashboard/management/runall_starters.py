#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
runall 前端与播放器启动编排，隔离子进程参数构造。
@Project : SCP-cv
@File : runall_starters.py
@Author : Qintsg
@Date : 2026-08-23
'''
from __future__ import annotations

import shutil
import sys
from pathlib import Path

from django.conf import settings

from scp_cv.apps.dashboard.management.runall_frontend import read_frontend_env


class RunallStarterMixin:
    """封装 Vue 前端与独立播放器进程的启动参数。"""

    def _start_mediamtx(self) -> None:
        """
        启动 MediaMTX 子进程。

        :return: None
        """
        from scp_cv.services.executables import get_mediamtx_executable

        mediamtx_bin = get_mediamtx_executable()
        if mediamtx_bin is None:
            self.stderr.write(
                self.style.WARNING(
                    "未找到 MediaMTX，可使用 --skip-mediamtx 或配置 MEDIAMTX_BIN_PATH"
                )
            )
            return
        command_args = [str(mediamtx_bin)]
        config_path = mediamtx_bin.parent / "mediamtx.yml"
        if config_path.exists():
            command_args.append(str(config_path))
        self._spawn(
            "MediaMTX", command_args, cwd=mediamtx_bin.parent, required=False
        )

    def _start_django_server(self, host: str, port: int) -> None:
        """
        启动 Django HTTP 开发服务器。

        :param host: 监听地址
        :param port: 监听端口
        :return: None
        """
        self._spawn(
            "Django",
            [sys.executable, "manage.py", "runserver", f"{host}:{port}", "--noreload"],
            required=True,
        )

    def _start_frontend(
        self,
        host: str,
        port: int,
        backend_host: str,
        backend_port: int,
    ) -> None:
        """
        启动 Vue Vite 开发服务器。

        :param host: 监听地址
        :param port: 监听端口
        :param backend_host: Django 监听地址
        :param backend_port: Django 监听端口
        :return: None
        """
        pnpm_path = shutil.which("pnpm") or shutil.which("npm")
        frontend_dir = Path(settings.BASE_DIR) / "frontend"
        if pnpm_path is None or not frontend_dir.exists():
            self.stderr.write(
                self.style.WARNING("未找到 pnpm/npm 或 frontend/，跳过 Vue 前端")
            )
            return
        extra_env: dict[str, str] | None = None
        frontend_env = read_frontend_env(frontend_dir)
        configured_target = frontend_env.get("VITE_BACKEND_TARGET", "").strip()
        if not configured_target:
            from scp_cv.apps.dashboard.management.commands import runall

            backend_target_host = runall.public_host(backend_host)
            extra_env = {
                "VITE_BACKEND_TARGET": f"http://{backend_target_host}:{backend_port}"
            }
        command_args = [pnpm_path, "run", "dev", "--", "--host", host]
        if port > 0:
            command_args.extend(["--port", str(port)])
        self._frontend_options = {
            "frontend_host": host,
            "frontend_port": port,
            "backend_host": backend_host,
            "backend_port": backend_port,
        }
        self._spawn(
            "Vue 前端",
            command_args,
            cwd=frontend_dir,
            required=True,
            extra_env=extra_env,
            env_remove_prefixes=("VITE_",),
        )
        if port <= 0:
            self.stdout.write(
                self.style.WARNING(
                    "Vue 前端未追加 --port，端口以 frontend/.env / Vite 配置为准"
                )
            )
        else:
            self.stdout.write(self.style.WARNING(f"Vue 前端已显式追加 --port {port}"))

    def _start_player(
        self,
        poll_interval: float,
        headless: bool = False,
        window_assignments: dict[int, int] | None = None,
        gpu_id: int = -1,
    ) -> None:
        """
        启动 PySide 播放器子进程。

        :param poll_interval: 轮询间隔秒数
        :param headless: 是否跳过播放器启动器
        :param window_assignments: 窗口编号到显示器 ID 的显式映射
        :param gpu_id: GPU ID；小于 0 表示使用系统默认 GPU
        :return: None
        """
        if headless:
            self._start_headless_player_processes(
                poll_interval, window_assignments or {}, gpu_id
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
        为每个输出窗口启动独立播放器进程。

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
            self._spawn(
                f"PySide 播放器 {window_id}", player_command, required=True
            )
