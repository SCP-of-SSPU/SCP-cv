#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
Django 管理命令：一键启动所有服务（MediaMTX + Django + PySide 播放器）。
在单个终端中同时运行 MediaMTX 流媒体服务，Django HTTP/gRPC 开发服务器，
以及 PySide6 本地播放器。退出播放器时自动停止所有子进程。
@Project : SCP-cv
@File : runall.py
@Author : Qintsg
@Date : 2026-04-14
'''
from __future__ import annotations

import atexit
import signal
import subprocess
import sys
import time
from typing import Optional

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "一键启动所有服务：MediaMTX + gRPC-Web Proxy + Django 开发服务器 + PySide6 播放器"

    # 子进程引用，供清理时使用
    _mediamtx_proc: Optional[subprocess.Popen[bytes]] = None
    _grpcweb_proxy_proc: Optional[subprocess.Popen[bytes]] = None
    _django_proc: Optional[subprocess.Popen[bytes]] = None

    def add_arguments(self, parser: object) -> None:
        """
        添加命令行参数。
        :param parser: ArgumentParser 实例
        """
        parser.add_argument(
            "--host",
            type=str,
            default="127.0.0.1",
            help="Django 开发服务器监听地址（默认 127.0.0.1）",
        )
        parser.add_argument(
            "--port",
            type=int,
            default=8000,
            help="Django 开发服务器监听端口（默认 8000）",
        )
        parser.add_argument(
            "--grpc-web-port",
            type=int,
            default=8081,
            help="gRPC-Web 代理监听端口（默认 8081）",
        )
        parser.add_argument(
            "--poll-interval",
            type=float,
            default=0.5,
            help="播放器轮询会话状态的间隔秒数（默认 0.5）",
        )
        parser.add_argument(
            "--skip-mediamtx",
            action="store_true",
            default=False,
            help="跳过 MediaMTX 启动（已在外部运行时使用）",
        )
        parser.add_argument(
            "--skip-grpcweb",
            action="store_true",
            default=False,
            help="跳过 gRPC-Web 代理启动（已在外部运行时使用）",
        )

    def handle(self, **options: object) -> None:
        """
        统一入口：
        1. 启动 MediaMTX（子进程）
        2. 启动 Django runserver（子进程）
        3. 运行 PySide6 播放器（主进程/主线程，Qt 要求）
        4. 播放器退出后清理所有子进程
        :param options: 命令行参数字典
        """
        # 注册清理函数（确保异常退出时也能清理子进程）
        atexit.register(self._cleanup_subprocesses)
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        host: str = str(options.get("host", "127.0.0.1"))
        port: int = int(options.get("port", 8000))
        grpc_web_port: int = int(options.get("grpc_web_port", 8081))
        poll_interval: float = float(options.get("poll_interval", 0.5))
        skip_mediamtx: bool = bool(options.get("skip_mediamtx", False))
        skip_grpcweb: bool = bool(options.get("skip_grpcweb", False))
        dev_mode: bool = settings.DEBUG

        # ═══ 第一步：启动 MediaMTX ═══
        if not skip_mediamtx:
            self._start_mediamtx()
        else:
            self.stdout.write(self.style.WARNING("跳过 MediaMTX 启动"))

        # ═══ 第二步：启动 gRPC-Web 代理 ═══
        if not skip_grpcweb:
            self._start_grpcweb_proxy(grpc_web_port)
        else:
            self.stdout.write(self.style.WARNING("跳过 gRPC-Web 代理启动"))

        # ═══ 第三步：启动 Django 开发服务器 ═══
        self._start_django_server(host, port)

        # 等待 Django 服务器就绪
        self._wait_for_django(host, port)

        # ═══ 第三步：启动播放器 ═══
        self._run_player(dev_mode, poll_interval)

        # ═══ 播放器退出，清理全部子进程 ═══
        self._cleanup_subprocesses()

    # ─── MediaMTX 启动 ─── #

    def _start_mediamtx(self) -> None:
        """
        以子进程方式启动 MediaMTX。
        使用 services.executables 查找可执行文件路径。
        """
        from scp_cv.services.executables import get_mediamtx_executable

        mediamtx_bin = get_mediamtx_executable()
        if mediamtx_bin is None:
            self.stderr.write(self.style.WARNING(
                "未找到 MediaMTX 可执行文件，WebRTC 流服务不可用。\n"
                "可通过 MEDIAMTX_BIN_PATH 环境变量指定路径，或将 mediamtx.exe 放入 "
                "tools/third_party/mediamtx/ 目录。"
            ))
            return

        # 查找配置文件（与可执行文件同目录）
        config_path = mediamtx_bin.parent / "mediamtx.yml"
        command_args = [str(mediamtx_bin)]
        if config_path.exists():
            command_args.append(str(config_path))

        try:
            self._mediamtx_proc = subprocess.Popen(
                command_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(mediamtx_bin.parent),
            )
            self.stdout.write(self.style.SUCCESS(
                f"MediaMTX 已启动（pid={self._mediamtx_proc.pid}）"
            ))
        except OSError as start_error:
            self.stderr.write(self.style.WARNING(
                f"MediaMTX 启动失败：{start_error}"
            ))

    # ─── gRPC-Web 代理启动 ─── #

    def _start_grpcweb_proxy(self, listen_port: int) -> None:
        """
        以子进程方式启动 @grpc-web/proxy（Node.js gRPC-Web 反向代理）。
        代理将浏览器的 gRPC-Web 请求转发到本地 gRPC 服务端口。
        :param listen_port: 代理监听端口
        """
        import shutil

        grpc_port: int = getattr(settings, "GRPC_PORT", 50051)
        npx_path = shutil.which("npx")
        if npx_path is None:
            self.stderr.write(self.style.WARNING(
                "未找到 npx，gRPC-Web 代理不可用。请安装 Node.js。"
            ))
            return

        proxy_command = [
            npx_path,
            "@grpc-web/proxy",
            f"--target=http://127.0.0.1:{grpc_port}",
            f"--listen={listen_port}",
        ]

        try:
            self._grpcweb_proxy_proc = subprocess.Popen(
                proxy_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            self.stdout.write(self.style.SUCCESS(
                f"gRPC-Web 代理已启动（pid={self._grpcweb_proxy_proc.pid}，"
                f"端口={listen_port}，后端=127.0.0.1:{grpc_port}）"
            ))
        except OSError as start_error:
            self.stderr.write(self.style.WARNING(
                f"gRPC-Web 代理启动失败：{start_error}"
            ))

    # ─── Django 开发服务器启动 ─── #

    def _start_django_server(self, host: str, port: int) -> None:
        """
        以子进程方式启动 Django 开发服务器。
        使用 --noreload 避免自动重载干扰主进程。
        :param host: 监听地址
        :param port: 监听端口
        """
        django_command = [
            sys.executable,
            "manage.py",
            "runserver",
            f"{host}:{port}",
            "--noreload",
        ]
        try:
            self._django_proc = subprocess.Popen(
                django_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            self.stdout.write(self.style.SUCCESS(
                f"Django 开发服务器已启动（pid={self._django_proc.pid}，"
                f"地址={host}:{port}）"
            ))
        except OSError as start_error:
            self.stderr.write(self.style.ERROR(
                f"Django 开发服务器启动失败：{start_error}"
            ))
            self._cleanup_subprocesses()
            sys.exit(1)

    def _wait_for_django(self, host: str, port: int) -> None:
        """
        等待 Django 开发服务器就绪（最多 10 秒）。
        通过轮询 HTTP 端口检测是否可连接。
        :param host: 监听地址
        :param port: 监听端口
        """
        import socket

        # 最多等待 10 秒
        max_wait_seconds = 10
        check_interval = 0.3
        elapsed = 0.0

        self.stdout.write("等待 Django 服务器就绪…")
        while elapsed < max_wait_seconds:
            try:
                probe = socket.create_connection((host, port), timeout=1)
                probe.close()
                self.stdout.write(self.style.SUCCESS("Django 服务器已就绪"))
                return
            except (ConnectionRefusedError, OSError):
                time.sleep(check_interval)
                elapsed += check_interval

        # 超时但不终止，Django 可能还在初始化
        self.stderr.write(self.style.WARNING(
            f"等待 Django 服务器超时（{max_wait_seconds}s），继续启动播放器…"
        ))

    # ─── PySide6 播放器主流程 ─── #

    def _run_player(self, dev_mode: bool, poll_interval: float) -> None:
        """
        在主线程运行 PySide6 播放器。
        Qt 要求 QApplication 在主线程创建和运行。
        :param dev_mode: 是否开发模式（有标题栏，可移动缩放）
        :param poll_interval: 轮询间隔秒数
        """
        from PySide6.QtWidgets import QApplication

        self.stdout.write(self.style.SUCCESS(
            f"启动播放器（dev={dev_mode}, poll={poll_interval}s）"
        ))

        # 创建 Qt 应用
        qt_app = QApplication.instance()
        if qt_app is None:
            qt_app = QApplication(sys.argv)

        # 显示启动器 GUI，等待用户逐个分配窗口→屏幕
        from scp_cv.player.launcher_gui import LauncherResult, LauncherWindow

        launcher_result_holder: list[LauncherResult] = []

        def on_launch_requested(result: LauncherResult) -> None:
            """
            启动器回调：保存选择结果。
            :param result: 用户选择的窗口→屏幕分配
            """
            launcher_result_holder.append(result)

        launcher = LauncherWindow(debug_mode=dev_mode)
        launcher.launch_requested.connect(on_launch_requested)
        launcher.show()

        # 运行事件循环（启动器关闭后返回）
        qt_app.exec()

        # 检查用户是否完成了选择
        if not launcher_result_holder:
            self.stdout.write(self.style.WARNING("用户未完成选择，退出"))
            return

        launch_result = launcher_result_holder[0]
        assigned_count = len(launch_result.window_assignments)
        self.stdout.write(self.style.SUCCESS(
            f"用户分配了 {assigned_count} 个播放窗口"
        ))

        # 根据选择结果创建播放窗口
        self._start_player_windows(qt_app, launch_result, dev_mode, poll_interval)

    def _start_player_windows(
        self,
        qt_app: object,
        launch_result: object,
        dev_mode: bool,
        poll_interval: float,
    ) -> None:
        """
        根据启动器结果创建多个播放窗口并启动事件循环。
        :param qt_app: QApplication 实例
        :param launch_result: LauncherResult（包含 window_assignments）
        :param dev_mode: 是否开发模式
        :param poll_interval: 轮询间隔
        """
        from PySide6.QtCore import QRect

        from scp_cv.player.controller import PlayerController
        from scp_cv.player.launcher_gui import LauncherResult
        from scp_cv.player.window import PlayerWindow
        from scp_cv.services.playback import get_or_create_session

        # 类型断言
        result: LauncherResult = launch_result

        # 创建控制器
        controller = PlayerController()
        all_windows: list[PlayerWindow] = []

        # 逐个创建播放窗口并注册到控制器
        for window_id, display_target in sorted(result.window_assignments.items()):
            player_window = PlayerWindow(
                window_id=window_id,
                debug_mode=dev_mode,
            )
            controller.register_window(window_id, player_window)
            all_windows.append(player_window)

            # 更新数据库会话并记录目标屏幕
            session = get_or_create_session(window_id)
            session.target_display_label = display_target.name
            session.save()

            # 定位窗口到目标屏幕
            target_rect = QRect(
                display_target.x, display_target.y,
                display_target.width, display_target.height,
            )
            player_window.position_on_display(target_rect)

            self.stdout.write(self.style.SUCCESS(
                f"窗口 {window_id} → {display_target.name}"
            ))

        # 启动轮询
        controller.start_polling(interval_seconds=poll_interval)

        # 任意窗口关闭时退出
        for player_window in all_windows:
            player_window.window_closed.connect(qt_app.quit)

        # dev 模式下显示窗口（非 dev 已由 position_on_display 处理）
        if dev_mode:
            for player_window in all_windows:
                player_window.resize(960, 540)
                player_window.show()

        self.stdout.write(self.style.SUCCESS(
            f"播放器已启动（{len(all_windows)} 窗口），等待播放指令…"
        ))

        # 进入事件循环（阻塞直到用户关闭窗口）
        qt_app.exec()

        # 退出后停止轮询和管线
        controller.stop_polling()
        self.stdout.write(self.style.SUCCESS("播放器窗口已关闭"))

    # ─── 清理与信号处理 ─── #

    def _cleanup_subprocesses(self) -> None:
        """
        终止所有子进程（MediaMTX 和 Django）。
        优先发送 SIGTERM/terminate，超时则强杀。
        """
        for label, proc in [
            ("Django", self._django_proc),
            ("gRPC-Web 代理", self._grpcweb_proxy_proc),
            ("MediaMTX", self._mediamtx_proc),
        ]:
            if proc is None:
                continue
            if proc.poll() is not None:
                continue
            try:
                proc.terminate()
                proc.wait(timeout=5)
                self.stdout.write(f"{label} 已停止（pid={proc.pid}）")
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=3)
                self.stdout.write(self.style.WARNING(
                    f"{label} 超时强制终止（pid={proc.pid}）"
                ))

        self._django_proc = None
        self._grpcweb_proxy_proc = None
        self._mediamtx_proc = None

    def _signal_handler(self, signum: int, frame: object) -> None:
        """
        Ctrl+C / SIGTERM 信号处理：清理子进程后退出。
        :param signum: 信号编号
        :param frame: 栈帧（未使用）
        """
        self.stdout.write(self.style.WARNING(f"\n收到信号 {signum}，正在停止所有服务…"))
        self._cleanup_subprocesses()
        sys.exit(0)
