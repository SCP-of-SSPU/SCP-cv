#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PowerPoint 物理冒烟命令共享的 Broker 与临时原生宿主运行时。
@Project : SCP-cv
@File : ppt_smoke_runtime.py
@Author : Qintsg
@Date : 2026-07-11
'''
from __future__ import annotations

import queue
import sys
import threading
from collections.abc import Callable

from django.core.management.base import CommandError


def connect_ppt_broker(timeout_seconds: float) -> object:
    """连接当前 Windows Session 的默认 PowerPoint Broker。"""
    from scp_cv.player.ppt_broker import PptBrokerClient

    return PptBrokerClient(timeout_seconds=timeout_seconds)


def run_with_temporary_ppt_hosts(
    runner: Callable[[dict[int, int]], dict[str, object]],
) -> dict[str, object]:
    """创建四个临时原生宿主，在 GUI 消息循环存活期间运行冒烟。"""
    try:
        from PySide6.QtCore import QTimer, Qt
        from PySide6.QtWidgets import QApplication, QWidget
    except ImportError as import_error:
        raise CommandError(
            "无法创建临时 PPT 宿主窗口：PySide6 未安装；"
            "请运行 `uv sync`，或使用兼容命令显式提供四个 --windowN-hwnd。"
        ) from import_error

    try:
        application = QApplication.instance() or QApplication(sys.argv[:1])
        screen = application.primaryScreen()
        if screen is None:
            raise RuntimeError("当前交互桌面没有可用显示器")
        available = screen.availableGeometry()
        width_limit = (available.width() - 16) // 2
        height_limit_as_width = int(((available.height() - 16) // 2) * 16 / 9)
        host_width = max(160, min(640, width_limit, height_limit_as_width))
        host_height = max(180, int(host_width * 9 / 16))
        hosts: list[QWidget] = []
        for index, window_id in enumerate(range(1, 5)):
            host = QWidget()
            host.setWindowTitle(f"SCP-cv PPT 并发冒烟 [窗口{window_id}]")
            host.setAttribute(Qt.WidgetAttribute.WA_NativeWindow, True)
            host.setStyleSheet("background-color: #000000;")
            host.resize(host_width, host_height)
            row, column = divmod(index, 2)
            host.move(
                available.x() + column * (host_width + 16),
                available.y() + row * (host_height + 16),
            )
            host.show()
            hosts.append(host)
        application.processEvents()
        parent_hwnds = {
            window_id: int(hosts[window_id - 1].winId())
            for window_id in range(1, 5)
        }
    except Exception as host_error:
        raise CommandError(
            "无法在当前交互桌面创建四个 PPT 临时宿主窗口；"
            "请确认命令不是从 Windows 服务或无桌面会话运行，"
            "也可使用兼容命令显式提供四个 --windowN-hwnd。"
            f"原始错误：{host_error}"
        ) from host_error

    outcome: queue.Queue[tuple[bool, object]] = queue.Queue(maxsize=1)

    def run_smoke() -> None:
        try:
            outcome.put((True, runner(parent_hwnds)))
        except BaseException as smoke_error:
            outcome.put((False, smoke_error))

    worker = threading.Thread(
        target=run_smoke,
        name="ppt-physical-smoke-worker",
        daemon=True,
    )
    poll_timer = QTimer()
    poll_timer.setInterval(25)
    poll_timer.timeout.connect(
        lambda: application.quit() if not worker.is_alive() else None
    )
    worker.start()
    poll_timer.start()
    try:
        application.exec()
        worker.join()
    finally:
        poll_timer.stop()
        for host in hosts:
            host.close()
        application.processEvents()

    succeeded, value = outcome.get_nowait()
    if not succeeded:
        if isinstance(value, BaseException):
            raise value
        raise CommandError(f"PPT 临时宿主冒烟失败：{value}")
    if not isinstance(value, dict):
        raise CommandError("PPT 临时宿主冒烟未返回结构化结果")
    return value


__all__ = ["connect_ppt_broker", "run_with_temporary_ppt_hosts"]
