#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
LibreOffice PPT 页面媒体控制工具，通过 XSlideShow 的 shape activity 控制媒体形状。
@Project : SCP-cv
@File : ppt_libreoffice_media.py
@Author : Qintsg
@Date : 2026-05-26
'''
from __future__ import annotations

import logging
import re
from typing import Optional


def control_libreoffice_media(
    controller: object,
    document: Optional[object],
    logger: logging.Logger,
    media_id: str,
    action: str,
    media_index: int,
    current_slide_index: int,
) -> None:
    """
    控制当前页 LibreOffice 媒体形状。
    :param controller: LibreOffice XSlideShowController
    :param document: LibreOffice 文档对象，用于控制器无法返回当前页时兜底
    :param logger: 日志器
    :param media_id: 前端媒体对象标识
    :param action: 控制动作（play / pause / stop）
    :param media_index: 当前页媒体序号，1-based
    :param current_slide_index: 当前页码，1-based
    :return: None
    """
    normalized_action = action.lower().strip()
    if normalized_action not in {"play", "pause", "stop"}:
        logger.warning("不支持的 LibreOffice PPT 媒体控制动作：%s", action)
        return

    slide_show = _get_slide_show(controller)
    if slide_show is None:
        logger.warning("LibreOffice PPT 媒体控制失败：未获取到 XSlideShow")
        return

    media_shape = resolve_libreoffice_media_shape(
        controller,
        document,
        media_id,
        media_index,
        current_slide_index,
    )
    if media_shape is None:
        logger.warning(
            "LibreOffice PPT 当前页未找到媒体形状：media_id=%s, media_index=%d",
            media_id,
            media_index,
        )
        return

    try:
        if normalized_action == "play":
            _resume_slide_show_if_needed(slide_show)
            slide_show.startShapeActivity(media_shape)
        elif normalized_action == "pause":
            _pause_slide_show(slide_show)
        elif normalized_action == "stop":
            slide_show.stopShapeActivity(media_shape)
    except Exception as media_error:
        logger.warning(
            "LibreOffice PPT 媒体控制失败：media_id=%s, media_index=%d, action=%s, error=%s",
            media_id,
            media_index,
            action,
            media_error,
        )


def resolve_libreoffice_media_shape(
    controller: object,
    document: Optional[object],
    media_id: str,
    media_index: int,
    current_slide_index: int,
) -> Optional[object]:
    """
    从当前页解析目标 LibreOffice 媒体形状。
    :param controller: LibreOffice XSlideShowController
    :param document: LibreOffice 文档对象
    :param media_id: 前端媒体对象标识
    :param media_index: 当前页媒体序号，1-based
    :param current_slide_index: 当前页码，1-based
    :return: 媒体 shape；未找到时返回 None
    """
    current_slide = _current_slide(controller, document, current_slide_index)
    if current_slide is None:
        return None
    media_shapes = list(_iter_media_shapes(current_slide))
    if not media_shapes:
        return None

    requested_index = media_index or _media_index_from_id(media_id)
    if requested_index > 0 and requested_index <= len(media_shapes):
        return media_shapes[requested_index - 1]
    matched_shape = _shape_by_identifier(media_shapes, media_id)
    if matched_shape is not None:
        return matched_shape
    if len(media_shapes) == 1:
        return media_shapes[0]
    return None


def _get_slide_show(controller: object) -> Optional[object]:
    """
    获取 XSlideShow 对象。
    :param controller: LibreOffice XSlideShowController
    :return: XSlideShow；不可用时返回 None
    """
    try:
        return controller.getSlideShow()  # type: ignore[attr-defined]
    except Exception:
        return None


def _current_slide(
    controller: object,
    document: Optional[object],
    current_slide_index: int,
) -> Optional[object]:
    """
    获取当前放映页。
    :param controller: LibreOffice XSlideShowController
    :param document: LibreOffice 文档对象
    :param current_slide_index: 当前页码，1-based
    :return: 当前页对象；不可用时返回 None
    """
    try:
        current_slide = controller.getCurrentSlide()  # type: ignore[attr-defined]
        if current_slide is not None:
            return current_slide
    except Exception:
        pass
    if document is None or current_slide_index <= 0:
        return None
    try:
        return document.getDrawPages().getByIndex(current_slide_index - 1)  # type: ignore[attr-defined]
    except Exception:
        return None


def _iter_media_shapes(shape_container: object) -> list[object]:
    """
    递归枚举当前页中的媒体形状。
    :param shape_container: DrawPage、GroupShape 或类似 XShapes 容器
    :return: 媒体 shape 列表
    """
    media_shapes: list[object] = []
    try:
        count = int(shape_container.getCount())  # type: ignore[attr-defined]
    except Exception:
        return media_shapes
    for shape_index in range(count):
        try:
            shape = shape_container.getByIndex(shape_index)  # type: ignore[attr-defined]
        except Exception:
            continue
        if _shape_has_media(shape):
            media_shapes.append(shape)
        media_shapes.extend(_iter_media_shapes(shape))
    return media_shapes


def _shape_has_media(shape: object) -> bool:
    """
    判断 shape 是否为 LibreOffice 媒体形状。
    :param shape: UNO shape
    :return: True 表示可尝试 shape activity 媒体控制
    """
    media_url = _shape_property(shape, "MediaURL")
    if isinstance(media_url, str) and media_url:
        return True
    shape_type = _shape_type(shape).lower()
    return "mediashape" in shape_type or shape_type.endswith("media")


def _shape_by_identifier(media_shapes: list[object], media_id: str) -> Optional[object]:
    """
    按 shape 名称或媒体 URL 匹配前端媒体标识。
    :param media_shapes: 当前页媒体形状列表
    :param media_id: 前端媒体对象标识
    :return: 匹配的 shape；未命中时返回 None
    """
    normalized_id = media_id.strip().lower()
    if not normalized_id:
        return None
    for shape in media_shapes:
        candidates = [
            _shape_property(shape, "Name"),
            _shape_property(shape, "Title"),
            _shape_property(shape, "Description"),
            _shape_property(shape, "MediaURL"),
        ]
        if any(normalized_id in str(candidate).lower() for candidate in candidates if candidate):
            return shape
    return None


def _media_index_from_id(media_id: str) -> int:
    """
    从 page-1-media-2 这类标识中解析媒体序号。
    :param media_id: 前端媒体对象标识
    :return: 1-based 媒体序号；无法解析时返回 0
    """
    match = re.search(r"(?:^|-)media-(\d+)$", media_id.strip().lower())
    if match is None:
        return 0
    try:
        return max(0, int(match.group(1)))
    except ValueError:
        return 0


def _shape_property(shape: object, property_name: str) -> object:
    """
    安全读取 UNO shape 属性。
    :param shape: UNO shape
    :param property_name: 属性名
    :return: 属性值；读取失败返回空字符串
    """
    try:
        return getattr(shape, property_name)
    except Exception:
        pass
    try:
        return shape.getPropertyValue(property_name)  # type: ignore[attr-defined]
    except Exception:
        return ""


def _shape_type(shape: object) -> str:
    """
    读取 UNO shape 类型。
    :param shape: UNO shape
    :return: shape type 字符串
    """
    try:
        return str(shape.getShapeType())  # type: ignore[attr-defined]
    except Exception:
        return str(_shape_property(shape, "ShapeType") or "")


def _pause_slide_show(slide_show: object) -> None:
    """
    暂停当前 slideshow 中正在运行的媒体/动画。
    :param slide_show: XSlideShow
    :return: None
    """
    pause_method = getattr(slide_show, "pause", None)
    if pause_method is not None:
        pause_method(True)


def _resume_slide_show_if_needed(slide_show: object) -> None:
    """
    恢复被 pause(true) 暂停的 slideshow。
    :param slide_show: XSlideShow
    :return: None
    """
    pause_method = getattr(slide_show, "pause", None)
    if pause_method is not None:
        pause_method(False)


__all__ = [
    "control_libreoffice_media",
    "resolve_libreoffice_media_shape",
]
