#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
网页媒体源服务：URL 规范化、创建与预热开关更新。
@Project : SCP-cv
@File : media_web.py
@Author : Qintsg
@Date : 2026-05-09
'''
from __future__ import annotations

import logging
from typing import Optional

from scp_cv.apps.playback.models import MediaFolder, MediaSource, SourceType
from scp_cv.services.media_types import MediaError

logger = logging.getLogger(__name__)


def add_web_url(
    url: str,
    display_name: Optional[str] = None,
    folder_id: Optional[int] = None,
    preheat_enabled: bool = True,
    keep_alive: Optional[bool] = None,
) -> MediaSource:
    """
    通过 URL 添加网页类型媒体源。
    :param url: 网页 URL（如 https://example.com）
    :param display_name: 显示名称，默认使用 URL
    :param folder_id: 所属文件夹 ID
    :param preheat_enabled: 是否在播放器启动时预热该网页
    :param keep_alive: 旧字段兼容；传入时覆盖 preheat_enabled
    :return: 创建的 MediaSource 实例
    :raises MediaError: URL 为空时
    """
    normalized_url = normalize_web_url(url)
    if not normalized_url:
        raise MediaError("URL 不能为空")

    if display_name is None:
        display_name = normalized_url[:80]

    folder = _optional_folder(folder_id)
    enabled = bool(preheat_enabled if keep_alive is None else keep_alive)
    media_source = MediaSource.objects.create(
        source_type=SourceType.WEB,
        name=display_name,
        uri=normalized_url,
        is_available=True,
        mime_type="text/html",
        folder=folder,
        keep_alive=enabled,
    )

    logger.info("通过 URL 添加网页媒体源「%s」→ %s（preheat=%s）", display_name, normalized_url, enabled)
    return media_source


def update_source(
    source_id: int,
    name: Optional[str] = None,
    uri: Optional[str] = None,
    preheat_enabled: Optional[bool] = None,
    keep_alive: Optional[bool] = None,
) -> MediaSource:
    """
    更新媒体源可编辑字段。
    :param source_id: 媒体源 ID
    :param name: 新显示名称（None 表示不修改）
    :param uri: 新 URI / URL（仅对网页源生效）
    :param preheat_enabled: 是否启用网页预热（None 表示不修改）
    :param keep_alive: 旧字段兼容；传入时覆盖 preheat_enabled
    :return: 更新后的 MediaSource 实例
    :raises MediaError: 源不存在或参数非法时
    """
    try:
        source = MediaSource.objects.get(pk=source_id)
    except MediaSource.DoesNotExist as not_found:
        raise MediaError(f"媒体源 id={source_id} 不存在") from not_found

    update_fields: list[str] = []
    _apply_source_name(source, name, update_fields)
    _apply_web_uri(source, uri, update_fields)

    enabled = preheat_enabled if keep_alive is None else keep_alive
    if enabled is not None and source.keep_alive != bool(enabled):
        source.keep_alive = bool(enabled)
        update_fields.append("keep_alive")

    if update_fields:
        source.save(update_fields=update_fields)
        logger.info("更新媒体源「%s」字段：%s", source.name, ", ".join(update_fields))
    return source


def normalize_web_url(url: str) -> str:
    """
    规范化网页源 URL，未写协议时默认使用 http 以兼容局域网设备。
    :param url: 用户输入的网页地址
    :return: 可交给 QWebEngineView 加载的 URL，空输入返回空字符串
    """
    stripped_url = url.strip()
    if not stripped_url:
        return ""
    lower_url = stripped_url.lower()
    if lower_url.startswith(("http://", "https://", "file://", "about:")):
        return stripped_url
    if len(stripped_url) > 2 and stripped_url[1] == ":":
        return f"file:///{stripped_url}"
    return f"http://{stripped_url}"


def _optional_folder(folder_id: Optional[int]) -> Optional[MediaFolder]:
    """
    按 ID 解析可选媒体文件夹，缺失或不存在时返回 None。
    :param folder_id: 文件夹 ID
    :return: MediaFolder 或 None
    """
    if not folder_id:
        return None
    try:
        return MediaFolder.objects.get(pk=folder_id)
    except MediaFolder.DoesNotExist:
        return None


def _apply_source_name(source: MediaSource, name: Optional[str], update_fields: list[str]) -> None:
    """
    校验并写入显示名称。
    :param source: 待更新的媒体源
    :param name: 新名称；None 表示不修改
    :param update_fields: 已变更字段收集器
    :return: None
    """
    if name is None:
        return
    trimmed_name = name.strip()
    if not trimmed_name:
        raise MediaError("显示名称不能为空")
    if len(trimmed_name) > 255:
        raise MediaError("显示名称过长（≤ 255 字符）")
    if source.name != trimmed_name:
        source.name = trimmed_name
        update_fields.append("name")


def _apply_web_uri(source: MediaSource, uri: Optional[str], update_fields: list[str]) -> None:
    """
    仅允许网页源通过编辑接口修改 URI。
    :param source: 待更新的媒体源
    :param uri: 新 URI；None 表示不修改
    :param update_fields: 已变更字段收集器
    :return: None
    """
    if uri is None or source.source_type != SourceType.WEB:
        return
    normalized_uri = normalize_web_url(uri)
    if not normalized_uri:
        raise MediaError("网页 URL 不能为空")
    if source.uri != normalized_uri:
        source.uri = normalized_uri
        update_fields.append("uri")
