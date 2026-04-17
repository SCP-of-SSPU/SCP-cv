#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
播放控制台 URL 路由配置。
播放控制端点通过 <window_id> 路径参数指定目标窗口。
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

    # ── 源管理（全局） ──
    path("sources/upload/", views.upload_source, name="upload_source"),
    path("sources/add-local/", views.add_local_source, name="add_local_source"),
    path("sources/add-web/", views.add_web_source, name="add_web_source"),
    path("sources/remove/", views.remove_source, name="remove_source"),
    path("api/sources/", views.api_sources, name="api_sources"),

    # ── 播放控制（按窗口） ──
    path("playback/<str:window_id>/open/", views.open_media_source, name="open_source"),
    path("playback/<str:window_id>/control/", views.playback_control, name="playback_control"),
    path("playback/<str:window_id>/navigate/", views.navigate, name="navigate"),
    path("playback/<str:window_id>/close/", views.close_current, name="close_current"),
    path("playback/<str:window_id>/toggle-loop/", views.toggle_loop, name="toggle_loop"),

    # ── 拼接模式（窗口 1+2） ──
    path("playback/splice/", views.toggle_splice, name="toggle_splice"),

    # ── 窗口 ID 叠加显示 ──
    path("playback/show-ids/", views.show_window_ids, name="show_window_ids"),

    # ── 状态查询 & SSE ──
    path("api/session/", views.api_session_state, name="api_session_state"),
    path("events/", views.sse_events, name="sse_events"),

    # ── 预案管理 ──
    path("api/scenarios/", views.api_scenarios, name="api_scenarios"),
    path("scenarios/create/", views.create_scenario_view, name="create_scenario"),
    path("scenarios/<str:scenario_id>/update/", views.update_scenario_view, name="update_scenario"),
    path("scenarios/<str:scenario_id>/delete/", views.delete_scenario_view, name="delete_scenario"),
    path("scenarios/<str:scenario_id>/activate/", views.activate_scenario_view, name="activate_scenario"),
]
