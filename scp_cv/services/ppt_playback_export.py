#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PPT 放映格式导出服务：统一委托唯一 PowerPoint Broker。
@Project : SCP-cv
@File : ppt_playback_export.py
@Author : Qintsg
@Date : 2026-05-31
'''
from __future__ import annotations

import logging
import uuid
from pathlib import Path

from django.conf import settings

from scp_cv.player.ppt_broker import (
    PptBrokerClient,
    PptShowExportRequest,
    PptShowFormat,
)

logger = logging.getLogger(__name__)

class PptPlaybackExportError(RuntimeError):
    """PPT 放映格式导出失败。"""


def export_show_file(
    source_path: Path,
    target_path: Path,
    target_extension: str,
    preferred_backend: str = "powerpoint",
) -> str:
    """
    使用 PowerPoint 导出 show-format 文件。

    :param source_path: 源文件路径
    :param target_path: 目标 .ppsx/.pps 路径
    :param target_extension: 目标扩展名
    :param preferred_backend: 旧参数兼容；当前忽略并始终使用 PowerPoint
    :return: 实际成功导出的后端，固定为 powerpoint
    """
    del preferred_backend
    target_path.unlink(missing_ok=True)
    target_format = _broker_show_format(target_extension)
    try:
        result = PptBrokerClient(
            timeout_seconds=_export_timeout_seconds(),
        ).export_show(
            PptShowExportRequest(
                source_uri=str(source_path),
                target_uri=str(target_path),
                target_format=target_format,
                request_id=uuid.uuid4().hex,
            )
        )
    except Exception as export_error:
        target_path.unlink(missing_ok=True)
        raise PptPlaybackExportError(
            "PowerPoint Broker 导出放映缓存失败；请确认 runall 正在运行，"
            "或先执行 manage.py run_ppt_broker，并检查 Broker 日志。"
            f"原始错误：{export_error}"
        ) from export_error
    if not target_path.is_file():
        raise PptPlaybackExportError(
            "PowerPoint Broker 未生成目标文件；请检查目标目录写权限和 Broker 日志："
            f"{target_path}"
        )
    logger.info(
        "PPT 放映格式缓存导出成功：%s -> %s（powerpoint_pid=%d）",
        source_path,
        target_path,
        result.powerpoint_pid,
    )
    return "powerpoint"


def _broker_show_format(target_extension: str) -> PptShowFormat:
    """把目标扩展名转换为 Broker 放映格式合同。"""
    normalized_extension = target_extension.casefold()
    if normalized_extension == ".ppsx":
        return PptShowFormat.PPSX
    if normalized_extension == ".pps":
        return PptShowFormat.PPS
    raise PptPlaybackExportError(f"不支持的 PPT 放映输出格式：{target_extension}")


def _export_timeout_seconds() -> float:
    """
    读取 PPT 播放缓存导出超时。

    :return: 超时秒数
    """
    raw_value = getattr(settings, "PPT_PLAYBACK_EXPORT_TIMEOUT_SECONDS", 180.0)
    try:
        return max(1.0, float(raw_value))
    except (TypeError, ValueError):
        return 180.0


__all__ = ["PptPlaybackExportError", "export_show_file"]
