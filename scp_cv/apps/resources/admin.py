from __future__ import annotations

from django.contrib import admin

from .models import PresentationDocument, PresentationPageMedia, ResourceFile


@admin.register(ResourceFile)
class ResourceFileAdmin(admin.ModelAdmin):
	list_display = (
		"display_name",
		"file_kind",
		"page_count",
		"parse_state",
		"resource_state",
		"uploaded_at",
		"last_used_at",
	)
	list_filter = ("file_kind", "parse_state", "resource_state")
	search_fields = ("display_name", "original_path", "storage_path")


@admin.register(PresentationDocument)
class PresentationDocumentAdmin(admin.ModelAdmin):
	list_display = ("resource", "total_pages", "current_page", "last_opened_at")
	search_fields = ("resource__display_name",)


@admin.register(PresentationPageMedia)
class PresentationPageMediaAdmin(admin.ModelAdmin):
	list_display = (
		"media_name",
		"document",
		"page_number",
		"media_kind",
		"playback_state",
		"sort_order",
	)
	list_filter = ("media_kind", "playback_state", "page_number")
	search_fields = ("media_name", "media_path")

