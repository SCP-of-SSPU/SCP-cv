#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
Django 管理命令：一键启动 SCP-cv 所有本地服务。
负责启动和监控 MediaMTX、gRPC-Web 代理、Django HTTP/gRPC、Vue 前端和 PySide 播放器。
@Project : SCP-cv
@File : runall.py
@Author : Qintsg
@Date : 2026-04-26
'''
from __future__ import annotations

import atexit
import os
import signal
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from django.conf import settings
from django.core.management.base import BaseCommand


@dataclass
class ManagedProcess:
    """被 runall 编排的子进程记录。"""

    name: str
    process: subprocess.Popen[bytes]
    required: bool = True
    log_handle: BinaryIO | None = None


class Command(BaseCommand):
    help = "一键启动所有服务：MediaMTX + gRPC-Web + Django + Vue 前端 + PySide6 播放器"

    def __init__(self, *args: object, **kwargs: object) -> None:
        """
        初始化管理命令状态。
        :param args: Django BaseCommand 参数
        :param kwargs: Django BaseCommand 关键字参数
        :return: None
        """
        super().__init__(*args, **kwargs)
        self._processes: list[ManagedProcess] = []
        self._shutting_down = False

    def add_arguments(self, parser: object) -> None:
        """
        添加命令行参数。
        :param parser: ArgumentParser 实例
        :return: None
        """
        parser.add_argument("--backend-host", "--host", type=str, default="0.0.0.0", help="Django 监听地址")
        parser.add_argument("--backend-port", "--port", type=int, default=8000, help="Django 监听端口")
        parser.add_argument("--frontend-host", type=str, default="0.0.0.0", help="Vue 前端监听地址")
        parser.add_argument("--frontend-port", type=int, default=5173, help="Vue 前端监听端口")
        parser.add_argument("--grpc-web-port", type=int, default=8081, help="gRPC-Web 代理监听端口")
        parser.add_argument("--poll-interval", type=float, default=0.2, help="播放器轮询间隔秒数")
        parser.add_argument("--skip-mediamtx", action="store_true", default=False, help="跳过 MediaMTX")
        parser.add_argument("--skip-grpcweb", "--skip-grpc", action="store_true", default=True, help="跳过 gRPC-Web 代理")
        parser.add_argument("--enable-grpcweb", action="store_false", dest="skip_grpcweb", help="启用 gRPC-Web 代理")
        parser.add_argument("--skip-frontend", action="store_true", default=False, help="跳过 Vue 前端")
        parser.add_argument("--skip-player", action="store_true", default=False, help="跳过 PySide 播放器")

    def handle(self, **options: object) -> None:
        """
        启动所有服务并持续监控，直到收到退出信号或关键服务退出。
        :param options: 命令行参数
        :return: None
        """
        atexit.register(self._cleanup_processes)
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        backend_host = str(options.get("backend_host", "127.0.0.1"))
        backend_port = int(options.get("backend_port", 8000))
        frontend_host = str(options.get("frontend_host", "0.0.0.0"))
        frontend_port = int(options.get("frontend_port", 5173))
        grpc_web_port = int(options.get("grpc_web_port", 8081))
        poll_interval = float(options.get("poll_interval", 0.2))

        if not bool(options.get("skip_mediamtx", False)):
            self._start_mediamtx()
        if not bool(options.get("skip_grpcweb", False)):
            self._start_grpcweb_proxy(grpc_web_port)
        self._start_django_server(backend_host, backend_port)
        if not bool(options.get("skip_frontend", False)):
            self._start_frontend(frontend_host, frontend_port, backend_host, backend_port)
        if not bool(options.get("skip_player", False)):
            self._start_player(poll_interval)

        self._wait_for_port("Django", backend_host, backend_port, required=True)
        if not bool(options.get("skip_frontend", False)):
            self._wait_for_port("Vue 前端", self._connect_host(frontend_host), frontend_port, required=False)
        if not bool(options.get("skip_grpcweb", False)):
            self._wait_for_port("gRPC-Web", "127.0.0.1", grpc_web_port, required=False)

        frontend_url_host = self._public_host(frontend_host)
        backend_url_host = self._public_host(backend_host)
        self.stdout.write(self.style.SUCCESS(
            f"服务已启动：前端 http://{frontend_url_host}:{frontend_port}/ ，后端 http://{backend_url_host}:{backend_port}/"
        ))
        self._monitor_processes()

    def _start_mediamtx(self) -> None:
        """启动 MediaMTX 子进程。"""
        from scp_cv.services.executables import get_mediamtx_executable

        mediamtx_bin = get_mediamtx_executable()
        if mediamtx_bin is None:
            self.stderr.write(self.style.WARNING("未找到 MediaMTX，可使用 --skip-mediamtx 或配置 MEDIAMTX_BIN_PATH"))
            return
        command_args = [str(mediamtx_bin)]
        config_path = mediamtx_bin.parent / "mediamtx.yml"
        if config_path.exists():
            command_args.append(str(config_path))
        self._spawn("MediaMTX", command_args, cwd=mediamtx_bin.parent, required=False)

    def _start_grpcweb_proxy(self, listen_port: int) -> None:
        """
        启动 gRPC-Web 代理，保留给旧前端和第三方浏览器客户端使用。
        :param listen_port: 监听端口
        :return: None
        """
        import shutil

        npx_path = shutil.which("npx")
        if npx_path is None:
            self.stderr.write(self.style.WARNING("未找到 npx，跳过 gRPC-Web 代理"))
            return
        grpc_port = int(getattr(settings, "GRPC_PORT", 50051))
        self._spawn(
            "gRPC-Web 代理",
            [npx_path, "@grpc-web/proxy", f"--target=http://127.0.0.1:{grpc_port}", f"--listen={listen_port}"],
            required=False,
        )

    def _start_django_server(self, host: str, port: int) -> None:
        """
        启动 Django HTTP/gRPC 开发服务器。
        :param host: 监听地址
        :param port: 监听端口
        :return: None
        """
        self._spawn(
            "Django",
            [sys.executable, "manage.py", "runserver", f"{host}:{port}", "--noreload"],
            required=True,
        )

    def _start_frontend(self, host: str, port: int, backend_host: str, backend_port: int) -> None:
        """
        启动 Vue Vite 开发服务器。
        :param host: 监听地址
        :param port: 监听端口
        :param backend_host: Django 监听地址
        :param backend_port: Django 监听端口
        :return: None
        """
        import shutil

        npm_path = shutil.which("npm")
        frontend_dir = Path(settings.BASE_DIR) / "frontend"
        if npm_path is None or not frontend_dir.exists():
            self.stderr.write(self.style.WARNING("未找到 npm 或 frontend/，跳过 Vue 前端"))
            return
        backend_target_host = self._public_host(backend_host)
        self._spawn(
            "Vue 前端",
            [npm_path, "run", "dev", "--", "--host", host, "--port", str(port)],
            cwd=frontend_dir,
            required=True,
            extra_env={"VITE_BACKEND_TARGET": f"http://{backend_target_host}:{backend_port}"},
        )

    def _start_player(self, poll_interval: float) -> None:
        """
        启动 PySide 播放器子进程，避免 Qt 主循环阻塞 runall 监控。
        :param poll_interval: 轮询间隔秒数
        :return: None
        """
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

    def _spawn(
        self,
        name: str,
        command_args: list[str],
        cwd: Path | None = None,
        required: bool = True,
        extra_env: dict[str, str] | None = None,
    ) -> None:
        """
        启动子进程并继承控制台输出，避免 PIPE 缓冲区导致阻塞。
        :param name: 服务名称
        :param command_args: 命令参数列表
        :param cwd: 工作目录
        :param required: 是否关键服务
        :param extra_env: 追加传给子进程的环境变量
        :return: None
        """
        log_handle: BinaryIO | None = None
        try:
            process_env = os.environ.copy()
            process_env.setdefault("CI", "true")
            process_env.setdefault("PYTHONUTF8", "1")
            process_env.setdefault("PYTHONIOENCODING", "utf-8")
            process_env.setdefault("npm_config_yes", "true")
            if extra_env:
                process_env.update(extra_env)
            log_handle = self._open_process_log(name)
            process = subprocess.Popen(
                command_args,
                cwd=str(cwd) if cwd else None,
                env=process_env,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
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
        self._processes.append(ManagedProcess(name=name, process=process, required=required, log_handle=log_handle))
        self.stdout.write(self.style.SUCCESS(f"{name} 已启动（pid={process.pid}，日志={log_handle.name}）"))

    def _open_process_log(self, process_name: str) -> BinaryIO:
        """
        为子进程打开独立日志文件，避免 stdout PIPE 阻塞并保留启动诊断信息。
        :param process_name: 服务名称
        :return: 二进制追加模式文件句柄
        """
        safe_name = process_name.lower().replace(" ", "-").replace("/", "-")
        log_path = Path(settings.LOG_DIR) / f"{safe_name}.log"
        return log_path.open("ab")

    def _wait_for_port(self, name: str, host: str, port: int, required: bool) -> None:
        """
        轮询端口可连接状态，用于启动健康检查。
        :param name: 服务名称
        :param host: 主机
        :param port: 端口
        :param required: 是否关键服务
        :return: None
        """
        deadline = time.time() + 20
        while time.time() < deadline:
            try:
                with socket.create_connection((host, port), timeout=1):
                    self.stdout.write(self.style.SUCCESS(f"{name} 端口已就绪：{host}:{port}"))
                    return
            except OSError:
                time.sleep(0.3)
        message = f"{name} 端口等待超时：{host}:{port}"
        if required:
            self.stderr.write(self.style.ERROR(message))
            self._cleanup_processes()
            sys.exit(1)
        self.stderr.write(self.style.WARNING(message))

    def _connect_host(self, listen_host: str) -> str:
        """
        将通配监听地址转换为本机健康检查可连接地址。
        :param listen_host: 服务监听地址
        :return: 用于 socket 连接探测的主机地址
        """
        if listen_host in {"0.0.0.0", "::"}:
            return "127.0.0.1"
        return listen_host

    def _public_host(self, listen_host: str) -> str:
        """
        将通配监听地址转换为局域网可访问地址，供浏览器和移动设备直连。
        :param listen_host: 服务监听地址
        :return: 可供客户端访问的主机地址
        """
        if listen_host not in {"0.0.0.0", "::"}:
            return listen_host
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
                udp_socket.connect(("8.8.8.8", 80))
                return str(udp_socket.getsockname()[0])
        except OSError:
            return "127.0.0.1"

    def _monitor_processes(self) -> None:
        """监控关键子进程，任一关键进程退出时清理所有服务。"""
        try:
            while not self._shutting_down:
                for managed_process in list(self._processes):
                    exit_code = managed_process.process.poll()
                    if exit_code is None:
                        continue
                    self.stdout.write(self.style.WARNING(
                        f"{managed_process.name} 已退出（pid={managed_process.process.pid}, code={exit_code}）"
                    ))
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
                self.stdout.write(f"正在停止 {managed_process.name}（pid={process.pid}）…")
                process.terminate()
                process.wait(timeout=8)
                self.stdout.write(self.style.SUCCESS(f"{managed_process.name} 已停止"))
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)
                self.stdout.write(self.style.WARNING(f"{managed_process.name} 已强制终止"))
            finally:
                if managed_process.log_handle is not None:
                    managed_process.log_handle.close()
        self._processes.clear()

    def _signal_handler(self, signum: int, _frame: object) -> None:
        """
        Ctrl+C / SIGTERM 信号处理。
        :param signum: 信号编号
        :param _frame: 当前栈帧
        :return: None
        """
        self.stdout.write(self.style.WARNING(f"收到信号 {signum}，正在停止所有服务…"))
        self._cleanup_processes()
        sys.exit(0)
