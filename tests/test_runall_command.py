#!/user/bin/env python
# -*- coding: UTF-8 -*-
"""
runall 管理命令测试。
覆盖通配监听地址健康检查和 Windows 子进程树清理。
@Project : SCP-cv
@File : test_runall_command.py
@Author : Qintsg
@Date : 2026-04-29
"""

from __future__ import annotations

from pathlib import Path
import shutil
from typing import Any

from scp_cv.apps.dashboard.management import runall_processes
from scp_cv.apps.dashboard.management.commands import runall
from scp_cv.apps.dashboard.management.runall_frontend import resolve_frontend_port


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
        frontend_port=0,
        grpc_web_port=8081,
        poll_interval=0.2,
        skip_mediamtx=True,
        skip_grpcweb=True,
        skip_frontend=True,
        skip_player=True,
    )

    assert checked_ports == [("Django", "127.0.0.1", 8000, True)]


def test_start_frontend_respects_configured_backend_target(monkeypatch: Any) -> None:
    """
    frontend/.env 已配置 VITE_BACKEND_TARGET 时，runall 不应覆盖该值。
    :param monkeypatch: pytest monkeypatch fixture
    :return: None
    """
    spawned_processes: list[dict[str, Any]] = []
    command = runall.Command()

    def record_spawn(
        name: str,
        command_args: list[str],
        cwd: object = None,
        required: bool = True,
        extra_env: dict[str, str] | None = None,
        env_remove_prefixes: tuple[str, ...] = (),
    ) -> None:
        """
        记录前端启动参数，避免测试中真正拉起 npm。
        :param name: 服务名称
        :param command_args: 命令参数
        :param cwd: 工作目录
        :param required: 是否关键服务
        :param extra_env: 额外环境变量
        :return: None
        """
        spawned_processes.append(
            {
                "name": name,
                "command_args": command_args,
                "cwd": cwd,
                "required": required,
                "extra_env": extra_env,
                "env_remove_prefixes": env_remove_prefixes,
            }
        )

    project_dir = Path("E:/Projects/SCP-cv")
    monkeypatch.setattr(
        shutil,
        "which",
        lambda command_name: "npm.cmd" if command_name == "npm" else None,
    )
    monkeypatch.setattr(command, "_spawn", record_spawn)
    monkeypatch.setattr(runall.settings, "BASE_DIR", project_dir)
    monkeypatch.setenv("VITE_BACKEND_TARGET", "http://root-env-should-not-win:8000")

    command._start_frontend("0.0.0.0", 5173, "0.0.0.0", 8000)

    assert len(spawned_processes) == 1
    assert spawned_processes[0]["name"] == "Vue 前端"
    assert spawned_processes[0]["extra_env"] is None
    assert spawned_processes[0]["env_remove_prefixes"] == ("VITE_",)
    assert spawned_processes[0]["command_args"][-2:] == ["--port", "5173"]


def test_start_frontend_uses_env_port_when_port_is_not_explicit(
    monkeypatch: Any, tmp_path: Path
) -> None:
    """
    未显式指定 frontend_port 时，runall 不应覆盖 frontend/.env 中的 VITE_FRONTEND_PORT。
    :param monkeypatch: pytest monkeypatch fixture
    :param tmp_path: pytest 临时目录 fixture
    :return: None
    """
    spawned_processes: list[dict[str, Any]] = []
    command = runall.Command()

    def record_spawn(
        name: str,
        command_args: list[str],
        cwd: object = None,
        required: bool = True,
        extra_env: dict[str, str] | None = None,
        env_remove_prefixes: tuple[str, ...] = (),
    ) -> None:
        spawned_processes.append(
            {
                "name": name,
                "command_args": command_args,
                "cwd": cwd,
                "required": required,
                "extra_env": extra_env,
                "env_remove_prefixes": env_remove_prefixes,
            }
        )

    frontend_dir = tmp_path / "frontend"
    frontend_dir.mkdir()
    (frontend_dir / ".env").write_text(
        "VITE_FRONTEND_PORT=5260\nVITE_BACKEND_TARGET=http://192.168.1.50:8000\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        shutil,
        "which",
        lambda command_name: "npm.cmd" if command_name == "npm" else None,
    )
    monkeypatch.setattr(command, "_spawn", record_spawn)
    monkeypatch.setattr(runall.settings, "BASE_DIR", tmp_path)
    monkeypatch.setenv("VITE_FRONTEND_PORT", "9999")
    monkeypatch.setenv("VITE_BACKEND_TARGET", "http://root-env-should-not-win:8000")

    command._start_frontend("0.0.0.0", 0, "0.0.0.0", 8000)

    assert len(spawned_processes) == 1
    assert spawned_processes[0]["command_args"] == [
        "npm.cmd",
        "run",
        "dev",
        "--",
        "--host",
        "0.0.0.0",
    ]
    assert resolve_frontend_port(frontend_dir) == 5260


