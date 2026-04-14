#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
Django 管理命令：启动 PySide6 播放器窗口。
支持单屏和多屏模式，通过轮询数据库同步会话状态。
使用 GStreamer WebRTC 管线替代 mpv 进行流播放。
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
    help = "启动 PySide6 本地播放器窗口（WebRTC + GStreamer）"

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
        根据当前会话的显示模式自动创建单窗口或多窗口。
        :param options: 命令行参数字典
        """
        # 初始化 GStreamer（必须在 Qt 之前）
        from scp_cv.player import init_gstreamer
        gst_ok = init_gstreamer()
        if not gst_ok:
            self.stderr.write(self.style.ERROR(
                "GStreamer 初始化失败。请确认已安装 GStreamer MSVC Runtime。\n"
                "下载地址：https://gstreamer.freedesktop.org/download/\n"
                "需要安装 Runtime 和 Development 两个包。"
            ))
            sys.exit(1)

        from PySide6.QtWidgets import QApplication

        from scp_cv.player.controller import PlayerController
        from scp_cv.player.window import PlayerWindow
        from scp_cv.services.playback import get_or_create_session
        from scp_cv.services.display import (
            list_display_targets,
            build_left_right_splice_target,
        )
        from scp_cv.apps.playback.models import PlaybackMode

        debug_window = bool(options.get("debug_window", False)) or settings.DEBUG
        poll_interval = float(options.get("poll_interval", 0.5))

        self.stdout.write(self.style.SUCCESS(
            f"启动播放器（debug={debug_window}, poll={poll_interval}s, engine=GStreamer+WebRTC）"
        ))

        # 创建 Qt 应用
        qt_app = QApplication.instance()
        if qt_app is None:
            qt_app = QApplication(sys.argv)

        # 创建控制器
        controller = PlayerController()

        # 根据会话显示模式决定窗口数量
        session = get_or_create_session()
        display_targets = list_display_targets()
        all_windows: list[PlayerWindow] = []

        if session.display_mode == PlaybackMode.LEFT_RIGHT_SPLICE:
            splice_target = build_left_right_splice_target(display_targets)
            if splice_target is not None:
                # 拼接模式：左右各一个窗口
                left_window = PlayerWindow(
                    window_id="left", debug_mode=debug_window,
                )
                right_window = PlayerWindow(
                    window_id="right", debug_mode=debug_window,
                )
                controller.register_window("left", left_window)
                controller.register_window("right", right_window)
                all_windows.extend([left_window, right_window])
                self.stdout.write(self.style.SUCCESS("拼接模式：创建左右两个窗口"))
            else:
                self.stdout.write(self.style.WARNING(
                    "拼接模式需要至少 2 台显示器，回退到单屏模式"
                ))
                single_window = PlayerWindow(
                    window_id="single", debug_mode=debug_window,
                )
                controller.register_window("single", single_window)
                all_windows.append(single_window)
        else:
            # 单屏模式：一个窗口
            single_window = PlayerWindow(
                window_id="single", debug_mode=debug_window,
            )
            controller.register_window("single", single_window)
            all_windows.append(single_window)

        # 定位窗口到目标显示器
        controller.apply_display_positions()

        # 启动轮询
        controller.start_polling(interval_seconds=poll_interval)

        # 任意窗口关闭时退出
        for player_window in all_windows:
            player_window.window_closed.connect(qt_app.quit)

        # 显示窗口
        for player_window in all_windows:
            if debug_window:
                player_window.resize(960, 540)
                player_window.show()
            else:
                player_window.showFullScreen()

        self.stdout.write(self.style.SUCCESS(
            f"播放器已启动（{len(all_windows)} 窗口），等待播放指令…"
        ))

        # 进入 Qt 事件循环
        exit_code = qt_app.exec()

        # 停止轮询和管线
        controller.stop_polling()

        self.stdout.write(self.style.SUCCESS("播放器窗口已关闭"))
        sys.exit(exit_code)
