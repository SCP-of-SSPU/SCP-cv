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
import subprocess
import threading
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

    def open(self, file_path: str, autoplay: bool) -> dict[str, object]:
        """
        启动 bridge 并打开 PPT。
        :param file_path: PPT 文件路径
        :param autoplay: 是否立即开始放映
        :return: worker 状态数据
        """
        self._ensure_process()
        return self.request("open", {"file_path": file_path, "autoplay": autoplay})

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
            while True:
                line = process.stdout.readline()
                if not line:
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
            try:
                process.terminate()
                process.wait(timeout=3)
            except Exception:
                try:
                    process.kill()
                    process.wait(timeout=3)
                except Exception:
                    self._logger.debug("LibreOffice bridge 子进程强制结束失败", exc_info=True)
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


def _subprocess_creation_flags() -> int:
    """
    返回 Windows 子进程创建标志。
    :return: subprocess creationflags
    """
    if os.name != "nt":
        return 0
    return getattr(subprocess, "CREATE_NO_WINDOW", 0)


__all__ = ["LibreOfficeBridgeClient", "LibreOfficeBridgeError"]