def test_resolve_frontend_port_falls_back_to_vite_default(
    monkeypatch: Any, tmp_path: Path
) -> None:
    """
    frontend/.env 未配置或配置非法时，应回退到 Vite 默认端口 5173。
    :param monkeypatch: pytest monkeypatch fixture
    :param tmp_path: pytest 临时目录 fixture
    :return: None
    """
    frontend_dir = tmp_path / "frontend"
    frontend_dir.mkdir()
    monkeypatch.setattr(runall.settings, "BASE_DIR", tmp_path)
    monkeypatch.setenv("VITE_FRONTEND_PORT", "9999")
    assert resolve_frontend_port(frontend_dir) == 5173
    (frontend_dir / ".env").write_text("VITE_FRONTEND_PORT=invalid\n", encoding="utf-8")
    assert resolve_frontend_port(frontend_dir) == 5173


def test_start_frontend_injects_backend_target_when_config_missing(
    monkeypatch: Any, tmp_path: Path
) -> None:
    """
    frontend/.env 缺少 VITE_BACKEND_TARGET 时，runall 应为前端提供可访问的兜底值。
    :param monkeypatch: pytest monkeypatch fixture
    :param tmp_path: pytest 临时目录 fixture
    :return: None
    """
    spawned_processes: list[dict[str, Any]] = []
    command = runall.Command()

    def record_spawn(
        name: str,
        command_args: list[str],
        cwd: object = None,
        required: bool = True,
        extra_env: dict[str, str] | None = None,
        env_remove_prefixes: tuple[str, ...] = (),
    ) -> None:
        """
        记录前端启动参数，避免测试中真正拉起 npm。
        :param name: 服务名称
        :param command_args: 命令参数
        :param cwd: 工作目录
        :param required: 是否关键服务
        :param extra_env: 额外环境变量
        :return: None
        """
        spawned_processes.append(
            {
                "name": name,
                "command_args": command_args,
                "cwd": cwd,
                "required": required,
                "extra_env": extra_env,
                "env_remove_prefixes": env_remove_prefixes,
            }
        )

    frontend_dir = tmp_path / "frontend"
    frontend_dir.mkdir()
    (frontend_dir / ".env").write_text("VITE_FRONTEND_PORT=5173\n", encoding="utf-8")
    monkeypatch.setattr(
        shutil,
        "which",
        lambda command_name: "npm.cmd" if command_name == "npm" else None,
    )
    monkeypatch.setattr(command, "_spawn", record_spawn)
    monkeypatch.setattr(runall.settings, "BASE_DIR", tmp_path)
    monkeypatch.setenv("VITE_BACKEND_TARGET", "http://root-env-should-not-win:8000")
    monkeypatch.setattr(runall, "public_host", lambda listen_host: "192.168.1.50")

    command._start_frontend("0.0.0.0", 5173, "0.0.0.0", 8000)

    assert len(spawned_processes) == 1
    assert spawned_processes[0]["extra_env"] == {
        "VITE_BACKEND_TARGET": "http://192.168.1.50:8000"
    }
    assert spawned_processes[0]["env_remove_prefixes"] == ("VITE_",)


