from __future__ import annotations

from django.contrib import admin

from .models import (
    BackgroundAudioPlaylistItem,
    BackgroundAudioState,
    ControlCommand,
    MediaSource,
    PlaybackSession,
)


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
    readonly_fields = ("pending_command", "command_args")
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
    readonly_fields = ("pending_command", "command_args")
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


@admin.register(ControlCommand)
class ControlCommandAdmin(admin.ModelAdmin):
    """只读展示持久化控制指令的领取和完成状态。"""

    list_display = (
        "id",
        "target",
        "command",
        "status",
        "consumer_id",
        "cancel_requested",
        "created_at",
        "started_at",
        "finished_at",
    )
    list_filter = ("target", "status", "command", "cancel_requested")
    search_fields = ("consumer_id", "error_message", "=batch_id")

    def has_add_permission(self, request: object) -> bool:
        """队列只能由服务层创建，后台禁止手工插入。"""
        return False

    def has_change_permission(
        self,
        request: object,
        obj: object | None = None,
    ) -> bool:
        """完成状态是审计事实，后台只读。"""
        return False

    def has_delete_permission(
        self,
        request: object,
        obj: object | None = None,
    ) -> bool:
        """终态清理由保留策略执行，后台禁止手工删除。"""
        return False
