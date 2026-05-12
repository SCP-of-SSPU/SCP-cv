#!/user/bin/env python
# -*- coding: UTF-8 -*-
"""
PowerPoint 页面媒体控制辅助函数。
集中处理当前幻灯片音视频 shape 的查找和播放控制，避免 PPT 适配器继续堆积实现。
@Project : SCP-cv
@File : ppt_media.py
@Author : Qintsg
@Date : 2026-05-12
"""

from __future__ import annotations

import logging
from typing import Optional

ALLOWED_MEDIA_ACTIONS = frozenset({"play", "pause", "stop"})


def control_slide_media(
    slideshow_view: Optional[object],
    presentation: Optional[object],
    logger: logging.Logger,
    media_id: str,
    action: str,
    media_index: int = 0,
) -> None:
    """
    控制当前幻灯片中的音视频媒体对象。
    :param slideshow_view: PowerPoint SlideShowView COM 对象
    :param presentation: PowerPoint Presentation COM 对象
    :param logger: 适配器日志器
    :param media_id: 媒体对象标识，可为 PowerPoint shape id
    :param action: 控制动作，支持 play / pause / stop
    :param media_index: 当前页媒体序号，从 1 开始
    :return: None
    """
    normalized_action = action.strip().lower()
    if normalized_action not in ALLOWED_MEDIA_ACTIONS:
        logger.warning("未知 PPT 媒体控制动作：%s", action)
        return
    if slideshow_view is None:
        logger.warning("PPT 放映未运行，无法控制页面媒体")
        return
    player = resolve_media_player(
        slideshow_view, presentation, media_id, media_index
    )
    if player is None:
        logger.warning("未找到 PPT 页面媒体：media_id=%s, index=%d", media_id, media_index)
        return
    try:
        getattr(player, normalized_action.capitalize())()
    except Exception as media_error:
        logger.warning("PPT 页面媒体 %s 执行 %s 失败：%s", media_id, action, media_error)


def resolve_media_player(
    slideshow_view: object,
    presentation: Optional[object],
    media_id: str,
    media_index: int,
) -> Optional[object]:
    """
    根据 shape id 或当前页媒体序号获取 PowerPoint Player 对象。
    :param slideshow_view: PowerPoint SlideShowView COM 对象
    :param presentation: PowerPoint Presentation COM 对象
    :param media_id: 媒体对象标识
    :param media_index: 媒体序号
    :return: PowerPoint Player COM 对象；找不到时返回 None
    """
    for shape_id in candidate_media_shape_ids(
        presentation, slideshow_view, media_id, media_index
    ):
        try:
            return slideshow_view.Player(shape_id)
        except Exception:
            continue
    return None


def candidate_media_shape_ids(
    presentation: Optional[object],
    slideshow_view: object,
    media_id: str,
    media_index: int,
) -> list[int]:
    """
    生成可尝试的媒体 shape id 列表。
    :param presentation: PowerPoint Presentation COM 对象
    :param slideshow_view: PowerPoint SlideShowView COM 对象
    :param media_id: 前端媒体对象标识
    :param media_index: 当前页媒体序号
    :return: shape id 列表
    """
    candidate_ids: list[int] = []
    try:
        parsed_media_id = int(media_id)
    except (TypeError, ValueError):
        parsed_media_id = 0
    if parsed_media_id > 0:
        candidate_ids.append(parsed_media_id)
    candidate_ids.extend(current_slide_media_shape_ids(presentation, slideshow_view))
    if media_index > 0 and len(candidate_ids) >= media_index:
        return [candidate_ids[media_index - 1]] + candidate_ids
    return candidate_ids


def current_slide_media_shape_ids(
    presentation: Optional[object], slideshow_view: object
) -> list[int]:
    """
    枚举当前页可作为媒体控制目标的 shape id。
    :param presentation: PowerPoint Presentation COM 对象
    :param slideshow_view: PowerPoint SlideShowView COM 对象
    :return: 当前页媒体 shape id 列表
    """
    if presentation is None:
        return []
    try:
        current_slide = presentation.Slides(slideshow_view.CurrentShowPosition)
    except Exception:
        return []
    shape_ids: list[int] = []
    for shape_index in range(1, int(current_slide.Shapes.Count) + 1):
        shape = current_slide.Shapes(shape_index)
        try:
            _ = shape.MediaFormat
            shape_ids.append(int(shape.Id))
        except Exception:
            continue
    return shape_ids
