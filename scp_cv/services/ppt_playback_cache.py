#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PPT 放映格式缓存服务：用 PowerPoint 将演示文稿导出为播放专用 .ppsx/.pps 副本。
@Project : SCP-cv
@File : ppt_playback_cache.py
@Author : Qintsg
@Date : 2026-05-31
'''
from __future__ import annotations

import hashlib
import logging
import shutil
import zipfile
from pathlib import Path

from django.conf import settings
from django.utils import timezone

from scp_cv.apps.playback.models import MediaSource, SourceType
from scp_cv.services.ppt_playback_export import export_show_file

logger = logging.getLogger(__name__)

PPT_PLAYBACK_METADATA_KEY = "ppt_playback"
_CACHE_ROOT = "ppt_playback"
_MODERN_EXTENSIONS = {".pptx", ".pptm", ".ppsx", ".ppsm", ".potx", ".potm", ".odp"}
_LEGACY_EXTENSIONS = {".ppt", ".pps", ".pot"}


class PptPlaybackCacheError(RuntimeError):
    """PPT 放映格式缓存生成失败。"""


def prepare_ppt_playback_cache(
    source: MediaSource,
    preferred_backend: str | None = None,
    force: bool = False,
) -> dict[str, object]:
    """
    为 PPT 源生成播放专用 show-format 文件。

    :param source: PPT 媒体源
    :param preferred_backend: 旧参数兼容；当前忽略并始终使用 PowerPoint
    :param force: 是否强制重新导出
    :return: 写入 MediaSource.metadata 的 ppt_playback 字段
    """
    if source.source_type != SourceType.PPT:
        return {}

    metadata = dict(source.metadata or {})
    try:
        payload = _build_playback_cache_payload(source, preferred_backend, force)
    except Exception as cache_error:
        logger.warning("PPT 放映格式缓存生成失败：source_id=%s, error=%s", source.pk, cache_error)
        payload = _failed_payload(source, preferred_backend, str(cache_error))

    metadata[PPT_PLAYBACK_METADATA_KEY] = payload
    source.metadata = metadata
    source.save(update_fields=["metadata"])
    return payload


def resolve_ppt_playback_uri(source: MediaSource) -> str:
    """
    获取 PPT 播放时应使用的 URI，优先返回已生成的 .ppsx/.pps 副本。

    :param source: 媒体源
    :return: 播放 URI；无可用缓存时返回原始 source.uri
    """
    if source.source_type != SourceType.PPT:
        return source.uri
    cache_info = dict((source.metadata or {}).get(PPT_PLAYBACK_METADATA_KEY) or {})
    if cache_info.get("status") != "ready":
        return source.uri
    cached_path = _cache_path_from_metadata(cache_info)
    if cached_path is None or not cached_path.is_file():
        return source.uri
    return str(cached_path)


def cleanup_ppt_playback_cache(source_id: int) -> None:
    """
    删除指定 PPT 源的播放格式缓存目录。

    :param source_id: MediaSource 主键
    :return: None
    """
    cache_dir = _cache_dir_for_source(source_id)
    if cache_dir.exists():
        shutil.rmtree(cache_dir, ignore_errors=True)
        logger.info("删除 PPT 放映格式缓存：%s", cache_dir)


def _build_playback_cache_payload(
    source: MediaSource,
    preferred_backend: str | None,
    force: bool,
) -> dict[str, object]:
    """
    构建并生成 PPT 播放缓存 payload。

    :param source: PPT 媒体源
    :param preferred_backend: 首选导出后端
    :param force: 是否强制重建
    :return: ready 状态 payload
    """
    source_path = Path(source.uri)
    if not source_path.is_file():
        raise PptPlaybackCacheError(f"PPT 源文件不存在：{source_path}")
    if not _is_export_candidate(source_path):
        raise PptPlaybackCacheError(f"PPT 文件不适合自动导出放映格式：{source_path.suffix}")
    source_digest = _file_digest(source_path)
    target_extension = _target_extension_for_source(source_path)
    if not target_extension:
        raise PptPlaybackCacheError(f"不支持的 PPT 放映格式导出源：{source_path.suffix}")

    backend = "powerpoint"
    existing_payload = dict((source.metadata or {}).get(PPT_PLAYBACK_METADATA_KEY) or {})
    existing_path = _cache_path_from_metadata(existing_payload)
    if (
        not force
        and existing_payload.get("status") == "ready"
        and existing_payload.get("source_digest") == source_digest
        and existing_payload.get("format") == target_extension.lstrip(".")
        and existing_payload.get("backend") == backend
        and existing_path is not None
        and existing_path.is_file()
    ):
        return existing_payload

    cache_dir = _cache_dir_for_source(source.pk)
    cache_dir.mkdir(parents=True, exist_ok=True)
    target_path = cache_dir / f"{source_digest[:16]}{target_extension}"
    actual_backend = export_show_file(source_path, target_path, target_extension)
    _remove_other_cache_files(cache_dir, target_path)
    return {
        "status": "ready",
        "source_digest": source_digest,
        "backend": actual_backend,
        "format": target_extension.lstrip("."),
        "path": str(target_path),
        "relative_path": str(target_path.relative_to(settings.MEDIA_ROOT)).replace("\\", "/"),
        "generated_at": timezone.now().isoformat(),
        "error": "",
        "original_extension": source_path.suffix.lower(),
    }


def _target_extension_for_source(source_path: Path) -> str:
    """
    根据源扩展名选择播放缓存格式。

    :param source_path: 源文件路径
    :return: .ppsx、.pps 或空字符串
    """
    suffix = source_path.suffix.lower()
    if suffix in _MODERN_EXTENSIONS:
        return ".ppsx"
    if suffix in _LEGACY_EXTENSIONS:
        return ".pps"
    return ""


def _is_export_candidate(source_path: Path) -> bool:
    """
    判断文件是否适合交给 PowerPoint 自动导出。

    :param source_path: 源文件路径
    :return: True 表示可尝试导出
    """
    suffix = source_path.suffix.lower()
    if suffix in _LEGACY_EXTENSIONS:
        return True
    if suffix not in _MODERN_EXTENSIONS:
        return False
    if suffix == ".odp":
        return True
    try:
        with zipfile.ZipFile(source_path) as archive:
            return "[Content_Types].xml" in archive.namelist()
    except (zipfile.BadZipFile, OSError):
        return False


def _file_digest(file_path: Path) -> str:
    """
    计算源文件 SHA-256 摘要。

    :param file_path: 文件路径
    :return: 十六进制摘要
    """
    digest = hashlib.sha256()
    with file_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _cache_dir_for_source(source_id: int | None) -> Path:
    """
    返回媒体源对应的 PPT 播放缓存目录。

    :param source_id: MediaSource 主键
    :return: 缓存目录路径
    """
    return Path(settings.MEDIA_ROOT) / _CACHE_ROOT / str(int(source_id or 0))


def _cache_path_from_metadata(cache_info: dict[str, object]) -> Path | None:
    """
    从 metadata 解析缓存文件路径。

    :param cache_info: ppt_playback metadata 字典
    :return: 本地路径或 None
    """
    raw_path = str(cache_info.get("path") or "")
    if raw_path:
        path = Path(raw_path)
        return path if path.is_absolute() else Path(settings.MEDIA_ROOT) / path
    relative_path = str(cache_info.get("relative_path") or "")
    if relative_path:
        return Path(settings.MEDIA_ROOT) / relative_path
    return None


def _remove_other_cache_files(cache_dir: Path, keep_path: Path) -> None:
    """
    清理同一媒体源目录下旧缓存文件。

    :param cache_dir: 缓存目录
    :param keep_path: 当前有效缓存文件
    :return: None
    """
    for child in cache_dir.iterdir():
        if child == keep_path:
            continue
        if child.is_file():
            child.unlink(missing_ok=True)
        elif child.is_dir():
            shutil.rmtree(child, ignore_errors=True)


def _failed_payload(source: MediaSource, preferred_backend: str | None, error_message: str) -> dict[str, object]:
    """
    构造失败状态 metadata。

    :param source: PPT 媒体源
    :param preferred_backend: 首选后端
    :param error_message: 错误说明
    :return: failed 状态 payload
    """
    source_path = Path(source.uri)
    source_digest = ""
    if source_path.is_file():
        try:
            source_digest = _file_digest(source_path)
        except OSError:
            source_digest = ""
    return {
        "status": "failed",
        "source_digest": source_digest,
        "backend": "powerpoint",
        "format": _target_extension_for_source(source_path).lstrip("."),
        "path": "",
        "relative_path": "",
        "generated_at": timezone.now().isoformat(),
        "error": error_message,
        "original_extension": source_path.suffix.lower(),
    }


__all__ = [
    "PPT_PLAYBACK_METADATA_KEY",
    "PptPlaybackCacheError",
    "cleanup_ppt_playback_cache",
    "prepare_ppt_playback_cache",
    "resolve_ppt_playback_uri",
]
