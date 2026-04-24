from __future__ import annotations

from django.db import models


class StreamState(models.TextChoices):
	"""外部推流（SRT/RTSP）连接状态。"""

	OFFLINE = "offline", "离线"
	CONNECTING = "connecting", "连接中"
	ONLINE = "online", "在线"
	DISCONNECTED = "disconnected", "已断开"
	ERROR = "error", "异常"


class StreamSource(models.Model):
	"""外部推流（SRT/RTSP）接入记录，由 MediaMTX 自动发现后同步创建。"""

	name = models.CharField(max_length=255, db_index=True)
	stream_identifier = models.CharField(max_length=255, unique=True)
	stream_url = models.CharField(max_length=512, blank=True)
	is_active = models.BooleanField(default=False)
	is_online = models.BooleanField(default=False)
	current_state = models.CharField(max_length=16, choices=StreamState.choices, default=StreamState.OFFLINE)
	last_connected_at = models.DateTimeField(null=True, blank=True)
	last_seen_at = models.DateTimeField(null=True, blank=True)
	last_error_message = models.TextField(blank=True)

	class Meta:
		ordering = ["name"]

	def __str__(self) -> str:
		return self.name

