#!/user/bin/env python
# -*- coding: UTF-8 -*-
"""
runall 前端环境与启动参数测试。
@Project : SCP-cv
@File : test_runall_frontend.py
@Author : Qintsg
@Date : 2026-07-12
"""

from __future__ import annotations

from pathlib import Path
import shutil
from typing import Any

from scp_cv.apps.dashboard.management.commands import runall
from scp_cv.apps.dashboard.management.runall_frontend import resolve_frontend_port


def test_start_frontend_respects_configured_backend_target(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    """
    frontend/.env 已配置 VITE_BACKEND_TARGET 时，runall 不应覆盖该值。
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
    (frontend_dir / ".env").write_text(
        "VITE_BACKEND_TARGET=http://192.168.1.50:8000\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        shutil,
        "which",
        lambda command_name: "npm.cmd" if command_name == "npm" else None,
    )
    monkeypatch.setattr(command, "_spawn", record_spawn)
    monkeypatch.setattr(runall.settings, "BASE_DIR", tmp_path)
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
