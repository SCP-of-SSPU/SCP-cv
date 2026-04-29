#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
媒体源模型：文件夹（MediaFolder）、统一源（MediaSource）、PPT 解析资源（PptResource）。
@Project : SCP-cv
@File : models/media.py
@Author : Qintsg
@Date : 2026-04-29
'''
from __future__ import annotations

from django.db import models

from .enums import SourceType


class MediaFolder(models.Model):
    """
    媒体源文件夹，支持层级组织。
    """

    name = models.CharField(
        max_length=255,
        verbose_name="文件夹名称",
    )
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="children",
        verbose_name="父文件夹",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="创建时间",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="更新时间",
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "媒体文件夹"
        verbose_name_plural = "媒体文件夹"

    def __str__(self) -> str:
        return self.name


class MediaSource(models.Model):
    """
    统一媒体源模型，所有可播放内容的注册表。
    文件型源（PPT/视频/图片等）通过上传或本地路径录入；
    RTSP 流型源由 MediaMTX 自动发现后同步创建。
    """

    source_type = models.CharField(
        max_length=24,
        choices=SourceType.choices,
        db_index=True,
        verbose_name="源类型",
    )
    name = models.CharField(
        max_length=255,
        verbose_name="显示名称",
    )
    uri = models.CharField(
        max_length=1024,
        verbose_name="资源地址",
        help_text="文件绝对路径、URL 或流标识符",
    )
    uploaded_file = models.FileField(
        upload_to="uploads/%Y%m%d/",
        blank=True,
        verbose_name="上传文件",
        help_text="通过 Web 上传的文件存储路径",
    )
    # 仅 RTSP_STREAM 类型使用，关联自动发现的流记录
    stream_identifier = models.CharField(
        max_length=255,
        blank=True,
        db_index=True,
        verbose_name="流标识符",
        help_text="RTSP 流的 MediaMTX 路径标识",
    )
    is_available = models.BooleanField(
        default=True,
        verbose_name="是否可用",
        help_text="文件是否存在 / 流是否在线",
    )

    # ── 文件夹与文件元数据 ──
    folder = models.ForeignKey(
        MediaFolder,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="sources",
        verbose_name="所属文件夹",
    )
    original_filename = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="原始文件名",
        help_text="上传时的原始文件名，用于下载",
    )
    file_size = models.BigIntegerField(
        default=0,
        verbose_name="文件大小（字节）",
    )
    mime_type = models.CharField(
        max_length=127,
        blank=True,
        verbose_name="MIME 类型",
    )

    # ── 临时源 ──
    is_temporary = models.BooleanField(
        default=False,
        verbose_name="是否临时源",
        help_text="临时源在切换离开后自动删除",
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="过期时间",
        help_text="临时源过期后自动清理",
    )

    # ── 扩展元数据 ──
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="扩展元数据",
        help_text="存储 PPT 解析资源 ID 等扩展信息",
    )

    # ── 时间戳 ──
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="创建时间",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "媒体源"
        verbose_name_plural = "媒体源"

    def __str__(self) -> str:
        return f"[{self.get_source_type_display()}] {self.name}"


class PptResource(models.Model):
    """
    PPT 解析资源，存储幻灯片 PNG 预览和提词器文本。
    与 MediaSource 关联，删除 PPT 时一并删除。
    """

    source = models.ForeignKey(
        MediaSource,
        on_delete=models.CASCADE,
        related_name="ppt_resources",
        verbose_name="关联 PPT 源",
    )
    page_index = models.PositiveIntegerField(
        verbose_name="页码（从 1 开始）",
    )
    slide_image = models.CharField(
        max_length=512,
        blank=True,
        verbose_name="幻灯片 PNG 路径",
    )
    next_slide_image = models.CharField(
        max_length=512,
        blank=True,
        verbose_name="下一页 PNG 路径",
    )
    speaker_notes = models.TextField(
        blank=True,
        default="",
        verbose_name="演讲者备注/提词器文本",
    )
    has_media = models.BooleanField(
        default=False,
        verbose_name="是否包含媒体",
        help_text="该页是否包含视频/音频媒体对象",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="创建时间",
    )

    class Meta:
        ordering = ["source", "page_index"]
        unique_together = [("source", "page_index")]
        verbose_name = "PPT 资源"
        verbose_name_plural = "PPT 资源"

    def __str__(self) -> str:
        return f"{self.source.name} - 第{self.page_index}页"
