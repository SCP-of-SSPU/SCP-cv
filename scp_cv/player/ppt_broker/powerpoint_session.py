#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PowerPoint Broker STA 内部 COM 会话记录。
@Project : SCP-cv
@File : powerpoint_session.py
@Author : Qintsg
@Date : 2026-07-11
'''
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from scp_cv.player.ppt_broker.contracts import PptOpenRequest


@dataclass(slots=True)
class PowerPointComSession:
    """仅存活于 Broker STA，任何 COM 对象都不会跨进程传递。"""

    request: PptOpenRequest
    presentation: object
    total_slides: int
    owner_token: int
    slideshow_window: object | None = None
    view: object | None = None
    hwnd: int = 0
    current_slide: int = 1
    playback_state: str = "stopped"


def presentation_window_name(presentation: object, source_uri: str) -> str:
    """返回 Untitled Presentation 的实际窗口名，读取失败时退回源文件名。"""
    try:
        presentation_name = str(presentation.Name).strip()  # type: ignore[attr-defined]
    except Exception:
        presentation_name = ""
    return presentation_name or Path(source_uri).name


def preheat_key(source_id: int, uri: str) -> tuple[int, str]:
    """按 Windows 路径语义生成文件级预热去重键。"""
    return source_id, os.path.normcase(str(Path(uri).resolve(strict=False)))


__all__ = ["PowerPointComSession", "preheat_key", "presentation_window_name"]
