from __future__ import annotations

from django.contrib import admin

from .models import MediaSource, PlaybackSession


@admin.register(MediaSource)
class MediaSourceAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "source_type",
        "uri",
        "is_available",
        "created_at",
    )
    list_filter = ("source_type", "is_available")
    search_fields = ("name", "uri", "stream_identifier")


@admin.register(PlaybackSession)
class PlaybackSessionAdmin(admin.ModelAdmin):
    list_display = (
        "media_source",
        "playback_state",
        "display_mode",
        "target_display_label",
        "pending_command",
        "last_updated_at",
    )
    list_filter = ("playback_state", "display_mode", "is_spliced")
    search_fields = ("target_display_label", "spliced_display_label")
