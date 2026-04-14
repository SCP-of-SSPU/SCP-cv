#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
Django 管理命令：启动 PySide6 播放器窗口。
先显示启动器 GUI 供用户选择显示模式和屏幕，
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
    help = "启动 PySide6 本地播放器窗口（WebRTC + GStreamer）"

    def add_arguments(self, parser: object) -> None:
        """
        添加命令行参数。
        :param parser: ArgumentParser 实例
        """
        parser.add_argument(
            "--dev",
            action="store_true",
            default=False,
            help="开发模式：启动器和播放窗口均显示标题栏，不全屏",
        )
        parser.add_argument(
            "--poll-interval",
            type=float,
            default=0.5,
            help="轮询会话状态的间隔秒数（默认 0.5）",
        )

    def handle(self, **options: object) -> None:
        """
        入口：初始化 GStreamer → 显示启动器 GUI → 创建播放窗口。
        :param options: 命令行参数字典
        """
        # 初始化 GStreamer（必须在 Qt 之前）
        from scp_cv.player import init_gstreamer
        gst_ok = init_gstreamer()
        if not gst_ok:
            self.stderr.write(self.style.ERROR(
                "GStreamer 初始化失败。请安装 GStreamer（Complete 选项）。\n"
                "支持变体（按优先级）：MSVC x86_64 → MinGW x86_64 → MSYS2 MinGW64\n"
                "下载地址：https://gstreamer.freedesktop.org/download/\n"
                "PyGObject 安装请运行：python tools/install_pygobject.py"
            ))
            sys.exit(1)

        from PySide6.QtWidgets import QApplication

        dev_mode = bool(options.get("dev", False)) or settings.DEBUG
        poll_interval = float(options.get("poll_interval", 0.5))

        self.stdout.write(self.style.SUCCESS(
            f"启动播放器（dev={dev_mode}, poll={poll_interval}s, engine=GStreamer+WebRTC）"
        ))

        # 创建 Qt 应用
        qt_app = QApplication.instance()
        if qt_app is None:
            qt_app = QApplication(sys.argv)

        # 显示启动器 GUI，等待用户选择
        from scp_cv.player.launcher_gui import LauncherResult, LauncherWindow

        launcher_result_holder: list[LauncherResult] = []

        def on_launch_requested(result: LauncherResult) -> None:
            """
            启动器回调：保存选择结果。
            :param result: 用户选择的显示模式和屏幕
            """
            launcher_result_holder.append(result)

        launcher = LauncherWindow(debug_mode=dev_mode)
        launcher.launch_requested.connect(on_launch_requested)
        launcher.show()

        # 运行事件循环（启动器关闭后返回）
        qt_app.exec()

        # 检查用户是否完成了选择（否则是直接关闭了窗口）
        if not launcher_result_holder:
            self.stdout.write(self.style.WARNING("用户未完成选择，退出"))
            sys.exit(0)

        launch_result = launcher_result_holder[0]
        self.stdout.write(self.style.SUCCESS(
            f"用户选择：mode={launch_result.display_mode}"
        ))

        # ═══ 根据选择结果创建播放窗口 ═══
        self._start_player(qt_app, launch_result, dev_mode, poll_interval)

    def _start_player(
        self,
        qt_app: object,
        launch_result: object,
        dev_mode: bool,
        poll_interval: float,
    ) -> None:
        """
        根据启动器结果创建播放窗口并启动事件循环。
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
        from scp_cv.apps.playback.models import PlaybackMode

        # 类型断言
        result: LauncherResult = launch_result

        # 更新数据库会话的显示模式
        session = get_or_create_session()
        if result.display_mode == "left_right_splice":
            session.display_mode = PlaybackMode.LEFT_RIGHT_SPLICE
            if result.left_target and result.right_target:
                session.spliced_display_label = (
                    f"{result.left_target.name} + {result.right_target.name}"
                )
                session.is_spliced = True
        else:
            session.display_mode = PlaybackMode.SINGLE
            if result.single_target:
                session.target_display_label = result.single_target.name
            session.is_spliced = False
        session.save()

        # 创建控制器
        controller = PlayerController()
        all_windows: list[PlayerWindow] = []

        if result.display_mode == "left_right_splice" and result.left_target and result.right_target:
            # 拼接模式：左右各一个窗口
            left_window = PlayerWindow(window_id="left", debug_mode=dev_mode)
            right_window = PlayerWindow(window_id="right", debug_mode=dev_mode)
            controller.register_window("left", left_window)
            controller.register_window("right", right_window)
            all_windows.extend([left_window, right_window])

            # 定位到用户选择的屏幕
            left_rect = QRect(
                result.left_target.x, result.left_target.y,
                result.left_target.width, result.left_target.height,
            )
            right_rect = QRect(
                result.right_target.x, result.right_target.y,
                result.right_target.width, result.right_target.height,
            )
            left_window.position_on_display(left_rect)
            right_window.position_on_display(right_rect)
            self.stdout.write(self.style.SUCCESS(
                f"拼接模式：左={result.left_target.name}，右={result.right_target.name}"
            ))
        else:
            # 单屏模式
            single_window = PlayerWindow(window_id="single", debug_mode=dev_mode)
            controller.register_window("single", single_window)
            all_windows.append(single_window)

            if result.single_target:
                target_rect = QRect(
                    result.single_target.x, result.single_target.y,
                    result.single_target.width, result.single_target.height,
                )
                single_window.position_on_display(target_rect)
                self.stdout.write(self.style.SUCCESS(
                    f"单屏模式：{result.single_target.name}"
                ))

        # 启动轮询
        controller.start_polling(interval_seconds=poll_interval)

        # 任意窗口关闭时退出
        for player_window in all_windows:
            player_window.window_closed.connect(qt_app.quit)

        # dev 模式下显示窗口（非 dev 已由 position_on_display 处理）
        for player_window in all_windows:
            if dev_mode:
                player_window.resize(960, 540)
                player_window.show()

        self.stdout.write(self.style.SUCCESS(
            f"播放器已启动（{len(all_windows)} 窗口），等待播放指令…"
        ))

        # 进入 Qt 事件循环
        exit_code = qt_app.exec()

        # 停止轮询和管线
        controller.stop_polling()

        self.stdout.write(self.style.SUCCESS("播放器窗口已关闭"))
        sys.exit(exit_code)
