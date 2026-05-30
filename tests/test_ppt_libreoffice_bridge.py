#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
LibreOffice PPT bridge 客户端测试，验证通过 LibreOffice 自带 Python 启动 worker。
@Project : SCP-cv
@File : test_ppt_libreoffice_bridge.py
@Author : Qintsg
@Date : 2026-05-27
'''
from __future__ import annotations

import io
import logging
from pathlib import Path

from pytest import MonkeyPatch

from scp_cv.player.adapters import ppt_libreoffice_bridge


class _FakeProcess:
    """subprocess.Popen 替身。"""

    def __init__(self, stdout: str) -> None:
        """
        初始化进程替身。
        :param stdout: 预置 stdout 内容
        :return: None
        """
        self.stdin = io.StringIO()
        self.stdout = io.StringIO(stdout)
        self.returncode = None

    def poll(self) -> int | None:
        """
        返回进程状态。
        :return: None 表示仍在运行
        """
        return self.returncode

    def terminate(self) -> None:
        """
        模拟终止进程。
        :return: None
        """
        self.returncode = -15

    def wait(self, timeout: float | None = None) -> int:
        """
        模拟等待进程退出。
        :param timeout: 等待超时秒数
        :return: 退出码
        """
        return int(self.returncode or 0)

    def kill(self) -> None:
        """
        模拟强制结束进程。
        :return: None
        """
        self.returncode = -9


def test_bridge_client_uses_libreoffice_python(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    """bridge 客户端应使用 LibreOffice 自带 Python，而不是项目 Python。"""
    captured: dict[str, object] = {}
    fake_process = _FakeProcess(
        '{"id": 1, "command": "open", "success": true, '
        '"data": {"playback_state": "playing", "current_slide": 1, "total_slides": 3, "process_id": 42}, "error": ""}\n'
    )
    lo_python = tmp_path / "python.exe"

    def fake_popen(command: list[str], **kwargs: object) -> _FakeProcess:
        """
        模拟启动 LibreOffice bridge 进程。
        :param command: Popen 命令
        :param kwargs: Popen 参数
        :return: fake 进程
        """
        captured["command"] = command
        captured["kwargs"] = kwargs
        return fake_process

    monkeypatch.setattr(
        ppt_libreoffice_bridge.lo_runtime,
        "resolve_libreoffice_python_executable",
        lambda: lo_python,
    )
    monkeypatch.setattr(ppt_libreoffice_bridge.lo_runtime, "configured_libreoffice_timeout", lambda: 7.0)
    monkeypatch.setattr(
        ppt_libreoffice_bridge.lo_runtime,
        "configured_libreoffice_bridge_command_timeout",
        lambda: 66.0,
    )
    monkeypatch.setenv("PYTHONHOME", str(tmp_path / "python-home"))
    monkeypatch.setenv("PYTHONPATH", str(tmp_path / "python-path"))
    monkeypatch.setenv("PYTHONEXECUTABLE", str(tmp_path / "python.exe"))
    virtual_env = tmp_path / ".venv"
    monkeypatch.setenv("VIRTUAL_ENV", str(virtual_env))
    monkeypatch.setenv("__PYVENV_LAUNCHER__", str(tmp_path / "launcher.exe"))
    monkeypatch.setenv("PATH", f"{virtual_env / 'Scripts'}{ppt_libreoffice_bridge.os.pathsep}{tmp_path / 'tools'}")
    monkeypatch.setattr(ppt_libreoffice_bridge.subprocess, "Popen", fake_popen)

    client = ppt_libreoffice_bridge.LibreOfficeBridgeClient(logging.getLogger(__name__))
    state = client.open("demo.pptx", True, display_index=3)

    assert state == {"playback_state": "playing", "current_slide": 1, "total_slides": 3, "process_id": 42}
    assert captured["command"] == [str(lo_python), "-m", "scp_cv.libreoffice_worker", "bridge"]
    assert captured["kwargs"]["env"]["LIBREOFFICE_CONNECT_TIMEOUT_SECONDS"] == "7.0"
    assert captured["kwargs"]["env"]["LIBREOFFICE_BRIDGE_COMMAND_TIMEOUT_SECONDS"] == "66.0"
    assert "PYTHONHOME" not in captured["kwargs"]["env"]
    assert "PYTHONPATH" not in captured["kwargs"]["env"]
    assert "PYTHONEXECUTABLE" not in captured["kwargs"]["env"]
    assert "VIRTUAL_ENV" not in captured["kwargs"]["env"]
    assert "__PYVENV_LAUNCHER__" not in captured["kwargs"]["env"]
    assert str(virtual_env / "Scripts") not in captured["kwargs"]["env"]["PATH"]
    assert str(tmp_path / "tools") in captured["kwargs"]["env"]["PATH"]
    assert '"command": "open"' in fake_process.stdin.getvalue()
    assert '"display_index": 3' in fake_process.stdin.getvalue()


def test_bridge_client_request_times_out_without_worker_response(monkeypatch: MonkeyPatch) -> None:
    """bridge worker 无响应时应超时终止，避免卡住播放器主线程。"""
    fake_process = _FakeProcess("")
    client = ppt_libreoffice_bridge.LibreOfficeBridgeClient(logging.getLogger(__name__))
    client._process = fake_process
    monkeypatch.setattr(
        ppt_libreoffice_bridge.lo_runtime,
        "configured_libreoffice_timeout",
        lambda: (_ for _ in ()).throw(AssertionError("不应使用 UNO 连接超时")),
    )
    monkeypatch.setattr(
        ppt_libreoffice_bridge.lo_runtime,
        "configured_libreoffice_bridge_command_timeout",
        lambda: 0.01,
    )

    try:
        client.request("open", {"file_path": "demo.pptx", "autoplay": True})
    except ppt_libreoffice_bridge.LibreOfficeBridgeError as request_error:
        assert "响应超时" in str(request_error)
    else:
        raise AssertionError("expected LibreOfficeBridgeError")

    assert fake_process.returncode == -15
    assert '"command": "open"' in fake_process.stdin.getvalue()


def test_bridge_client_close_uses_short_shutdown_timeout(monkeypatch: MonkeyPatch) -> None:
    """bridge 关闭不应沿用较长的播放命令超时。"""
    fake_process = _FakeProcess("")
    client = ppt_libreoffice_bridge.LibreOfficeBridgeClient(logging.getLogger(__name__))
    client._process = fake_process
    monkeypatch.setattr(
        ppt_libreoffice_bridge.lo_runtime,
        "configured_libreoffice_bridge_command_timeout",
        lambda: (_ for _ in ()).throw(AssertionError("不应使用全局 bridge 命令超时")),
    )
    monkeypatch.setattr(ppt_libreoffice_bridge, "_shutdown_timeout_seconds", lambda: 0.1)

    client.close()

    assert fake_process.returncode == -15
    assert '"command": "shutdown"' in fake_process.stdin.getvalue()


def test_bridge_worker_allows_visible_libreoffice_windows() -> None:
    """bridge worker 不能隐藏创建，否则 LibreOffice 全屏放映窗口会卡住。"""
    assert ppt_libreoffice_bridge._subprocess_creation_flags() == 0
