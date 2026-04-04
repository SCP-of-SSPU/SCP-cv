from __future__ import annotations

from django.db import models

from scp_cv.apps.resources.models import ResourceFile
from scp_cv.apps.streams.models import StreamSource


class PlaybackContentKind(models.TextChoices):
	"""当前播放内容类型。"""

	NONE = "none", "无"
	PPT = "ppt", "PPT"
	STREAM = "stream", "SRT 流"


class PlaybackMode(models.TextChoices):
	"""播放目标布局。"""

	SINGLE = "single", "单屏"
	LEFT_RIGHT_SPLICE = "left_right_splice", "左右拼接"


class PlaybackState(models.TextChoices):
	"""播放会话状态。"""

	IDLE = "idle", "待机"
	LOADING = "loading", "加载中"
	PLAYING = "playing", "播放中"
	PAUSED = "paused", "暂停"
	STOPPED = "stopped", "已停止"
	ERROR = "error", "异常"


class PlaybackSession(models.Model):
	"""统一播放会话，只维护一个当前内容源。"""

	content_kind = models.CharField(max_length=16, choices=PlaybackContentKind.choices, default=PlaybackContentKind.NONE)
	content_resource = models.ForeignKey(
		ResourceFile,
		null=True,
		blank=True,
		on_delete=models.SET_NULL,
		related_name="playback_sessions",
	)
	stream_source = models.ForeignKey(
		StreamSource,
		null=True,
		blank=True,
		on_delete=models.SET_NULL,
		related_name="playback_sessions",
	)
	current_page_number = models.PositiveIntegerField(default=1)
	total_pages = models.PositiveIntegerField(default=0)
	playback_state = models.CharField(max_length=16, choices=PlaybackState.choices, default=PlaybackState.IDLE)
	display_mode = models.CharField(max_length=24, choices=PlaybackMode.choices, default=PlaybackMode.SINGLE)
	target_display_label = models.CharField(max_length=255, blank=True)
	spliced_display_label = models.CharField(max_length=255, blank=True)
	is_spliced = models.BooleanField(default=False)
	last_updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ["-last_updated_at"]

	def __str__(self) -> str:
		return f"{self.get_content_kind_display()} / {self.get_playback_state_display()}"

