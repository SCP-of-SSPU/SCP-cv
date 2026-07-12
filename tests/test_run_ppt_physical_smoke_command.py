#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
并发 PowerPoint 物理冒烟管理命令测试。
@Project : SCP-cv
@File : test_run_ppt_physical_smoke_command.py
@Author : Qintsg
@Date : 2026-07-11
'''
from __future__ import annotations

from io import StringIO
from pathlib import Path

import pytest
from django.core.management.base import CommandError
from pytest import MonkeyPatch

from scp_cv.apps.dashboard.management.commands.run_ppt_physical_smoke import (
    Command,
)


def test_command_runs_three_rounds_with_explicit_parent_hwnds(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """现场命令应接收 PPT 路径和窗口 1-4 HWND，并输出结构化结果。"""
    ppt_path = tmp_path / "field-smoke.pptx"
    ppt_path.write_bytes(b"fake")
    fake_broker = object()
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        "scp_cv.apps.dashboard.management.ppt_smoke_runtime.connect_ppt_broker",
        lambda timeout_seconds: (
            captured.update({"broker_timeout": timeout_seconds}) or fake_broker
        ),
    )

    def fake_runner(
        broker: object,
        selected_ppt_path: Path,
        parent_hwnds: dict[int, int],
        *,
        iterations: int,
    ) -> dict[str, object]:
        captured.update({
            "broker": broker,
            "ppt_path": selected_ppt_path,
            "parent_hwnds": parent_hwnds,
            "iterations": iterations,
        })
        return {
            "success": True,
            "iterations_requested": iterations,
            "iterations_completed": iterations,
            "rounds": [],
        }

    monkeypatch.setattr(
        "scp_cv.apps.dashboard.management.commands.run_ppt_physical_smoke.run_ppt_concurrency_smoke_test",
        fake_runner,
    )
    output = StringIO()

    Command(stdout=output).handle(
        ppt=str(ppt_path),
        window1_hwnd=1001,
        window2_hwnd=1002,
        window3_hwnd=1003,
        window4_hwnd=1004,
        iterations=3,
        broker_timeout=45.0,
    )

    assert captured == {
        "broker_timeout": 45.0,
        "broker": fake_broker,
        "ppt_path": ppt_path.resolve(),
        "parent_hwnds": {1: 1001, 2: 1002, 3: 1003, 4: 1004},
        "iterations": 3,
    }
    assert '"success": true' in output.getvalue()
    assert "并发 PPT 物理冒烟通过：3/3 轮" in output.getvalue()


def test_command_can_create_temporary_hosts_when_hwnds_are_omitted(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """四项 HWND 全不填时应在临时宿主窗口中执行同一公开服务。"""
    ppt_path = tmp_path / "automatic-hosts.pptx"
    ppt_path.write_bytes(b"fake")
    temporary_parents = {1: 7001, 2: 7002, 3: 7003, 4: 7004}
    captured: dict[str, object] = {}
    monkeypatch.setattr(
        "scp_cv.apps.dashboard.management.ppt_smoke_runtime.connect_ppt_broker",
        lambda _timeout_seconds: object(),
    )
    monkeypatch.setattr(
        "scp_cv.apps.dashboard.management.ppt_smoke_runtime.run_with_temporary_ppt_hosts",
        lambda runner: runner(temporary_parents),
    )

    def fake_runner(
        _broker: object,
        _ppt_path: Path,
        parent_hwnds: dict[int, int],
        *,
        iterations: int,
    ) -> dict[str, object]:
        captured.update({"parents": parent_hwnds, "iterations": iterations})
        return {
            "success": True,
            "iterations_requested": iterations,
            "iterations_completed": iterations,
            "rounds": [],
        }

    monkeypatch.setattr(
        "scp_cv.apps.dashboard.management.commands.run_ppt_physical_smoke.run_ppt_concurrency_smoke_test",
        fake_runner,
    )

    Command(stdout=StringIO()).handle(
        ppt=str(ppt_path),
        window1_hwnd=0,
        window2_hwnd=0,
        window3_hwnd=0,
        window4_hwnd=0,
        iterations=3,
        broker_timeout=120.0,
    )

    assert captured == {"parents": temporary_parents, "iterations": 3}


def test_command_returns_nonzero_failure_with_field_diagnostics(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """冒烟失败应保留结构化结果，并通过 CommandError 产生非零退出。"""
    ppt_path = tmp_path / "powerpoint-missing.pptx"
    ppt_path.write_bytes(b"fake")
    monkeypatch.setattr(
        "scp_cv.apps.dashboard.management.ppt_smoke_runtime.connect_ppt_broker",
        lambda _timeout_seconds: object(),
    )
    monkeypatch.setattr(
        "scp_cv.apps.dashboard.management.commands.run_ppt_physical_smoke.run_ppt_concurrency_smoke_test",
        lambda *_args, **_kwargs: {
            "success": False,
            "iterations_requested": 3,
            "iterations_completed": 0,
            "rounds": [{
                "iteration": 1,
                "status": "failed",
                "error_message": "Microsoft PowerPoint.Application 无法创建",
            }],
        },
    )
    output = StringIO()

    with pytest.raises(CommandError, match="已安装 Microsoft PowerPoint") as error:
        Command(stdout=output).handle(
            ppt=str(ppt_path),
            window1_hwnd=1001,
            window2_hwnd=1002,
            window3_hwnd=1003,
            window4_hwnd=1004,
            iterations=3,
            broker_timeout=120.0,
        )

    assert "第 1 轮" in str(error.value)
    assert "Microsoft PowerPoint.Application 无法创建" in str(error.value)
    assert '"success": false' in output.getvalue()


def test_command_explains_how_to_start_missing_broker(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """Broker 不可达时应给出可直接执行的恢复命令。"""
    ppt_path = tmp_path / "broker-missing.pptx"
    ppt_path.write_bytes(b"fake")
    monkeypatch.setattr(
        "scp_cv.apps.dashboard.management.ppt_smoke_runtime.connect_ppt_broker",
        lambda _timeout_seconds: (_ for _ in ()).throw(FileNotFoundError("pipe missing")),
    )

    with pytest.raises(CommandError, match="manage.py run_ppt_broker") as error:
        Command(stdout=StringIO()).handle(
            ppt=str(ppt_path),
            window1_hwnd=1001,
            window2_hwnd=1002,
            window3_hwnd=1003,
            window4_hwnd=1004,
            iterations=3,
            broker_timeout=120.0,
        )

    assert "pipe missing" in str(error.value)
