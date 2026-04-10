#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
Django 管理命令：启动本地 PySide6 播放器窗口。
可与 runserver 同时运行，播放器通过轮询数据库同步会话状态。
@Project : SCP-cv
@File : run_player.py
@Author : Qintsg
@Date : 2026-04-10
'''
from __future__ import annotations

import sys

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "启动 PySide6 本地播放器窗口"

    def add_arguments(self, parser: object) -> None:
        """
        添加命令行参数。
        :param parser: ArgumentParser 实例
        """
        parser.add_argument(
            "--debug-window",
            action="store_true",
            default=False,
            help="以 DEBUG 窗口模式启动（不全屏、不置顶）",
        )
        parser.add_argument(
            "--poll-interval",
            type=float,
            default=0.5,
            help="轮询会话状态的间隔秒数（默认 0.5）",
        )

    def handle(self, **options: object) -> None:
        """
        启动 Qt 应用和播放器窗口。
        :param options: 命令行参数字典
        """
        from PySide6.QtWidgets import QApplication

        from scp_cv.player.controller import PlayerController
        from scp_cv.player.window import PlayerWindow

        # 是否使用 DEBUG 窗口模式
        debug_window = bool(options.get("debug_window", False)) or settings.DEBUG
        poll_interval = float(options.get("poll_interval", 0.5))

        self.stdout.write(self.style.SUCCESS(
            f"启动播放器窗口（debug={debug_window}, poll={poll_interval}s）"
        ))

        # 创建 Qt 应用
        qt_app = QApplication.instance()
        if qt_app is None:
            qt_app = QApplication(sys.argv)

        # 创建播放器窗口
        player_window = PlayerWindow(debug_mode=debug_window)

        # 创建控制器并绑定
        controller = PlayerController()
        controller.bind_window(player_window)

        # 根据当前会话定位窗口
        controller.apply_display_position()

        # 启动轮询
        controller.start_polling(interval_seconds=poll_interval)

        # 窗口关闭时退出事件循环
        player_window.window_closed.connect(qt_app.quit)

        # 显示窗口
        if debug_window:
            player_window.resize(1280, 720)
            player_window.show()
        else:
            player_window.showFullScreen()

        self.stdout.write(self.style.SUCCESS("播放器窗口已启动，等待播放指令…"))

        # 进入 Qt 事件循环
        exit_code = qt_app.exec()

        # 停止轮询
        controller.stop_polling()

        self.stdout.write(self.style.SUCCESS("播放器窗口已关闭"))
        sys.exit(exit_code)
