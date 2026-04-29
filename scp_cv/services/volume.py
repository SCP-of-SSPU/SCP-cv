#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
系统音量管理服务，与 Windows 系统音量同步。
@Project : SCP-cv
@File : volume.py
@Author : Qintsg
@Date : 2026-04-29
'''
from __future__ import annotations

import logging

from scp_cv.apps.playback.models import RuntimeState

logger = logging.getLogger(__name__)


class VolumeError(Exception):
    """音量操作过程中的业务异常。"""


def get_system_volume() -> dict[str, object]:
    """
    获取当前系统音量状态。
    :return: 包含 level 和 muted 的字典
    """
    runtime = RuntimeState.get_instance()
    return {
        "level": runtime.volume_level,
        "muted": runtime.volume_level == 0,
    }


def set_system_volume(level: int) -> dict[str, object]:
    """
    设置系统音量。
    :param level: 音量等级（0-100）
    :return: 更新后的音量状态
    :raises VolumeError: 音量值无效时
    """
    level = max(0, min(100, int(level)))
    runtime = RuntimeState.get_instance()
    runtime.volume_level = level
    runtime.save(update_fields=["volume_level", "updated_at"])
    logger.info("系统音量设置为 %d", level)
    return {"level": level, "muted": level == 0}
