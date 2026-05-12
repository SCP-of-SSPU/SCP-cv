#!/user/bin/env python
# -*- coding: UTF-8 -*-
"""
runall 进程和网络辅助函数。
封装子进程启动、端口探测和进程树终止逻辑。
@Project : SCP-cv
@File : runall_processes.py
@Author : Qintsg
@Date : 2026-05-12
"""

from __future__ import annotations

import os
import socket
import subprocess
import time
from pathlib import Path
from typing import BinaryIO

import psutil


def open_process_log(log_dir: Path, process_name: str) -> BinaryIO:
    """
    为子进程打开独立日志文件，避免 stdout PIPE 阻塞并保留启动诊断信息。
    :param log_dir: 日志目录
    :param process_name: 服务名称
    :return: 二进制追加模式文件句柄
    """
    safe_name = process_name.lower().replace(" ", "-").replace("/", "-")
    log_path = log_dir / f"{safe_name}.log"
    return log_path.open("ab")


def build_child_environment(
    extra_env: dict[str, str] | None = None,
    env_remove_prefixes: tuple[str, ...] = (),
) -> dict[str, str]:
    """
    构造 runall 子进程环境，按需移除前端变量前缀。
    :param extra_env: 追加传给子进程的环境变量
    :param env_remove_prefixes: 传递前从父进程环境移除的变量名前缀
    :return: 子进程环境变量
    """
    process_env = os.environ.copy()
    process_env.setdefault("CI", "true")
    process_env.setdefault("PYTHONUTF8", "1")
    process_env.setdefault("PYTHONIOENCODING", "utf-8")
    process_env.setdefault("npm_config_yes", "true")
    for env_key in list(process_env):
        if env_key.startswith(env_remove_prefixes):
            process_env.pop(env_key, None)
    if extra_env:
        process_env.update(extra_env)
    return process_env


def spawn_process(
    command_args: list[str],
    log_handle: BinaryIO,
    cwd: Path | None = None,
    extra_env: dict[str, str] | None = None,
    env_remove_prefixes: tuple[str, ...] = (),
) -> subprocess.Popen[bytes]:
    """
    启动一个由 runall 管理的子进程。
    :param command_args: 命令参数列表
    :param log_handle: 子进程日志句柄
    :param cwd: 工作目录
    :param extra_env: 追加传给子进程的环境变量
    :param env_remove_prefixes: 传递前从父进程环境移除的变量名前缀
    :return: Popen 进程对象
    """
    return subprocess.Popen(
        command_args,
        cwd=str(cwd) if cwd else None,
        env=build_child_environment(extra_env, env_remove_prefixes),
        stdout=log_handle,
        stderr=subprocess.STDOUT,
    )


def wait_for_port(host: str, port: int, timeout_seconds: float = 20) -> bool:
    """
    轮询端口可连接状态。
    :param host: 主机
    :param port: 端口
    :param timeout_seconds: 最大等待秒数
    :return: True 表示端口已就绪
    """
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except OSError:
            time.sleep(0.3)
    return False


def connect_host(listen_host: str) -> str:
    """
    将通配监听地址转换为本机健康检查可连接地址。
    :param listen_host: 服务监听地址
    :return: 用于 socket 连接探测的主机地址
    """
    if listen_host in {"0.0.0.0", "::"}:
        return "127.0.0.1"
    return listen_host


def public_host(listen_host: str) -> str:
    """
    将通配监听地址转换为局域网可访问地址，供浏览器和移动设备直连。
    :param listen_host: 服务监听地址
    :return: 可供客户端访问的主机地址
    """
    if listen_host not in {"0.0.0.0", "::"}:
        return listen_host
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
            udp_socket.connect(("8.8.8.8", 80))
            return str(udp_socket.getsockname()[0])
    except OSError:
        return "127.0.0.1"


def terminate_process_tree(process_id: int) -> None:
    """
    终止父进程及其全部子进程，避免 Windows npm/cmd 留下 node 孤儿进程。
    :param process_id: 父进程 PID
    :return: None
    """
    parent_process = psutil.Process(process_id)
    process_tree = parent_process.children(recursive=True)
    process_tree.append(parent_process)
    for child_process in process_tree:
        child_process.terminate()
    _, alive_processes = psutil.wait_procs(process_tree, timeout=8)
    for alive_process in alive_processes:
        alive_process.kill()
    if alive_processes:
        psutil.wait_procs(alive_processes, timeout=3)
