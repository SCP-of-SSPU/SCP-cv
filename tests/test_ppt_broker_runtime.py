#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PowerPoint Broker 运行时认证文件测试。
@Project : SCP-cv
@File : test_ppt_broker_runtime.py
@Author : Qintsg
@Date : 2026-07-11
'''
from __future__ import annotations

import os
from pathlib import Path

import pytest

from scp_cv.player.ppt_broker import connect_or_start, load_or_create_authkey
from scp_cv.player.ppt_broker.contracts import BrokerHealth
from scp_cv.player.ppt_broker.runtime import (
    BrokerAlreadyRunningError,
    BrokerInstanceLock,
)


@pytest.mark.skipif(os.name != "nt", reason="命名互斥量仅在 Windows 生效")
def test_broker_instance_lock_is_shared_across_pipe_addresses() -> None:
    """同一 Windows Session 更换管道地址也不得启动第二个 Broker。"""
    with BrokerInstanceLock(r"\\.\pipe\scp-cv-ppt-broker-first"):
        with pytest.raises(BrokerAlreadyRunningError):
            with BrokerInstanceLock(r"\\.\pipe\scp-cv-ppt-broker-second"):
                pass


def test_invalid_authkey_reports_path_and_recovery_steps(tmp_path: Path) -> None:
    """损坏认证文件应给出可直接执行的现场恢复步骤。"""
    auth_path = tmp_path / "ppt-broker.auth"
    auth_path.write_text("not-a-valid-authkey", encoding="ascii")

    with pytest.raises(RuntimeError) as error_info:
        load_or_create_authkey(auth_path)

    message = str(error_info.value)
    assert str(auth_path) in message
    assert "停止 runall、播放器和 PowerPoint Broker" in message
    assert "删除该认证文件" in message
    assert "重新启动" in message


def test_unreadable_authkey_content_reports_recovery_steps(tmp_path: Path) -> None:
    """认证文件无法按 ASCII 读取时也应转换为现场可操作错误。"""
    auth_path = tmp_path / "ppt-broker.auth"
    auth_path.write_bytes(b"\xff\xfe")

    with pytest.raises(RuntimeError) as error_info:
        load_or_create_authkey(auth_path)

    message = str(error_info.value)
    assert str(auth_path) in message
    assert "无法读取" in message
    assert "删除该认证文件" in message


def test_connect_or_start_does_not_claim_a_competing_broker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """并发启动输掉互斥量时不得把另一进程的 Broker 记为己有。"""

    class _ClientStub:
        """模拟首次探测失败、随后可复用的客户端。"""

        def __init__(self, *_args: object, **kwargs: object) -> None:
            self.timeout_seconds = float(kwargs.get("timeout_seconds", 0.0))
            self.started_process: object | None = None

        def health(self) -> BrokerHealth:
            raise OSError("pipe unavailable")

    class _ProcessStub:
        pid = 4100

    monkeypatch.setattr(
        "scp_cv.player.ppt_broker.transport.PptBrokerClient",
        _ClientStub,
    )
    monkeypatch.setattr(
        "scp_cv.player.ppt_broker.runtime.wait_for_broker",
        lambda *_args, **_kwargs: BrokerHealth(
            ready=True,
            generation="winner",
            pid=4200,
        ),
    )

    client = connect_or_start(
        _ProcessStub,
        address=r"\\.\pipe\scp-cv-test",
        authkey=b"x" * 32,
        timeout_seconds=3.0,
    )

    assert client.started_process is None


def test_connect_or_start_claims_only_the_process_reported_by_health(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """健康响应确认 PID 后，独立播放器才拥有刚启动的 Broker。"""

    class _ClientStub:
        def __init__(self, *_args: object, **kwargs: object) -> None:
            self.timeout_seconds = float(kwargs.get("timeout_seconds", 0.0))
            self.started_process: object | None = None

        def health(self) -> BrokerHealth:
            raise OSError("pipe unavailable")

    class _ProcessStub:
        pid = 4300

    started_process = _ProcessStub()
    monkeypatch.setattr(
        "scp_cv.player.ppt_broker.transport.PptBrokerClient",
        _ClientStub,
    )
    monkeypatch.setattr(
        "scp_cv.player.ppt_broker.runtime.wait_for_broker",
        lambda *_args, **_kwargs: BrokerHealth(
            ready=True,
            generation="owned",
            pid=4300,
        ),
    )

    client = connect_or_start(
        lambda: started_process,
        address=r"\\.\pipe\scp-cv-test",
        authkey=b"x" * 32,
    )

    assert client.started_process is started_process


def test_connect_or_start_claims_a_verified_venv_launcher_child(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Windows venv 启动器的 Broker 子进程经谱系与命令行验证后仍归父进程所有。"""

    class _ClientStub:
        def __init__(self, *_args: object, **kwargs: object) -> None:
            self.timeout_seconds = float(kwargs.get("timeout_seconds", 0.0))
            self.started_process: object | None = None

        def health(self) -> BrokerHealth:
            raise OSError("pipe unavailable")

    class _StartedProcessStub:
        pid = 4400

        def poll(self) -> None:
            return None

    class _PsutilProcessStub:
        def __init__(self, process_id: int) -> None:
            self.pid = process_id

        def children(self, recursive: bool = False) -> list[object]:
            assert recursive is True
            return [_PsutilProcessStub(4500)] if self.pid == 4400 else []

        def create_time(self) -> float:
            return 100.0 if self.pid == 4400 else 101.0

        def cmdline(self) -> list[str]:
            if self.pid == 4500:
                return ["python.exe", "manage.py", "run_ppt_broker"]
            return ["python.exe"]

    started_process = _StartedProcessStub()
    monkeypatch.setattr(
        "scp_cv.player.ppt_broker.transport.PptBrokerClient",
        _ClientStub,
    )
    monkeypatch.setattr(
        "scp_cv.player.ppt_broker.runtime.wait_for_broker",
        lambda *_args, **_kwargs: BrokerHealth(
            ready=True,
            generation="venv-child",
            pid=4500,
        ),
    )
    monkeypatch.setattr("psutil.Process", _PsutilProcessStub)

    client = connect_or_start(
        lambda: started_process,
        address=r"\\.\pipe\scp-cv-test",
        authkey=b"x" * 32,
    )

    assert client.started_process is started_process
