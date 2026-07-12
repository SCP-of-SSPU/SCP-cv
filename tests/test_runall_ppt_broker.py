#!/user/bin/env python
# -*- coding: UTF-8 -*-
"""
runall PowerPoint Broker 启停与关键进程测试。
@Project : SCP-cv
@File : test_runall_ppt_broker.py
@Author : Qintsg
@Date : 2026-07-11
"""

from __future__ import annotations

from typing import Any

from scp_cv.apps.dashboard.management.commands import runall
from scp_cv.player.ppt_broker.contracts import BrokerHealth


def test_handle_waits_for_required_ppt_broker_before_starting_player(
    monkeypatch: Any,
) -> None:
    """
    只要 runall 启动播放器，就应先启动关键 Broker 并等待其就绪。
    :param monkeypatch: pytest monkeypatch fixture
    :return: None
    """
    events: list[str] = []
    spawned_processes: list[dict[str, Any]] = []
    command = runall.Command()

    class _UnavailableClient:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            self.timeout_seconds = 0.5

        def health(self) -> BrokerHealth:
            raise OSError("test broker unavailable")

    def record_spawn(
        name: str,
        command_args: list[str],
        **kwargs: Any,
    ) -> None:
        spawned_processes.append(
            {"name": name, "command_args": command_args, **kwargs}
        )
        events.append(f"spawn:{name}")

    monkeypatch.setattr(runall.atexit, "register", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(runall.signal, "signal", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        runall,
        "create_runall_log_dir",
        lambda log_dir: log_dir / "runall",
    )
    monkeypatch.setattr(command, "_start_django_server", lambda *_args: None)
    monkeypatch.setattr(command, "_wait_for_port", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(command, "_reset_startup_state", lambda: None)
    monkeypatch.setattr(command, "_spawn", record_spawn)
    monkeypatch.setattr(
        "scp_cv.player.ppt_broker.PptBrokerClient",
        _UnavailableClient,
    )
    monkeypatch.setattr(
        command,
        "_wait_for_ppt_broker",
        lambda: events.append("ready:PowerPoint Broker"),
        raising=False,
    )
    monkeypatch.setattr(command, "_monitor_processes", lambda: None)
    monkeypatch.setattr(runall.settings, "DEBUG", False)

    command.handle(
        backend_host="127.0.0.1",
        backend_port=8000,
        frontend_host="127.0.0.1",
        frontend_port=5173,
        grpc_web_port=8081,
        poll_interval=0.2,
        skip_mediamtx=True,
        skip_grpcweb=True,
        skip_frontend=True,
        skip_player=False,
        headless=False,
        service=False,
        gpu=-1,
    )

    assert events == [
        "spawn:PowerPoint Broker",
        "ready:PowerPoint Broker",
        "spawn:PySide 播放器",
    ]
    assert spawned_processes[0]["required"] is True
    assert spawned_processes[0]["command_args"] == [
        runall.sys.executable,
        "manage.py",
        "run_ppt_broker",
    ]


def test_wait_for_ppt_broker_cleans_up_after_authkey_failure(
    monkeypatch: Any,
) -> None:
    """Broker 认证文件异常时 runall 应清理服务并以失败状态退出。"""
    command = runall.Command()
    errors: list[str] = []
    cleanup_calls: list[str] = []

    def fail_wait_for_broker(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("认证文件损坏：C:/runtime/ppt-broker.auth")

    monkeypatch.setattr(
        "scp_cv.player.ppt_broker.wait_for_broker",
        fail_wait_for_broker,
    )
    monkeypatch.setattr(command.stderr, "write", lambda message: errors.append(str(message)))
    monkeypatch.setattr(
        command,
        "_cleanup_processes",
        lambda: cleanup_calls.append("cleanup"),
    )

    try:
        command._wait_for_ppt_broker()
    except SystemExit as exit_error:
        assert exit_error.code == 1
    else:
        raise AssertionError("认证文件异常时 runall 应退出")

    assert cleanup_calls == ["cleanup"]
    assert errors
    assert "PowerPoint Broker 启动失败" in errors[0]
    assert "C:/runtime/ppt-broker.auth" in errors[0]


def test_prepare_ppt_broker_reuses_an_existing_healthy_instance(
    monkeypatch: Any,
) -> None:
    """runall 不得重复拉起已有的健康 Broker，也不得取得其关闭所有权。"""
    command = runall.Command()
    started: list[str] = []
    waited: list[str] = []

    class _ClientStub:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def health(self) -> BrokerHealth:
            return BrokerHealth(ready=True, generation="existing", pid=3900)

    monkeypatch.setattr(
        "scp_cv.player.ppt_broker.PptBrokerClient",
        _ClientStub,
    )
    monkeypatch.setattr(
        command,
        "_start_ppt_broker",
        lambda: started.append("start"),
    )
    monkeypatch.setattr(
        command,
        "_wait_for_ppt_broker",
        lambda: waited.append("wait"),
    )

    health = command._prepare_ppt_broker()

    assert health.pid == 3900
    assert started == []
    assert waited == []


def test_reused_ppt_broker_generation_change_is_critical() -> None:
    """复用 Broker 被替换后会话已丢失，runall 必须按关键依赖失败处理。"""
    command = runall.Command()

    class _ClientStub:
        def health(self) -> BrokerHealth:
            return BrokerHealth(ready=True, generation="replacement", pid=4001)

    command._ppt_broker_client = _ClientStub()
    command._ppt_broker_health = BrokerHealth(
        ready=True,
        generation="original",
        pid=4000,
    )

    assert command._ppt_broker_is_healthy() is False


def test_cleanup_stops_player_before_ppt_broker(monkeypatch: Any) -> None:
    """
    runall 清理时应先停止播放器，再停止其依赖的 PowerPoint Broker。
    :param monkeypatch: pytest monkeypatch fixture
    :return: None
    """
    events: list[str] = []
    terminated_process_ids: list[int] = []

    class FakeProcess:
        """保持运行状态的子进程替身。"""

        def __init__(self, process_id: int) -> None:
            self.pid = process_id

        def poll(self) -> None:
            return None

    command = runall.Command()
    command._processes = [
        runall.ManagedProcess(
            name="PowerPoint Broker",
            process=FakeProcess(100),  # type: ignore[arg-type]
        ),
        runall.ManagedProcess(
            name="PySide 播放器",
            process=FakeProcess(200),  # type: ignore[arg-type]
        ),
    ]
    monkeypatch.setattr(
        runall,
        "terminate_process_tree",
        lambda process_id: (
            terminated_process_ids.append(process_id),
            events.append(f"tree:{process_id}"),
        ),
    )
    monkeypatch.setattr(
        command,
        "_stop_ppt_broker",
        lambda managed_process: events.append(
            f"broker:{managed_process.process.pid}"
        ),
        raising=False,
    )

    command._cleanup_processes()

    assert terminated_process_ids == [200]
    assert events == ["tree:200", "broker:100"]


def test_stop_ppt_broker_waits_for_graceful_shutdown_without_tree_kill(
    monkeypatch: Any,
) -> None:
    """Broker 正常响应 shutdown 时应等待其自行退出，不发送强制终止。"""
    events: list[str] = []

    class _ClientStub:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def shutdown(self) -> None:
            events.append("shutdown")

    class _ProcessStub:
        pid = 100

        def __init__(self) -> None:
            self.exit_code: int | None = None

        def poll(self) -> int | None:
            return self.exit_code

        def wait(self, timeout: int) -> int:
            events.append(f"wait:{timeout}")
            self.exit_code = 0
            return 0

        def terminate(self) -> None:
            raise AssertionError("正常 shutdown 后不得 terminate")

        def kill(self) -> None:
            raise AssertionError("正常 shutdown 后不得 kill")

    monkeypatch.setattr(
        "scp_cv.player.ppt_broker.PptBrokerClient",
        _ClientStub,
    )
    command = runall.Command()
    process = _ProcessStub()

    command._stop_ppt_broker(
        runall.ManagedProcess(
            name="PowerPoint Broker",
            process=process,  # type: ignore[arg-type]
        )
    )

    assert events == ["shutdown", "wait:15"]
