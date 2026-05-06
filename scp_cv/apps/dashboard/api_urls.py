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

from . import api_playback_views, api_scenario_views, api_views

app_name = "dashboard_api"

urlpatterns = [
    path("folders/", api_views.folders_api, name="folders"),
    path("folders/<int:folder_id>/", api_views.folder_detail_api, name="folder_detail"),
    path("sources/", api_views.list_sources_api, name="list_sources"),
    path("sources/upload/", api_views.upload_source_api, name="upload_source"),
    path("sources/local/", api_views.add_local_source_api, name="add_local_source"),
    path("sources/web/", api_views.add_web_source_api, name="add_web_source"),
    path("sources/<int:source_id>/move/", api_views.move_source_api, name="move_source"),
    path("sources/<int:source_id>/download/", api_views.download_source_api, name="download_source"),
    path("sources/<int:source_id>/ppt-resources/", api_views.ppt_resources_api, name="ppt_resources"),
    path("sources/<int:source_id>/", api_views.delete_source_api, name="delete_source"),
    path("sessions/", api_playback_views.list_sessions_api, name="list_sessions"),
    path("sessions/<int:window_id>/", api_playback_views.session_detail_api, name="session_detail"),
    path("runtime/", api_playback_views.runtime_state_api, name="runtime_state"),
    path("volume/", api_playback_views.system_volume_api, name="system_volume"),
    path("playback/<int:window_id>/open/", api_playback_views.open_source_api, name="open_source"),
    path("playback/<int:window_id>/control/", api_playback_views.playback_control_api, name="playback_control"),
    path("playback/<int:window_id>/navigate/", api_playback_views.navigate_content_api, name="navigate_content"),
    path("playback/<int:window_id>/ppt-media/", api_playback_views.ppt_media_control_api, name="ppt_media_control"),
    path("playback/<int:window_id>/close/", api_playback_views.close_source_api, name="close_source"),
    path("playback/<int:window_id>/loop/", api_playback_views.toggle_loop_api, name="toggle_loop"),
    path("playback/<int:window_id>/volume/", api_playback_views.set_window_volume_api, name="set_window_volume"),
    path("playback/<int:window_id>/mute/", api_playback_views.set_window_mute_api, name="set_window_mute"),
    path("playback/show-ids/", api_playback_views.show_window_ids_api, name="show_window_ids"),
    path("playback/reset-all/", api_playback_views.reset_all_sessions_api, name="reset_all_sessions"),
    path("system/shutdown/", api_playback_views.shutdown_system_api, name="shutdown_system"),
    path("displays/", api_playback_views.list_displays_api, name="list_displays"),
    path("displays/select/", api_playback_views.select_display_api, name="select_display"),
    path("devices/", api_views.list_devices_api, name="list_devices"),
    path("devices/<str:device_type>/toggle/", api_views.toggle_device_api, name="toggle_device"),
    path("devices/<str:device_type>/power/<str:action>/", api_views.power_device_api, name="power_device"),
    path("scenarios/", api_scenario_views.list_scenarios_api, name="list_scenarios"),
    path("scenarios/create/", api_scenario_views.create_scenario_api, name="create_scenario_compat"),
    path("scenarios/capture/", api_scenario_views.capture_scenario_api, name="capture_scenario"),
    path("scenarios/<int:scenario_id>/", api_scenario_views.scenario_detail_api, name="scenario_detail"),
    path("scenarios/<int:scenario_id>/pin/", api_scenario_views.pin_scenario_api, name="pin_scenario"),
    path("scenarios/<int:scenario_id>/activate/", api_scenario_views.activate_scenario_api, name="activate_scenario"),
    path("events/", api_views.events_api, name="events"),
]
