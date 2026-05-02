#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PowerPoint COM 常量，集中标注 magic number 的 Office 枚举含义。
@Project : SCP-cv
@File : ppt_constants.py
@Author : Qintsg
@Date : 2026-05-02
'''
from __future__ import annotations

# PowerPoint 放映推进类型常量
PP_ADVANCE_MODE_ON_CLICK = 1  # ppAdvanceOnClick
PP_SLIDE_SHOW_WINDOW = 1      # ppShowTypeWindow
PP_SLIDE_SHOW_SPEAKER = 1     # ppShowTypeSpeaker
PP_SLIDE_SHOW_KIOSK = 3       # ppShowTypeKiosk

# 放映状态常量
PP_SLIDE_SHOW_RUNNING = 1     # ppSlideShowRunning
PP_SLIDE_SHOW_PAUSED = 2      # ppSlideShowPaused
PP_SLIDE_SHOW_DONE = 5        # ppSlideShowDone
PP_ALERTS_NONE = 1            # ppAlertsNone
PP_ALERTS_ALL = 2             # ppAlertsAll
