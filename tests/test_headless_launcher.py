#!/user/bin/env python
# -*- coding: UTF-8 -*-
"""
播放器无 GUI 启动参数测试。
覆盖显示器和 GPU ID 到启动结果的解析。
@Project : SCP-cv
@File : test_headless_launcher.py
@Author : Qintsg
@Date : 2026-05-12
"""

from __future__ import annotations
from typing import Any
import pytest
from scp_cv.player.gpu_detector import GPUInfo
from scp_cv.player.headless_launcher import build_headless_launch_result
from scp_cv.services.display import DisplayTarget


def test_build_headless_launch_result_uses_default_window_display_mapping(
    monkeypatch: Any,
) -> None:
    """
    未显式配置窗口显示器时，窗口 1-4 应默认映射到显示器 1-4。
    :param monkeypatch: pytest monkeypatch fixture
    :return: None
    """
    displays = [
        DisplayTarget(
            index=index,
            name=f"显示器 {index}",
            width=1920,
            height=1080,
            x=0,
            y=0,
            is_primary=index == 1,
        )
        for index in range(1, 5)
    ]
    monkeypatch.setattr(
        "scp_cv.player.headless_launcher.list_display_targets", lambda: displays
    )
    monkeypatch.setattr("scp_cv.player.headless_launcher.enumerate_gpus", lambda: [])
    launch_result = build_headless_launch_result(window_display_ids={}, gpu_id=None)
    assert sorted(launch_result.window_assignments) == [1, 2, 3, 4]
    assert [target.index for target in launch_result.window_assignments.values()] == [
        1,
        2,
        3,
        4,
    ]
    assert launch_result.selected_gpu is None


def test_build_headless_launch_result_respects_explicit_display_and_gpu(
    monkeypatch: Any,
) -> None:
    """
    显式 window* 与 --gpu 应按 ID 选择对应显示器和显卡。
    :param monkeypatch: pytest monkeypatch fixture
    :return: None
    """
    displays = [
        DisplayTarget(
            index=index,
            name=f"显示器 {index}",
            width=1920,
            height=1080,
            x=0,
            y=0,
            is_primary=index == 1,
        )
        for index in range(1, 5)
    ]
    gpus = [
        GPUInfo(index=0, name="Intel UHD", vendor="intel"),
        GPUInfo(index=2, name="NVIDIA RTX", vendor="nvidia"),
    ]
    monkeypatch.setattr(
        "scp_cv.player.headless_launcher.list_display_targets", lambda: displays
    )
    monkeypatch.setattr("scp_cv.player.headless_launcher.enumerate_gpus", lambda: gpus)
    launch_result = build_headless_launch_result(
        window_display_ids={1: 4, 2: 3, 3: 2, 4: 1},
        gpu_id=2,
    )
    assert [target.index for target in launch_result.window_assignments.values()] == [
        4,
        3,
        2,
        1,
    ]
    assert launch_result.selected_gpu == gpus[1]


def test_build_headless_launch_result_rejects_missing_display(monkeypatch: Any) -> None:
    """
    显示器 ID 不存在时应明确报错，避免创建错屏窗口。
    :param monkeypatch: pytest monkeypatch fixture
    :return: None
    """
    displays = [
        DisplayTarget(
            index=1, name="显示器 1", width=1920, height=1080, x=0, y=0, is_primary=True
        ),
    ]
    monkeypatch.setattr(
        "scp_cv.player.headless_launcher.list_display_targets", lambda: displays
    )
    with pytest.raises(ValueError, match="未找到显示器 ID 2"):
        build_headless_launch_result(window_display_ids={}, gpu_id=None)


def test_build_headless_launch_result_rejects_missing_gpu(monkeypatch: Any) -> None:
    """
    GPU ID 不存在时应明确报错，避免现场误以为已绑定目标显卡。
    :param monkeypatch: pytest monkeypatch fixture
    :return: None
    """
    displays = [
        DisplayTarget(
            index=index,
            name=f"显示器 {index}",
            width=1920,
            height=1080,
            x=0,
            y=0,
            is_primary=index == 1,
        )
        for index in range(1, 5)
    ]
    monkeypatch.setattr(
        "scp_cv.player.headless_launcher.list_display_targets", lambda: displays
    )
    monkeypatch.setattr("scp_cv.player.headless_launcher.enumerate_gpus", lambda: [])
    with pytest.raises(ValueError, match="未找到 GPU ID 9"):
        build_headless_launch_result(window_display_ids={}, gpu_id=9)
