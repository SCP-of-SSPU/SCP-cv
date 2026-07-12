#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PowerPoint 放映窗口标题归一化与请求文件匹配。
@Project : SCP-cv
@File : window_titles.py
@Author : Qintsg
@Date : 2026-07-11
'''
from __future__ import annotations

import re
import unicodedata
from pathlib import Path

_SLIDESHOW_TITLE_PREFIXES = (
    "powerpoint slide show -",
    "powerpoint slide show:",
    "powerpoint 幻灯片放映 -",
    "powerpoint 幻灯片放映:",
    "powerpoint幻灯片放映 -",
    "powerpoint幻灯片放映:",
    "slide show -",
    "slide show:",
    "slideshow -",
    "slideshow:",
    "幻灯片放映 -",
    "幻灯片放映:",
)


def normalize_window_title(title: str) -> str:
    """对窗口标题做 NFKC、大小写和连续空白归一。"""
    normalized = unicodedata.normalize("NFKC", title).casefold().strip()
    return re.sub(r"\s+", " ", normalized)


def looks_like_slideshow_title(normalized_title: str) -> bool:
    """识别中英文 PowerPoint 放映标题前缀。"""
    normalized_punctuation = normalized_title.replace("：", ":")
    normalized_punctuation = normalized_punctuation.replace("—", "-").replace(
        "–",
        "-",
    )
    return any(
        normalized_punctuation.startswith(prefix)
        for prefix in _SLIDESHOW_TITLE_PREFIXES
    )


def matches_expected_presentation_title(title: str, expected_name: str) -> bool:
    """校验 fallback 候选标题包含本次请求的演示文稿文件名。"""
    normalized_expected = normalize_window_title(Path(expected_name).name)
    if not normalized_expected:
        return True
    expected_stem = normalize_window_title(Path(normalized_expected).stem)
    normalized_title = normalize_window_title(title)
    return normalized_expected in normalized_title or (
        bool(expected_stem) and expected_stem in normalized_title
    )


__all__ = [
    "looks_like_slideshow_title",
    "matches_expected_presentation_title",
    "normalize_window_title",
]
