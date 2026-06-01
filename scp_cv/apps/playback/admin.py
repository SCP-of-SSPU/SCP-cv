from __future__ import annotations

from django.contrib import admin

from .models import BackgroundAudioPlaylistItem, BackgroundAudioState, MediaSource, PlaybackSession


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


@admin.register(BackgroundAudioState)
class BackgroundAudioStateAdmin(admin.ModelAdmin):
    list_display = (
        "current_source",
        "playback_state",
        "volume",
        "is_muted",
        "loop_enabled",
        "pending_command",
        "updated_at",
    )
    list_filter = ("playback_state", "is_muted", "loop_enabled")


@admin.register(BackgroundAudioPlaylistItem)
class BackgroundAudioPlaylistItemAdmin(admin.ModelAdmin):
    list_display = ("source", "sort_order", "created_at")
    list_filter = ("source__source_type",)
    search_fields = ("source__name", "source__uri")
