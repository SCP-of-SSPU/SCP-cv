from __future__ import annotations

from django.contrib import admin

from .models import PlaybackSession


@admin.register(PlaybackSession)
class PlaybackSessionAdmin(admin.ModelAdmin):
	list_display = (
		"content_kind",
		"playback_state",
		"display_mode",
		"current_page_number",
		"total_pages",
		"target_display_label",
		"last_updated_at",
	)
	list_filter = ("content_kind", "playback_state", "display_mode", "is_spliced")
	search_fields = ("target_display_label", "spliced_display_label")

