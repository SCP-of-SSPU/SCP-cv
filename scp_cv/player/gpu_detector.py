#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
GPU 检测与选择模块：枚举系统可用显卡，存储用户选择并生成 mpv/PySide6 配置。
支持 Windows 多显卡场景（Intel 核显 + NVIDIA/AMD 独显），
通过 WMI 查询显卡信息，生成 mpv d3d11-adapter 参数实现指定显卡渲染。
@Project : SCP-cv
@File : gpu_detector.py
@Author : Qintsg
@Date : 2026-04-30
'''
from __future__ import annotations

import json
import logging
import os
import subprocess
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

_VIRTUAL_ADAPTER_KEYWORDS = (
    "microsoft basic",
    "virtual display",
    "virtual adapter",
    "orayidd",
    "indirect display",
    "remote display",
    "rdp",
)

# 模块级存储：用户当前选择的显卡，供各适配器读取
_selected_gpu: Optional[GPUInfo] = None
# 模块级缓存：系统检测到的所有显卡
_cached_gpus: list[GPUInfo] = []


def _is_virtual_adapter(adapter_name: str) -> bool:
    """
    判断显卡名称是否属于虚拟/远程显示适配器。
    :param adapter_name: WMI 返回的显卡名称
    :return: True 表示不应作为渲染显卡提供给用户选择
    """
    normalized_name = adapter_name.lower()
    return any(keyword in normalized_name for keyword in _VIRTUAL_ADAPTER_KEYWORDS)


@dataclass(frozen=True)
class GPUInfo:
    """
    单块显卡的描述信息。
    index: 显卡序号（0-based）
    name: 显卡显示名称（如 "NVIDIA GeForce RTX 4060"）
    vendor: 厂商（nvidia / amd / intel / unknown）
    memory_gb: 显存大小（GB，取整）
    device_id: PNPDeviceID，用于 mpv d3d11-adapter 精确匹配
    """

    index: int
    name: str
    vendor: str = "unknown"
    memory_gb: int = 0
    device_id: str = ""

    @property
    def display_label(self) -> str:
        """显卡选择器中的显示标签。"""
        vendor_icon = {"nvidia": "NVIDIA", "amd": "AMD", "intel": "Intel"}.get(
            self.vendor, ""
        )
        mem_label = f"  {self.memory_gb}GB" if self.memory_gb > 0 else ""
        icon_label = f"[{vendor_icon}] " if vendor_icon else ""
        return f"{icon_label}{self.name}{mem_label}"

    @property
    def mpv_adapter_name(self) -> str:
        """
        mpv d3d11-adapter 参数所需的适配器名称。
        优先使用完整名称精确匹配；PNPDeviceID 作备用。
        """
        return self.name


def enumerate_gpus() -> list[GPUInfo]:
    """
    通过 Windows WMI 枚举系统所有显卡。
    使用 PowerShell Get-CimInstance Win32_VideoController 查询，
    返回按厂商排序的显卡列表（独立显卡优先）。
    :return: GPUInfo 列表
    """
    global _cached_gpus

    if _cached_gpus:
        return _cached_gpus

    gpu_list: list[GPUInfo] = []

    try:
        ps_command = (
            "Get-CimInstance Win32_VideoController | "
            "Select-Object Name, AdapterRAM, PNPDeviceID | "
            "ConvertTo-Json"
        )
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_command],
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )

        if result.returncode != 0 or not result.stdout.strip():
            logger.warning("GPU 枚举失败：PowerShell 返回码=%d", result.returncode)
            _cached_gpus = gpu_list
            return gpu_list

        raw_data = json.loads(result.stdout.strip())
        # 单显卡时 ConvertTo-Json 返回对象而非数组，统一为列表
        if isinstance(raw_data, dict):
            raw_data = [raw_data]

        for idx, gpu_entry in enumerate(raw_data):
            name = str(gpu_entry.get("Name", "") or f"显卡 {idx + 1}").strip()
            if not name or _is_virtual_adapter(name):
                # 跳过虚拟/远程显示适配器，避免用户选择后 mpv 无法绑定真实 GPU。
                continue

            ram_bytes = int(gpu_entry.get("AdapterRAM", 0) or 0)
            mem_gb = round(ram_bytes / (1024 ** 3)) if ram_bytes > 0 else 0
            device_id = str(gpu_entry.get("PNPDeviceID", "") or "").strip()

            name_lower = name.lower()
            if "nvidia" in name_lower or "geforce" in name_lower or "rtx" in name_lower or "gtx" in name_lower or "quadro" in name_lower:
                vendor = "nvidia"
            elif "amd" in name_lower or "radeon" in name_lower or "rx " in name_lower:
                vendor = "amd"
            elif "intel" in name_lower or "uhd" in name_lower or "iris" in name_lower or "arc" in name_lower:
                vendor = "intel"
            else:
                vendor = "unknown"

            gpu_list.append(GPUInfo(
                index=idx,
                name=name,
                vendor=vendor,
                memory_gb=mem_gb,
                device_id=device_id,
            ))
            logger.debug("检测到显卡[%d]：%s（厂商=%s, 显存=%dGB）", idx, name, vendor, mem_gb)

    except json.JSONDecodeError as json_err:
        logger.warning("GPU 枚举 JSON 解析失败：%s", json_err)
    except subprocess.TimeoutExpired:
        logger.warning("GPU 枚举超时")
    except Exception as enum_error:
        logger.warning("GPU 枚举异常：%s", enum_error)

    # 排序：独立显卡（nvidia/amd）优先 → Intel → unknown
    vendor_order = {"nvidia": 0, "amd": 1, "intel": 2, "unknown": 3}
    gpu_list.sort(key=lambda g: (vendor_order.get(g.vendor, 3), g.name))

    # 重新分配 index（统一为排序后的顺序）
    gpu_list = [
        GPUInfo(
            index=new_idx,
            name=g.name,
            vendor=g.vendor,
            memory_gb=g.memory_gb,
            device_id=g.device_id,
        )
        for new_idx, g in enumerate(gpu_list)
    ]

    _cached_gpus = gpu_list
    return gpu_list


def set_selected_gpu(gpu: GPUInfo) -> None:
    """
    设置当前选中显卡为指定 GPUInfo 实例。
    :param gpu: 用户选择的显卡
    """
    global _selected_gpu
    _selected_gpu = gpu
    logger.info("已选择显卡：%s", gpu.display_label)


def get_selected_gpu() -> Optional[GPUInfo]:
    """获取用户当前选择的显卡，未选择时返回 None。"""
    return _selected_gpu


def auto_select_gpu() -> None:
    """
    自动选择最优显卡（独立显卡优先）。
    在未手动选择时，默认优先使用 NVIDIA/AMD 独显。
    """
    global _selected_gpu
    if _selected_gpu is not None:
        return

    gpu_list = enumerate_gpus()
    if not gpu_list:
        logger.warning("未检测到可用显卡，无法自动选择")
        return

    # 优先选择独立显卡
    for gpu in gpu_list:
        if gpu.vendor in ("nvidia", "amd"):
            _selected_gpu = gpu
            logger.info("自动选择显卡：%s", gpu.display_label)
            return

    # 无独显则选择第一个
    _selected_gpu = gpu_list[0]
    logger.info("未检测到独显，自动选择：%s", gpu_list[0].display_label)


def get_mpv_gpu_options() -> dict[str, str]:
    """
    根据选中显卡生成 mpv 初始化参数。
    当选中特定显卡时，强制使用 d3d11 渲染 API 并指定适配器名称。
    :return: mpv 选项字典，可直接解包传入 mpv.MPV()
    """
    gpu = get_selected_gpu()
    if gpu is None:
        return {}

    options: dict[str, str] = {}
    options["gpu-api"] = "d3d11"
    options["gpu-context"] = "d3d11"

    # mpv d3d11-adapter 通过显卡名称匹配选择特定 GPU
    adapter_name = gpu.mpv_adapter_name
    if adapter_name:
        options["d3d11-adapter"] = adapter_name
        logger.debug("mpv GPU 配置：d3d11-adapter=%s", adapter_name)

    return options
