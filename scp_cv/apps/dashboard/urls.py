#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
播放控制台 URL 路由配置。
@Project : SCP-cv
@File : urls.py
@Author : Qintsg
@Date : 2026-04-14
'''
from django.urls import path

from . import views

app_name = "dashboard"
urlpatterns = [
    # 页面
    path("", views.home, name="home"),

    # ── 源管理 ──
    path("sources/upload/", views.upload_source, name="upload_source"),
    path("sources/add-local/", views.add_local_source, name="add_local_source"),
    path("sources/add-web/", views.add_web_source, name="add_web_source"),
    path("sources/remove/", views.remove_source, name="remove_source"),
    path("api/sources/", views.api_sources, name="api_sources"),

    # ── 播放控制 ──
    path("playback/open/", views.open_media_source, name="open_source"),
    path("playback/control/", views.playback_control, name="playback_control"),
    path("playback/navigate/", views.navigate, name="navigate"),
    path("playback/close/", views.close_current, name="close_current"),
    path("playback/toggle-loop/", views.toggle_loop, name="toggle_loop"),

    # ── 显示配置 ──
    path("display/switch/", views.switch_display, name="switch_display"),

    # ── 状态查询 & SSE ──
    path("api/session/", views.api_session_state, name="api_session_state"),
    path("events/", views.sse_events, name="sse_events"),
]
