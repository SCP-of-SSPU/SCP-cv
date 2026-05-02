#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
媒体源类型识别工具，集中维护扩展名映射、MIME 推断和媒体业务异常。
@Project : SCP-cv
@File : media_types.py
@Author : Qintsg
@Date : 2026-05-02
'''
from __future__ import annotations

import mimetypes
from pathlib import Path

from scp_cv.apps.playback.models import SourceType


class MediaError(Exception):
    """媒体源操作过程中的业务异常。"""


# 源类型与文件扩展名映射集中放置，避免上传、本地注册和测试各自维护一份判断逻辑。
_EXTENSION_SOURCE_TYPE_MAP: dict[str, str] = {
    ".pptx": SourceType.PPT,
    ".ppt": SourceType.PPT,
    ".ppsx": SourceType.PPT,
    ".pps": SourceType.PPT,
    ".mp4": SourceType.VIDEO,
    ".mkv": SourceType.VIDEO,
    ".avi": SourceType.VIDEO,
    ".mov": SourceType.VIDEO,
    ".wmv": SourceType.VIDEO,
    ".flv": SourceType.VIDEO,
    ".webm": SourceType.VIDEO,
    ".m4v": SourceType.VIDEO,
    ".mp3": SourceType.AUDIO,
    ".wav": SourceType.AUDIO,
    ".flac": SourceType.AUDIO,
    ".aac": SourceType.AUDIO,
    ".ogg": SourceType.AUDIO,
    ".wma": SourceType.AUDIO,
    ".m4a": SourceType.AUDIO,
    ".png": SourceType.IMAGE,
    ".jpg": SourceType.IMAGE,
    ".jpeg": SourceType.IMAGE,
    ".gif": SourceType.IMAGE,
    ".bmp": SourceType.IMAGE,
    ".webp": SourceType.IMAGE,
    ".svg": SourceType.IMAGE,
}


def detect_source_type(file_path: str) -> str:
    """
    根据文件扩展名自动检测源类型。
    :param file_path: 文件路径或文件名
    :return: SourceType 值
    :raises MediaError: 无法识别扩展名时
    """
    extension = Path(file_path).suffix.lower()
    detected_type = _EXTENSION_SOURCE_TYPE_MAP.get(extension)
    if detected_type is None:
        raise MediaError(f"无法识别的文件类型：{extension}")
    return detected_type


def guess_mime_type(file_name: str) -> str:
    """
    根据文件名猜测 MIME 类型。
    :param file_name: 文件名或路径
    :return: 可用于下载响应的 MIME 类型
    """
    mime_type, _ = mimetypes.guess_type(file_name)
    return mime_type or "application/octet-stream"
