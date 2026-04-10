from __future__ import annotations

from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    # 主页面
    path("", views.home, name="home"),

    # 操作端点
    path("upload/", views.upload_file, name="upload_file"),
    path("delete/", views.delete_file, name="delete_file"),
    path("open-resource/", views.open_resource, name="open_resource"),
    path("ppt-navigate/", views.ppt_navigate, name="ppt_navigate"),
    path("stop/", views.stop_playback, name="stop_playback"),
    path("switch-display/", views.switch_display, name="switch_display"),
    path("open-stream/", views.open_stream, name="open_stream"),

    # JSON API
    path("api/session/", views.api_session_state, name="api_session_state"),
    path("api/resources/", views.api_resources, name="api_resources"),
    path("api/page-media/", views.api_page_media, name="api_page_media"),
    path("api/streams/", views.api_streams, name="api_streams"),

    # SSE 事件流
    path("events/", views.sse_events, name="sse_events"),
]
