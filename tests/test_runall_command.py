#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
runall 管理命令测试。
覆盖通配监听地址健康检查和 Windows 子进程树清理。
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


def test_terminate_process_tree_stops_children_before_parent(monkeypatch: Any) -> None:
    """
    清理服务时应终止子进程树，避免 npm/cmd 留下 node 孤儿进程。
    :param monkeypatch: pytest monkeypatch fixture
    :return: None
    """
    terminated_processes: list[int] = []
    waited_batches: list[tuple[list[int], int]] = []

    class FakeProcessNode:
        """模拟 psutil 进程节点，记录终止顺序。"""

        def __init__(self, process_id: int, children: list["FakeProcessNode"] | None = None) -> None:
            """
            初始化模拟进程节点。
            :param process_id: 模拟 PID
            :param children: 模拟子进程集合
            :return: None
            """
            self.pid = process_id
            self._children = children or []

        def children(self, recursive: bool) -> list["FakeProcessNode"]:
            """
            返回模拟子进程集合。
            :param recursive: 是否递归查找子进程
            :return: 子进程集合
            """
            assert recursive is True
            return self._children

        def terminate(self) -> None:
            """
            记录 terminate 调用。
            :return: None
            """
            terminated_processes.append(self.pid)

        def kill(self) -> None:
            """
            wait_procs 全部成功时不应触发 kill。
            :return: None
            """
            raise AssertionError("unexpected kill")

    child_process = FakeProcessNode(11)
    parent_process = FakeProcessNode(10, [child_process])

    def fake_wait_procs(processes: list[FakeProcessNode], timeout: int) -> tuple[list[FakeProcessNode], list[FakeProcessNode]]:
        """
        模拟进程均在超时前退出。
        :param processes: 等待进程集合
        :param timeout: 等待秒数
        :return: 已退出进程和仍存活进程
        """
        waited_batches.append(([process.pid for process in processes], timeout))
        return processes, []

    monkeypatch.setattr(runall.psutil, "Process", lambda process_id: parent_process if process_id == 10 else None)
    monkeypatch.setattr(runall.psutil, "wait_procs", fake_wait_procs)

    runall.Command()._terminate_process_tree(10)

    assert terminated_processes == [11, 10]
    assert waited_batches == [([11, 10], 8)]
