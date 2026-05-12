#!/user/bin/env python
# -*- coding: UTF-8 -*-
"""
runall 命令行参数注册。
集中维护服务编排、无 GUI 和后台服务参数。
@Project : SCP-cv
@File : runall_arguments.py
@Author : Qintsg
@Date : 2026-05-12
"""

from __future__ import annotations


def add_runall_arguments(parser: object) -> None:
    """
    添加 runall 管理命令参数。
    :param parser: ArgumentParser 实例
    :return: None
    """
    parser.add_argument(
        "--backend-host", "--host", type=str, default="0.0.0.0", help="Django 监听地址"
    )
    parser.add_argument(
        "--backend-port", "--port", type=int, default=8000, help="Django 监听端口"
    )
    parser.add_argument(
        "--frontend-host", type=str, default="0.0.0.0", help="Vue 前端监听地址"
    )
    parser.add_argument(
        "--frontend-port",
        type=int,
        default=0,
        help="Vue 前端监听端口，0 表示使用 frontend/.env 中的 VITE_FRONTEND_PORT 或 Vite 默认值",
    )
    parser.add_argument(
        "--grpc-web-port", type=int, default=8081, help="gRPC-Web 代理监听端口"
    )
    parser.add_argument(
        "--poll-interval", type=float, default=0.2, help="播放器轮询间隔秒数"
    )
    parser.add_argument(
        "--skip-mediamtx", action="store_true", default=False, help="跳过 MediaMTX"
    )
    parser.add_argument(
        "--skip-grpcweb",
        "--skip-grpc",
        action="store_true",
        default=True,
        help="跳过 gRPC-Web 代理",
    )
    parser.add_argument(
        "--enable-grpcweb",
        action="store_false",
        dest="skip_grpcweb",
        help="启用 gRPC-Web 代理",
    )
    parser.add_argument(
        "--skip-frontend", action="store_true", default=False, help="跳过 Vue 前端"
    )
    parser.add_argument(
        "--skip-player", action="store_true", default=False, help="跳过 PySide 播放器"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=False,
        help="跳过播放器启动器，按命令行显示器配置直接创建窗口",
    )
    parser.add_argument(
        "--service",
        action="store_true",
        default=False,
        help="以后台服务方式启动 runall，并立即返回当前终端",
    )
    parser.add_argument(
        "--window1",
        type=int,
        default=0,
        help="headless 模式下窗口 1 使用的 Windows 显示器 ID",
    )
    parser.add_argument(
        "--window2",
        type=int,
        default=0,
        help="headless 模式下窗口 2 使用的 Windows 显示器 ID",
    )
    parser.add_argument(
        "--window3",
        "--windows3",
        type=int,
        default=0,
        help="headless 模式下窗口 3 使用的 Windows 显示器 ID",
    )
    parser.add_argument(
        "--window4",
        type=int,
        default=0,
        help="headless 模式下窗口 4 使用的 Windows 显示器 ID",
    )
    parser.add_argument(
        "--gpu",
        type=int,
        default=-1,
        help="headless 模式下使用的 GPU ID；未指定时使用系统默认 GPU",
    )
