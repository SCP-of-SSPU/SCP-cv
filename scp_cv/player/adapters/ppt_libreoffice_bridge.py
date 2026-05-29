#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
LibreOffice PPT 放映 bridge 客户端，通过 LibreOffice 自带 Python 执行 UNO。
@Project : SCP-cv
@File : ppt_libreoffice_bridge.py
@Author : Qintsg
@Date : 2026-05-27
'''
from __future__ import annotations

import json
import logging
import os
import queue
import subprocess
import threading
import time
from typing import Optional

from django.conf import settings

from scp_cv import libreoffice as lo_runtime


class LibreOfficeBridgeError(RuntimeError):
    """LibreOffice bridge 调用失败。"""


class LibreOfficeBridgeClient:
    """LibreOffice Python bridge 子进程客户端。"""

    def __init__(self, logger: logging.Logger) -> None:
        """
        初始化 bridge 客户端。
        :param logger: 日志器
        :return: None
        """
        self._logger = logger
        self._process: Optional[subprocess.Popen[str]] = None
        self._request_id = 0
        self._lock = threading.Lock()
        self._stdout_queue: queue.Queue[str | None] = queue.Queue()
        self._stdout_thread: Optional[threading.Thread] = None

    def open(self, file_path: str, autoplay: bool) -> dict[str, object]:
        """
        启动 bridge 并打开 PPT。
        :param file_path: PPT 文件路径
        :param autoplay: 是否立即开始放映
        :return: worker 状态数据
        """
        self._ensure_process()
        return self.request("open", {"file_path": file_path, "autoplay": autoplay})

    def preheat(self) -> dict[str, object]:
        """
        启动 bridge 与 LibreOffice 会话但不打开文档。
        :return: worker 状态数据
        """
        self._ensure_process()
        return self.request("preheat")

    def close_document(self) -> dict[str, object]:
        """
        关闭当前文档但保留 bridge 和 LibreOffice 进程。
        :return: worker 状态数据
        """
        return self.request("close_document")

    def request(self, command: str, payload: Optional[dict[str, object]] = None) -> dict[str, object]:
        """
        发送 bridge 命令并等待 JSON 响应。
        :param command: 命令名称
        :param payload: 命令参数
        :return: worker 响应 data
        :raises LibreOfficeBridgeError: 子进程未启动、退出或返回失败时
        """
        process = self._process
        if process is None or process.stdin is None or process.stdout is None:
            raise LibreOfficeBridgeError("LibreOffice bridge 未启动")
        if process.poll() is not None:
            raise LibreOfficeBridgeError(f"LibreOffice bridge 已退出，退出码={process.returncode}")

        with self._lock:
            self._request_id += 1
            request_id = self._request_id
            request = {"id": request_id, "command": command, "payload": payload or {}}
            process.stdin.write(json.dumps(request, ensure_ascii=False) + "\n")
            process.stdin.flush()
            timeout_seconds = lo_runtime.configured_libreoffice_bridge_command_timeout()
            deadline = time.monotonic() + timeout_seconds
            while True:
                if process.poll() is not None:
                    raise LibreOfficeBridgeError(f"LibreOffice bridge 已退出，退出码={process.returncode}")
                remaining_seconds = deadline - time.monotonic()
                if remaining_seconds <= 0:
                    self._terminate_process(process)
                    raise LibreOfficeBridgeError(
                        f"LibreOffice bridge 响应超时（命令：{command}，{timeout_seconds:.1f}s）"
                    )
                try:
                    line = self._stdout_queue.get(timeout=min(0.1, remaining_seconds))
                except queue.Empty:
                    continue
                if line is None:
                    raise LibreOfficeBridgeError("LibreOffice bridge 未返回响应")
                try:
                    response = json.loads(line)
                except json.JSONDecodeError:
                    self._logger.debug("LibreOffice bridge 输出：%s", line.strip())
                    continue
                if response.get("id") != request_id:
                    self._logger.debug("忽略非当前 LibreOffice bridge 响应：%s", response)
                    continue
                if not response.get("success"):
                    raise LibreOfficeBridgeError(str(response.get("error", "LibreOffice bridge 调用失败")))
                data = response.get("data", {})
                return data if isinstance(data, dict) else {}

    def close(self) -> None:
        """
        关闭 bridge 子进程。
        :return: None
        """
        process = self._process
        if process is None:
            return
        try:
            if process.poll() is None:
                try:
                    self.request("shutdown")
                except Exception:
                    pass
                process.wait(timeout=3)
        except Exception:
            self._terminate_process(process)
        self._process = None

    def _ensure_process(self) -> None:
        """
        确保 bridge 子进程已启动。
        :return: None
        """
        if self._process is not None and self._process.poll() is None:
            return
        python_executable = lo_runtime.resolve_libreoffice_python_executable()
        env = os.environ.copy()
        env["LIBREOFFICE_CONNECT_TIMEOUT_SECONDS"] = str(lo_runtime.configured_libreoffice_timeout())
        env["LIBREOFFICE_BRIDGE_COMMAND_TIMEOUT_SECONDS"] = str(
            lo_runtime.configured_libreoffice_bridge_command_timeout()
        )
        command = [str(python_executable), "-m", "scp_cv.libreoffice_worker", "bridge"]
        self._process = subprocess.Popen(
            command,
            cwd=str(settings.BASE_DIR),
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=_subprocess_creation_flags(),
        )
        self._stdout_queue = queue.Queue()
        self._stdout_thread = threading.Thread(
            target=_read_stdout_lines,
            args=(self._process, self._stdout_queue),
            daemon=True,
            name="libreoffice-bridge-stdout",
        )
        self._stdout_thread.start()

    def _terminate_process(self, process: subprocess.Popen[str]) -> None:
        """
        终止无响应的 bridge 子进程。
        :param process: 待终止的 bridge 进程
        :return: None
        """
        if process.poll() is not None:
            return
        if _terminate_process_tree(getattr(process, "pid", 0), self._logger):
            return
        try:
            process.terminate()
            process.wait(timeout=3)
            return
        except Exception:
            pass
        try:
            process.kill()
            process.wait(timeout=3)
        except Exception:
            self._logger.debug("LibreOffice bridge 子进程强制结束失败", exc_info=True)


def _terminate_process_tree(process_id: int, logger: logging.Logger) -> bool:
    """
    终止 bridge 进程树，避免卡住的 soffice 子进程残留。
    :param process_id: bridge 进程 PID
    :param logger: 日志器
    :return: True 表示已尝试通过 psutil 处理
    """
    if process_id <= 0:
        return False
    try:
        import psutil

        parent_process = psutil.Process(process_id)
        process_tree = parent_process.children(recursive=True)
        process_tree.append(parent_process)
        for child_process in process_tree:
            try:
                child_process.terminate()
            except psutil.Error:
                pass
        _, alive_processes = psutil.wait_procs(process_tree, timeout=3)
        for alive_process in alive_processes:
            try:
                alive_process.kill()
            except psutil.Error:
                pass
        if alive_processes:
            psutil.wait_procs(alive_processes, timeout=2)
        return True
    except Exception:
        logger.debug("LibreOffice bridge 进程树终止失败，退回单进程终止", exc_info=True)
        return False


def _read_stdout_lines(
    process: subprocess.Popen[str],
    stdout_queue: queue.Queue[str | None],
) -> None:
    """
    后台读取 bridge stdout，避免主线程在 readline 上无限阻塞。
    :param process: bridge 进程
    :param stdout_queue: stdout 行队列；None 表示 EOF
    :return: None
    """
    stdout = process.stdout
    if stdout is None:
        stdout_queue.put(None)
        return
    try:
        while True:
            line = stdout.readline()
            if not line:
                break
            stdout_queue.put(line)
    finally:
        stdout_queue.put(None)


def _subprocess_creation_flags() -> int:
    """
    返回 Windows 子进程创建标志。
    :return: subprocess creationflags
    """
    if os.name != "nt":
        return 0
    return getattr(subprocess, "CREATE_NO_WINDOW", 0)


__all__ = ["LibreOfficeBridgeClient", "LibreOfficeBridgeError"]
