#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
播放控制台旧视图的兼容导出。

新路由 urls.py 直接指向各职责 module；本文件仅保留旧导入路径。
@Project : SCP-cv
@File : views.py
@Author : Qintsg
@Date : 2026-04-14
'''
from __future__ import annotations

from scp_cv.apps.dashboard.legacy_media_views import (
    add_local_source,
    add_web_source,
    api_sources,
    home,
    remove_source,
    upload_source,
)
from scp_cv.apps.dashboard.legacy_playback_views import (
    api_session_state,
    close_current,
    navigate,
    open_media_source,
    playback_control,
    show_window_ids,
    sse_events,
    toggle_loop,
)
from scp_cv.apps.dashboard.legacy_scenario_views import (
    activate_scenario_view,
    api_scenarios,
    create_scenario_view,
    delete_scenario_view,
    update_scenario_view,
)

__all__ = [
    "activate_scenario_view",
    "add_local_source",
    "add_web_source",
    "api_scenarios",
    "api_session_state",
    "api_sources",
    "close_current",
    "create_scenario_view",
    "delete_scenario_view",
    "home",
    "navigate",
    "open_media_source",
    "playback_control",
    "remove_source",
    "show_window_ids",
    "sse_events",
    "toggle_loop",
    "update_scenario_view",
    "upload_source",
]
