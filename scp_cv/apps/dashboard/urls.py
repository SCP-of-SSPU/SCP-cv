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

from . import legacy_media_views, legacy_playback_views, legacy_scenario_views

app_name = "dashboard"
urlpatterns = [
    # 页面
    path("", legacy_media_views.home, name="home"),

    # ── 源管理（全局） ──
    path("sources/upload/", legacy_media_views.upload_source, name="upload_source"),
    path("sources/add-local/", legacy_media_views.add_local_source, name="add_local_source"),
    path("sources/add-web/", legacy_media_views.add_web_source, name="add_web_source"),
    path("sources/remove/", legacy_media_views.remove_source, name="remove_source"),
    path("api/sources/", legacy_media_views.api_sources, name="api_sources"),

    # ── 播放控制（按窗口） ──
    path("playback/<str:window_id>/open/", legacy_playback_views.open_media_source, name="open_source"),
    path("playback/<str:window_id>/control/", legacy_playback_views.playback_control, name="playback_control"),
    path("playback/<str:window_id>/navigate/", legacy_playback_views.navigate, name="navigate"),
    path("playback/<str:window_id>/close/", legacy_playback_views.close_current, name="close_current"),
    path("playback/<str:window_id>/toggle-loop/", legacy_playback_views.toggle_loop, name="toggle_loop"),

    # ── 窗口 ID 叠加显示 ──
    path("playback/show-ids/", legacy_playback_views.show_window_ids, name="show_window_ids"),

    # ── 状态查询 & SSE ──
    path("api/session/", legacy_playback_views.api_session_state, name="api_session_state"),
    path("events/", legacy_playback_views.sse_events, name="sse_events"),

    # ── 预案管理 ──
    path("api/scenarios/", legacy_scenario_views.api_scenarios, name="api_scenarios"),
    path("scenarios/create/", legacy_scenario_views.create_scenario_view, name="create_scenario"),
    path("scenarios/<str:scenario_id>/update/", legacy_scenario_views.update_scenario_view, name="update_scenario"),
    path("scenarios/<str:scenario_id>/delete/", legacy_scenario_views.delete_scenario_view, name="delete_scenario"),
    path("scenarios/<str:scenario_id>/activate/", legacy_scenario_views.activate_scenario_view, name="activate_scenario"),
]
