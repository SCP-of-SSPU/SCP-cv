#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
runall 残留进程清理测试，覆盖项目归属判定与退出竞态。
@Project : SCP-cv
@File : test_runall_residual_processes.py
@Author : Qintsg
@Date : 2026-08-23
'''
from __future__ import annotations

from pathlib import Path
from typing import Any

from scp_cv.apps.dashboard.management import runall_processes


class _ResidualProcess:
    """提供残留进程清理所需的最小 psutil 接口。"""

    def __init__(self, process_info: dict[str, object], terminated: list[int]) -> None:
        """
        初始化模拟进程。

        :param process_info: psutil 进程信息
        :param terminated: 终止调用记录
        :return: None
        """
        self.info = process_info
        self._terminated = terminated

    def terminate(self) -> None:
        """
        记录终止调用。

        :return: None
        """
        self._terminated.append(int(self.info["pid"]))


def test_cleanup_only_terminates_project_owned_processes(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    """
    兜底清理不得误杀无关 PowerShell，并应识别项目播放器。

    :param monkeypatch: pytest monkeypatch fixture
    :param tmp_path: 模拟项目目录
    :return: None
    """
    project_dir = tmp_path / "SCP-cv"
    project_dir.mkdir()
    terminated: list[int] = []
    processes = [
        _ResidualProcess({
            "pid": 21, "ppid": 1, "name": "powershell.exe",
            "cmdline": ["powershell.exe", "-NoProfile"],
            "cwd": str(tmp_path / "other"),
            "exe": "C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe",
        }, terminated),
        _ResidualProcess({
            "pid": 23, "ppid": 1, "name": "python.exe",
            "cmdline": ["python.exe", "manage.py", "run_player", "--only-window", "1"],
            "cwd": str(project_dir), "exe": "C:/Python/python.exe",
        }, terminated),
    ]
    monkeypatch.setattr(runall_processes.psutil, "process_iter", lambda _attrs: processes)
    monkeypatch.setattr(
        runall_processes.psutil,
        "wait_procs",
        lambda process_list, timeout: (process_list, []),
    )

    result = runall_processes.cleanup_residual_processes(10, 11, project_dir)

    assert result == [23]
    assert terminated == [23]


def test_cleanup_waits_on_original_process_object(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    """
    terminate 后必须继续等待原始进程对象，避免 PID 复用误杀新进程。

    :param monkeypatch: pytest monkeypatch fixture
    :param tmp_path: 模拟项目目录
    :return: None
    """
    process = _ResidualProcess({
        "pid": 23, "ppid": 1, "name": "python.exe",
        "cmdline": ["python.exe", "manage.py", "run_player"],
        "cwd": str(tmp_path), "exe": "C:/Python/python.exe",
    }, [])
    monkeypatch.setattr(runall_processes.psutil, "process_iter", lambda _attrs: [process])

    monkeypatch.setattr(
        runall_processes.psutil,
        "Process",
        lambda _pid: (_ for _ in ()).throw(AssertionError("不得按 PID 重建进程对象")),
    )
    waited: list[list[object]] = []
    monkeypatch.setattr(
        runall_processes.psutil,
        "wait_procs",
        lambda process_list, timeout: (waited.append(process_list) or process_list, []),
    )

    assert runall_processes.cleanup_residual_processes(10, None, tmp_path) == [23]
    assert waited == [[process], []]
