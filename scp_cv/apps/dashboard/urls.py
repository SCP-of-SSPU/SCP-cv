from __future__ import annotations

from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    # 主页面
    path("", views.home, name="home"),

    # 操作端点
    path("stop/", views.stop_playback, name="stop_playback"),
    path("switch-display/", views.switch_display, name="switch_display"),
    path("open-stream/", views.open_stream, name="open_stream"),

    # JSON API
    path("api/session/", views.api_session_state, name="api_session_state"),
    path("api/streams/", views.api_streams, name="api_streams"),

    # SSE 事件流
    path("events/", views.sse_events, name="sse_events"),
]
