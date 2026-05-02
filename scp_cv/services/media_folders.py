#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
媒体文件夹管理服务，负责文件夹列表、创建、更新和删除归档。
@Project : SCP-cv
@File : media_folders.py
@Author : Qintsg
@Date : 2026-05-02
'''
from __future__ import annotations

import logging
from typing import Optional

from scp_cv.apps.playback.models import MediaFolder, MediaSource
from scp_cv.services.media_types import MediaError

logger = logging.getLogger(__name__)


def list_folders() -> list[dict[str, object]]:
    """
    获取所有文件夹列表。
    :return: 文件夹字典列表
    """
    return list(MediaFolder.objects.values(
        "id", "name", "parent_id", "created_at", "updated_at",
    ))


def create_folder(name: str, parent_id: Optional[int] = None) -> MediaFolder:
    """
    创建文件夹。
    :param name: 文件夹名称
    :param parent_id: 父文件夹 ID（可选）
    :return: 创建的 MediaFolder 实例
    :raises MediaError: 名称为空或父文件夹不存在时
    """
    if not name.strip():
        raise MediaError("文件夹名称不能为空")
    parent = None
    if parent_id:
        try:
            parent = MediaFolder.objects.get(pk=parent_id)
        except MediaFolder.DoesNotExist as not_found:
            raise MediaError(f"父文件夹 id={parent_id} 不存在") from not_found
    folder = MediaFolder.objects.create(name=name.strip(), parent=parent)
    logger.info("创建文件夹「%s」(id=%d)", folder.name, folder.pk)
    return folder


def update_folder(folder_id: int, name: Optional[str] = None, parent_id: Optional[int] = None) -> MediaFolder:
    """
    更新文件夹。
    :param folder_id: 文件夹 ID
    :param name: 新名称
    :param parent_id: 新父文件夹 ID
    :return: 更新后的文件夹
    :raises MediaError: 文件夹不存在时
    """
    try:
        folder = MediaFolder.objects.get(pk=folder_id)
    except MediaFolder.DoesNotExist as not_found:
        raise MediaError(f"文件夹 id={folder_id} 不存在") from not_found
    if name is not None:
        if not name.strip():
            raise MediaError("文件夹名称不能为空")
        folder.name = name.strip()
    if parent_id is not None:
        if parent_id == folder_id:
            raise MediaError("不能将文件夹设为自己的子文件夹")
        folder.parent_id = parent_id if parent_id > 0 else None
    folder.save()
    logger.info("更新文件夹「%s」(id=%d)", folder.name, folder.pk)
    return folder


def delete_folder(folder_id: int) -> None:
    """
    删除文件夹，其中的源自动归到根目录。
    :param folder_id: 文件夹 ID
    :raises MediaError: 文件夹不存在时
    """
    try:
        folder = MediaFolder.objects.get(pk=folder_id)
    except MediaFolder.DoesNotExist as not_found:
        raise MediaError(f"文件夹 id={folder_id} 不存在") from not_found
    # 删除文件夹前先收集完整子树，避免级联删除导致源记录失去归档入口。
    descendant_ids = _collect_folder_tree_ids(folder)
    MediaSource.objects.filter(folder_id__in=descendant_ids).update(folder=None)
    folder_name = folder.name
    folder.delete()
    logger.info("删除文件夹「%s」", folder_name)


def _collect_folder_tree_ids(folder: MediaFolder) -> list[int]:
    """
    递归收集文件夹及其所有子文件夹 ID。
    :param folder: 根文件夹
    :return: 文件夹主键列表
    """
    folder_ids = [folder.pk]
    for child in folder.children.all():
        folder_ids.extend(_collect_folder_tree_ids(child))
    return folder_ids