def test_spawn_removes_prefixed_environment(monkeypatch: Any) -> None:
    """
    前端子进程启动前应移除父进程 VITE_*，避免根目录 .env 遮蔽 frontend/.env。
    :param monkeypatch: pytest monkeypatch fixture
    :return: None
    """
    captured_env: dict[str, str] = {}

    class FakeLog:
        """模拟日志句柄，避免测试写入真实日志文件。"""

        name = "fake.log"

        def close(self) -> None:
            """关闭模拟日志句柄。"""

    class FakeProcess:
        """模拟 Popen 返回对象。"""

        pid = 12345

    def fake_popen(
        command_args: list[str],
        cwd: str | None,
        env: dict[str, str],
        stdout: FakeLog,
        stderr: int,
    ) -> FakeProcess:
        """
        记录传入子进程的环境变量。
        :param command_args: 命令参数
        :param cwd: 工作目录
        :param env: 子进程环境变量
        :param stdout: 标准输出句柄
        :param stderr: 标准错误重定向
        :return: 模拟进程
        """
        captured_env.update(env)
        return FakeProcess()

    command = runall.Command()
    monkeypatch.setenv("VITE_BACKEND_TARGET", "http://root-env-should-not-win:8000")
    monkeypatch.setenv("VITE_FRONTEND_PORT", "9999")
    monkeypatch.setattr(runall, "open_process_log", lambda _log_dir, _name: FakeLog())
    monkeypatch.setattr(runall_processes.subprocess, "Popen", fake_popen)

    command._spawn(
        "Vue 前端",
        ["npm.cmd", "run", "dev"],
        extra_env={"VITE_BACKEND_TARGET": "http://127.0.0.1:8000"},
        env_remove_prefixes=("VITE_",),
    )

    assert captured_env["VITE_BACKEND_TARGET"] == "http://127.0.0.1:8000"
    assert "VITE_FRONTEND_PORT" not in captured_env


def test_start_player_forwards_headless_display_and_gpu_options(
    monkeypatch: Any,
) -> None:
    """
    runall --headless 应把窗口显示器 ID 和 GPU ID 透传给 run_player。
    :param monkeypatch: pytest monkeypatch fixture
    :return: None
    """
    spawned_processes: list[dict[str, Any]] = []
    command = runall.Command()

    def record_spawn(
        name: str,
        command_args: list[str],
        cwd: object = None,
        required: bool = True,
        extra_env: dict[str, str] | None = None,
        env_remove_prefixes: tuple[str, ...] = (),
    ) -> None:
        """
        记录播放器启动命令，避免测试拉起 Qt。
        :param name: 服务名称
        :param command_args: 命令参数
        :param cwd: 工作目录
        :param required: 是否关键服务
        :param extra_env: 额外环境变量
        :param env_remove_prefixes: 环境变量清理前缀
        :return: None
        """
        spawned_processes.append(
            {
                "name": name,
                "command_args": command_args,
                "cwd": cwd,
                "required": required,
                "extra_env": extra_env,
                "env_remove_prefixes": env_remove_prefixes,
            }
        )

    monkeypatch.setattr(command, "_spawn", record_spawn)
    monkeypatch.setattr(runall.settings, "DEBUG", False)

    command._start_player(
        poll_interval=0.3,
        headless=True,
        window_assignments={1: 4, 2: 3, 3: 2, 4: 1},
        gpu_id=2,
    )

    assert len(spawned_processes) == 1
    assert spawned_processes[0]["name"] == "PySide 播放器"
    assert spawned_processes[0]["command_args"][-11:] == [
        "--headless",
        "--window1",
        "4",
        "--window2",
        "3",
        "--window3",
        "2",
        "--window4",
        "1",
        "--gpu",
        "2",
    ]


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

        def __init__(
            self, process_id: int, children: list["FakeProcessNode"] | None = None
        ) -> None:
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

    def fake_wait_procs(
        processes: list[FakeProcessNode], timeout: int
    ) -> tuple[list[FakeProcessNode], list[FakeProcessNode]]:
        """
        模拟进程均在超时前退出。
        :param processes: 等待进程集合
        :param timeout: 等待秒数
        :return: 已退出进程和仍存活进程
        """
        waited_batches.append(([process.pid for process in processes], timeout))
        return processes, []

    monkeypatch.setattr(
        runall_processes.psutil,
        "Process",
        lambda process_id: parent_process if process_id == 10 else None,
    )
    monkeypatch.setattr(runall_processes.psutil, "wait_procs", fake_wait_procs)

    runall_processes.terminate_process_tree(10)

    assert terminated_processes == [11, 10]
    assert waited_batches == [([11, 10], 8)]
