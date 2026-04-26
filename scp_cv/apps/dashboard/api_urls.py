#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
控制台 REST API 路由。
统一挂载在 /api/ 前缀下，供 Vue 前端调用。
@Project : SCP-cv
@File : api_urls.py
@Author : Qintsg
@Date : 2026-04-26
'''
from django.urls import path

from . import api_views

app_name = "dashboard_api"

urlpatterns = [
    path("sources/", api_views.list_sources_api, name="list_sources"),
    path("sources/upload/", api_views.upload_source_api, name="upload_source"),
    path("sources/local/", api_views.add_local_source_api, name="add_local_source"),
    path("sources/web/", api_views.add_web_source_api, name="add_web_source"),
    path("sources/<int:source_id>/", api_views.delete_source_api, name="delete_source"),
    path("sessions/", api_views.list_sessions_api, name="list_sessions"),
    path("sessions/<int:window_id>/", api_views.session_detail_api, name="session_detail"),
    path("playback/<int:window_id>/open/", api_views.open_source_api, name="open_source"),
    path("playback/<int:window_id>/control/", api_views.playback_control_api, name="playback_control"),
    path("playback/<int:window_id>/navigate/", api_views.navigate_content_api, name="navigate_content"),
    path("playback/<int:window_id>/close/", api_views.close_source_api, name="close_source"),
    path("playback/<int:window_id>/loop/", api_views.toggle_loop_api, name="toggle_loop"),
    path("playback/splice/", api_views.set_splice_mode_api, name="set_splice_mode"),
    path("playback/show-ids/", api_views.show_window_ids_api, name="show_window_ids"),
    path("displays/", api_views.list_displays_api, name="list_displays"),
    path("displays/select/", api_views.select_display_api, name="select_display"),
    path("scenarios/", api_views.list_scenarios_api, name="list_scenarios"),
    path("scenarios/create/", api_views.create_scenario_api, name="create_scenario_compat"),
    path("scenarios/capture/", api_views.capture_scenario_api, name="capture_scenario"),
    path("scenarios/<int:scenario_id>/", api_views.scenario_detail_api, name="scenario_detail"),
    path("scenarios/<int:scenario_id>/activate/", api_views.activate_scenario_api, name="activate_scenario"),
    path("events/", api_views.events_api, name="events"),
]
