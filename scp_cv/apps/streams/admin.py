from __future__ import annotations

from django.contrib import admin

from .models import StreamSource


@admin.register(StreamSource)
class StreamSourceAdmin(admin.ModelAdmin):
	list_display = (
		"name",
		"stream_identifier",
		"current_state",
		"is_online",
		"is_active",
		"last_connected_at",
		"last_seen_at",
	)
	list_filter = ("current_state", "is_online", "is_active")
	search_fields = ("name", "stream_identifier", "stream_url")

