#!/user/bin/env python
# -*- coding: UTF-8 -*-
"""
PowerPoint 进程识别测试，覆盖 COM 主窗口不可读时的进程差集兜底。
@Project : SCP-cv
@File : test_ppt_process.py
@Author : Qintsg
@Date : 2026-06-10
"""

from __future__ import annotations

from pytest import MonkeyPatch

from scp_cv.player.adapters import ppt_process
from scp_cv.player.adapters.ppt_process import read_ppt_app_process_id
from scp_cv.player.adapters.ppt_process import snapshot_candidate_process_ids_for_prog_ids


def test_read_ppt_app_process_id_uses_new_process_when_app_hwnd_missing(
    monkeypatch: MonkeyPatch,
) -> None:
    """
    COM Application.HWND 不可读时，应通过创建前后的进程差集识别新 PowerPoint。
    :param monkeypatch: pytest monkeypatch fixture
    :return: None
    """
    monkeypatch.setattr(
        ppt_process,
        "snapshot_candidate_process_ids",
        lambda _prog_id: {100, 200},
    )

    process_id = read_ppt_app_process_id(
        object(),
        "PowerPoint.Application",
        existing_process_ids={100},
    )

    assert process_id == 200


def test_snapshot_candidate_process_ids_for_prog_ids_uses_prog_id_candidates(
    monkeypatch: MonkeyPatch,
) -> None:
    """
    新建 COM 前应按候选 ProgID 推断进程名，而不是依赖尚未设置的 active ProgID。
    :param monkeypatch: pytest monkeypatch fixture
    :return: None
    """
    captured_names: list[set[str]] = []

    def fake_snapshot_process_ids(process_names: set[str]) -> set[int]:
        """
        记录用于快照的进程名。
        :param process_names: 小写进程名集合
        :return: 伪进程 ID 集合
        """
        captured_names.append(process_names)
        return {101}

    monkeypatch.setattr(ppt_process, "_snapshot_process_ids", fake_snapshot_process_ids)

    process_ids = snapshot_candidate_process_ids_for_prog_ids(
        ["PowerPoint.Application"],
    )

    assert process_ids == {101}
    assert captured_names == [{"powerpnt.exe"}]
