#!/user/bin/env python
# -*- coding: UTF-8 -*-
"""
播放器命令行启动辅助函数。
根据显示器 ID 和 GPU ID 构造 LauncherResult，跳过交互式启动器 GUI。
@Project : SCP-cv
@File : headless_launcher.py
@Author : Qintsg
@Date : 2026-05-12
"""

from __future__ import annotations
from scp_cv.player.gpu_detector import GPUInfo, enumerate_gpus
from scp_cv.player.launcher_gui import LauncherResult, TOTAL_WINDOWS
from scp_cv.services.display import DisplayTarget, list_display_targets


def build_headless_launch_result(
    window_display_ids: dict[int, int],
    gpu_id: int | None,
) -> LauncherResult:
    """
    根据命令行显示器配置构造播放器启动结果。
    :param window_display_ids: 窗口编号到显示器 ID 的映射；未提供时默认窗口 N -> 显示器 N
    :param gpu_id: GPU ID；None 表示使用系统默认 GPU
    :return: 可直接传给播放器启动流程的 LauncherResult
    :raises ValueError: 显示器或 GPU ID 不存在时
    """
    display_targets = list_display_targets()
    display_by_id = {
        display_target.index: display_target for display_target in display_targets
    }
    window_assignments: dict[int, DisplayTarget] = {}
    for window_id in range(1, TOTAL_WINDOWS + 1):
        requested_display_id = int(window_display_ids.get(window_id) or window_id)
        display_target = display_by_id.get(requested_display_id)
        if display_target is None:
            raise ValueError(
                f"未找到显示器 ID {requested_display_id}，无法创建窗口 {window_id}"
            )
        window_assignments[window_id] = display_target
    return LauncherResult(
        window_assignments=window_assignments,
        selected_gpu=resolve_headless_gpu(gpu_id),
    )


def resolve_headless_gpu(gpu_id: int | None) -> GPUInfo | None:
    """
    根据命令行 GPU ID 查找 GPUInfo。
    :param gpu_id: GPU ID；None 表示交给系统默认选择
    :return: GPUInfo 或 None
    :raises ValueError: GPU ID 不存在时
    """
    if gpu_id is None:
        return None
    gpu_list = enumerate_gpus()
    matched_gpu = next((gpu for gpu in gpu_list if gpu.index == gpu_id), None)
    if matched_gpu is None:
        raise ValueError(f"未找到 GPU ID {gpu_id}")
    return matched_gpu
