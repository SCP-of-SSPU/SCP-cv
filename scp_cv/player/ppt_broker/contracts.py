#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PowerPoint Broker 的进程间数据合同。
@Project : SCP-cv
@File : contracts.py
@Author : Qintsg
@Date : 2026-07-11
'''
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Protocol


class PptCommand(StrEnum):
    """Broker 支持的 PowerPoint 会话指令。"""

    PLAY = "play"
    PAUSE = "pause"
    STOP = "stop"
    NEXT = "next"
    PREVIOUS = "previous"
    GOTO = "goto"
    RESIZE = "resize"
    CONTROL_MEDIA = "control_media"


class PptShowFormat(StrEnum):
    """PowerPoint 放映缓存输出格式。"""

    PPSX = "ppsx"
    PPS = "pps"


@dataclass(frozen=True, slots=True)
class PptSessionKey:
    """绑定播放器窗口与播放器进程代次的会话键。"""

    window_id: int
    owner_token: str

    def __post_init__(self) -> None:
        if self.window_id <= 0:
            raise ValueError("PPT 会话 window_id 必须大于 0")
        if not self.owner_token.strip():
            raise ValueError("PPT 会话 owner_token 不能为空")


@dataclass(frozen=True, slots=True)
class PptOpenRequest:
    """打开 PowerPoint 放映所需的全部普通数据。"""

    session: PptSessionKey
    uri: str
    parent_hwnd: int
    autoplay: bool = True
    start_slide: int = 1
    source_id: int = 0
    request_id: str = ""

    def __post_init__(self) -> None:
        if not self.uri.strip():
            raise ValueError("PPT 文件路径不能为空")
        if self.parent_hwnd <= 0:
            raise ValueError("PPT 父窗口 HWND 必须大于 0")
        if self.start_slide <= 0:
            raise ValueError("PPT 起始页码必须大于 0")
        if self.source_id < 0:
            raise ValueError("PPT source_id 不能小于 0")


@dataclass(frozen=True, slots=True)
class PptCommandRequest:
    """作用于既有 PowerPoint 会话的控制指令。"""

    session: PptSessionKey
    command: PptCommand
    slide_index: int = 0
    media_id: str = ""
    media_action: str = ""
    media_index: int = 0
    request_id: str = ""

    def __post_init__(self) -> None:
        if self.command is PptCommand.GOTO and self.slide_index <= 0:
            raise ValueError("PPT goto 指令必须提供大于 0 的 slide_index")
        if self.command is PptCommand.CONTROL_MEDIA:
            if self.media_action not in {"play", "pause", "stop"}:
                raise ValueError("PPT 媒体指令必须是 play、pause 或 stop")
            if self.media_index < 0:
                raise ValueError("PPT media_index 不能小于 0")


@dataclass(frozen=True, slots=True)
class PptPreheatRequest:
    """PowerPoint 应用级或文件级预热请求。"""

    uri: str = ""
    source_id: int = 0
    request_id: str = ""

    def __post_init__(self) -> None:
        if self.source_id < 0:
            raise ValueError("PPT source_id 不能小于 0")
        if self.source_id > 0 and not self.uri.strip():
            raise ValueError("文件级 PPT 预热必须提供 uri")


@dataclass(frozen=True, slots=True)
class PptShowExportRequest:
    """把 PowerPoint 源导出为放映格式文件。"""

    source_uri: str
    target_uri: str
    target_format: PptShowFormat
    request_id: str = ""

    def __post_init__(self) -> None:
        if not self.source_uri.strip():
            raise ValueError("PPT 导出源路径不能为空")
        if not self.target_uri.strip():
            raise ValueError("PPT 导出目标路径不能为空")
        target_format = self.target_format
        if not isinstance(target_format, PptShowFormat):
            normalized_format = str(target_format).removeprefix(".").casefold()
            object.__setattr__(self, "target_format", PptShowFormat(normalized_format))
            target_format = self.target_format
        if Path(self.target_uri).suffix.casefold() != f".{target_format.value}":
            raise ValueError(
                "PPT 导出目标扩展名必须与 target_format 一致："
                f"target={self.target_uri}, format={target_format.value}"
            )


@dataclass(frozen=True, slots=True)
class PptSlideExportRequest:
    """把 PowerPoint 各页导出到调用方准备好的目录。"""

    source_uri: str
    output_dir: str
    image_format: str = "PNG"
    request_id: str = ""

    def __post_init__(self) -> None:
        if not self.source_uri.strip():
            raise ValueError("PPT 预览导出源路径不能为空")
        if not self.output_dir.strip():
            raise ValueError("PPT 预览导出目录不能为空")
        normalized_format = self.image_format.strip().upper()
        if normalized_format != "PNG":
            raise ValueError("PPT 逐页导出当前仅支持 PNG")
        object.__setattr__(self, "image_format", normalized_format)


@dataclass(frozen=True, slots=True)
class PptExportResult:
    """PowerPoint 导出任务返回的纯文件路径结果。"""

    paths: tuple[str, ...]
    powerpoint_pid: int = 0


@dataclass(frozen=True, slots=True)
class PptState:
    """不含 COM 对象的 PowerPoint 会话状态快照。"""

    playback_state: str = "idle"
    current_slide: int = 0
    total_slides: int = 0
    error_message: str = ""
    powerpoint_pid: int = 0
    slideshow_hwnd: int = 0
    parent_hwnd: int = 0
    generation: str = ""


@dataclass(frozen=True, slots=True)
class BrokerHealth:
    """Broker 就绪状态。"""

    ready: bool
    generation: str
    pid: int


class PptBroker(Protocol):
    """播放器和测试共同使用的 PowerPoint Broker 接口。"""

    def open(self, request: PptOpenRequest) -> PptState: ...

    def command(self, request: PptCommandRequest) -> PptState: ...

    def get_state(self, session: PptSessionKey) -> PptState: ...

    def close(self, session: PptSessionKey) -> None: ...

    def preheat(self, request: PptPreheatRequest) -> None: ...

    def export_show(self, request: PptShowExportRequest) -> PptExportResult: ...

    def export_slides(self, request: PptSlideExportRequest) -> PptExportResult: ...

    def health(self) -> BrokerHealth: ...

    def shutdown(self) -> None: ...


class PptSessionNotFoundError(LookupError):
    """目标窗口当前没有属于调用方的 PowerPoint 会话。"""


__all__ = [
    "BrokerHealth",
    "PptBroker",
    "PptCommand",
    "PptCommandRequest",
    "PptExportResult",
    "PptOpenRequest",
    "PptPreheatRequest",
    "PptSessionKey",
    "PptSessionNotFoundError",
    "PptShowExportRequest",
    "PptShowFormat",
    "PptSlideExportRequest",
    "PptState",
]
