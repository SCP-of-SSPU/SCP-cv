from __future__ import annotations

from django.db import models


class ResourceKind(models.TextChoices):
	"""阶段一支持的资源类型。"""

	PPT = "ppt", "PPT"
	PPTX = "pptx", "PPTX"
	DERIVED = "derived", "派生资源"
	STREAM_CONFIG = "stream_config", "流配置"


class ParseState(models.TextChoices):
	"""资源解析状态。"""

	PENDING = "pending", "待解析"
	PROCESSING = "processing", "解析中"
	READY = "ready", "已就绪"
	FAILED = "failed", "失败"


class ResourceState(models.TextChoices):
	"""资源当前状态。"""

	IDLE = "idle", "空闲"
	OPENED = "opened", "已打开"
	PLAYING = "playing", "播放中"
	STOPPED = "stopped", "已停止"
	ARCHIVED = "archived", "已归档"


class MediaKind(models.TextChoices):
	"""PPT 当前页中的媒体类型。"""

	VIDEO = "video", "视频"
	AUDIO = "audio", "音频"


class MediaPlaybackState(models.TextChoices):
	"""单个媒体的播放状态。"""

	STOPPED = "stopped", "停止"
	PLAYING = "playing", "播放中"
	PAUSED = "paused", "暂停"


class ResourceFile(models.Model):
	"""统一记录 PPT / 派生资源 / 流配置等本地资源。"""

	display_name = models.CharField(max_length=255, db_index=True)
	file_kind = models.CharField(max_length=32, choices=ResourceKind.choices, db_index=True)
	original_path = models.CharField(max_length=512)
	storage_path = models.CharField(max_length=512, blank=True)
	file_size_bytes = models.BigIntegerField(default=0)
	page_count = models.PositiveIntegerField(default=0)
	uploaded_at = models.DateTimeField(auto_now_add=True)
	last_used_at = models.DateTimeField(null=True, blank=True)
	parse_state = models.CharField(max_length=32, choices=ParseState.choices, default=ParseState.PENDING, db_index=True)
	resource_state = models.CharField(max_length=32, choices=ResourceState.choices, default=ResourceState.IDLE)
	source_checksum = models.CharField(max_length=128, blank=True)

	class Meta:
		ordering = ["-last_used_at", "-uploaded_at"]

	def __str__(self) -> str:
		return self.display_name


class PresentationDocument(models.Model):
	"""PPT 文档的解析结果与派生资源索引。"""

	resource = models.OneToOneField(
		ResourceFile,
		on_delete=models.CASCADE,
		related_name="presentation_document",
	)
	total_pages = models.PositiveIntegerField(default=0)
	current_page = models.PositiveIntegerField(default=1)
	derived_resource_path = models.CharField(max_length=512, blank=True)
	last_opened_at = models.DateTimeField(null=True, blank=True)

	class Meta:
		ordering = ["-id"]

	def __str__(self) -> str:
		return f"{self.resource.display_name} ({self.total_pages} 页)"


class PresentationPageMedia(models.Model):
	"""单页内识别出的媒体对象。"""

	document = models.ForeignKey(
		PresentationDocument,
		on_delete=models.CASCADE,
		related_name="media_items",
	)
	page_number = models.PositiveIntegerField()
	media_name = models.CharField(max_length=255)
	media_kind = models.CharField(max_length=16, choices=MediaKind.choices)
	media_path = models.CharField(max_length=512)
	playback_state = models.CharField(
		max_length=16,
		choices=MediaPlaybackState.choices,
		default=MediaPlaybackState.STOPPED,
	)
	sort_order = models.PositiveIntegerField(default=0)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ["page_number", "sort_order", "media_name"]
		constraints = [
			models.UniqueConstraint(
				fields=["document", "page_number", "media_name"],
				name="unique_page_media_name",
			)
		]

	def __str__(self) -> str:
		return f"{self.media_name} @ 第 {self.page_number} 页"

