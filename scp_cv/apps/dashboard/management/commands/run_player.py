#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
Django 管理命令：启动 PySide6 多窗口播放器。
先显示启动器 GUI 供用户逐个选择 4 个输出窗口的目标屏幕，
选择完成后创建播放窗口并启动轮询。
@Project : SCP-cv
@File : run_player.py
@Author : Qintsg
@Date : 2026-04-14
'''
from __future__ import annotations

import sys

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "启动 PySide6 多窗口本地播放器"

    def add_arguments(self, parser: object) -> None:
        """
        添加命令行参数。
        :param parser: ArgumentParser 实例
        """
        parser.add_argument(
            "--dev",
            action="store_true",
            default=False,
            help="开发模式：播放窗口显示标题栏，不全屏",
        )
        parser.add_argument(
            "--poll-interval",
            type=float,
            default=0.5,
            help="轮询会话状态的间隔秒数（默认 0.5）",
        )

    def handle(self, **options: object) -> None:
        """
        入口：配置日志 → 显示启动器 GUI → 创建播放窗口。
        :param options: 命令行参数字典
        """
        import logging
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
            datefmt="%H:%M:%S",
        )

        from PySide6.QtWidgets import QApplication

        dev_mode = bool(options.get("dev", False)) or settings.DEBUG
        poll_interval = float(options.get("poll_interval", 0.5))

        self.stdout.write(self.style.SUCCESS(
            f"启动播放器（dev={dev_mode}, poll={poll_interval}s）"
        ))

        # 创建 Qt 应用
        qt_app = QApplication.instance()
        if qt_app is None:
            qt_app = QApplication(sys.argv)

        # 显示启动器 GUI，等待用户选择屏幕分配
        from scp_cv.player.launcher_gui import LauncherResult, LauncherWindow

        launcher_result_holder: list[LauncherResult] = []

        def on_launch_requested(launch_result: LauncherResult) -> None:
            """
            启动器回调：保存选择结果。
            :param launch_result: 用户选择的窗口→屏幕分配
            """
            launcher_result_holder.append(launch_result)

        launcher = LauncherWindow(debug_mode=dev_mode)
        launcher.launch_requested.connect(on_launch_requested)
        launcher.show()

        # 运行事件循环（启动器关闭后返回）
        qt_app.exec()

        # 检查用户是否完成了选择
        if not launcher_result_holder:
            self.stdout.write(self.style.WARNING("用户未完成选择，退出"))
            sys.exit(0)

        launch_result = launcher_result_holder[0]
        assigned_count = len(launch_result.window_assignments)
        self.stdout.write(self.style.SUCCESS(
            f"用户分配了 {assigned_count} 个播放窗口"
        ))

        # ═══ 根据分配结果创建播放窗口 ═══
        self._start_player(qt_app, launch_result, dev_mode, poll_interval)

    def _start_player(
        self,
        qt_app: object,
        launch_result: object,
        dev_mode: bool,
        poll_interval: float,
    ) -> None:
        """
        根据启动器结果创建多个播放窗口并启动事件循环。
        :param qt_app: QApplication 实例
        :param launch_result: LauncherResult
        :param dev_mode: 是否开发模式
        :param poll_interval: 轮询间隔
        """
        from PySide6.QtCore import QRect

        from scp_cv.player.controller import PlayerController
        from scp_cv.player.launcher_gui import LauncherResult
        from scp_cv.player.window import PlayerWindow
        from scp_cv.services.playback import get_or_create_session

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
                f"窗口 {window_id} → {display_target.name} "
                f"({display_target.geometry_label})"
            ))

        # 启动轮询
        controller.start_polling(interval_seconds=poll_interval)

        # 任意窗口关闭时退出应用（仅非 dev 模式）
        if not dev_mode:
            for player_window in all_windows:
                player_window.window_closed.connect(qt_app.quit)

        # dev 模式下额外处理：调整窗口尺寸显示
        if dev_mode:
            for player_window in all_windows:
                player_window.resize(960, 540)
                player_window.show()

        self.stdout.write(self.style.SUCCESS(
            f"播放器已启动（{len(all_windows)} 窗口），等待播放指令…"
        ))

        # 进入 Qt 事件循环
        exit_code = qt_app.exec()

        # 停止轮询
        controller.stop_polling()

        self.stdout.write(self.style.SUCCESS("播放器窗口已关闭"))
        sys.exit(exit_code)
