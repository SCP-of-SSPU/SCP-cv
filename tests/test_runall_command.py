#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
runall 管理命令测试。
覆盖通配监听地址启动时的健康检查连接地址转换。
@Project : SCP-cv
@File : test_runall_command.py
@Author : Qintsg
@Date : 2026-04-29
'''
from __future__ import annotations

from typing import Any

from scp_cv.apps.dashboard.management.commands import runall


def test_handle_checks_django_via_loopback_for_wildcard_host(monkeypatch: Any) -> None:
    """
    Django 监听 0.0.0.0 时应使用 127.0.0.1 做本机健康检查。
    :param monkeypatch: pytest monkeypatch fixture
    :return: None
    """
    checked_ports: list[tuple[str, str, int, bool]] = []
    command = runall.Command()

    def record_wait_for_port(name: str, host: str, port: int, required: bool) -> None:
        """
        记录健康检查参数，避免测试真正占用端口。
        :param name: 服务名称
        :param host: 健康检查连接地址
        :param port: 健康检查端口
        :param required: 是否关键服务
        :return: None
        """
        checked_ports.append((name, host, port, required))

    monkeypatch.setattr(runall.atexit, "register", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(runall.signal, "signal", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(command, "_start_django_server", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(command, "_wait_for_port", record_wait_for_port)
    monkeypatch.setattr(command, "_monitor_processes", lambda: None)

    command.handle(
        backend_host="0.0.0.0",
        backend_port=8000,
        frontend_host="0.0.0.0",
        frontend_port=5173,
        grpc_web_port=8081,
        poll_interval=0.2,
        skip_mediamtx=True,
        skip_grpcweb=True,
        skip_frontend=True,
        skip_player=True,
    )

    assert checked_ports == [("Django", "127.0.0.1", 8000, True)]
