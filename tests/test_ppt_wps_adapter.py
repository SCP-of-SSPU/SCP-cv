#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
WPS 演示 PPT 适配器测试，覆盖 WPS 专属窗口查找候选配置。
@Project : SCP-cv
@File : test_ppt_wps_adapter.py
@Author : Qintsg
@Date : 2026-05-27
'''
from __future__ import annotations

from scp_cv.player.adapters.ppt_window import SLIDESHOW_CLASS_NAMES
from scp_cv.player.adapters.ppt_wps import (
    WPS_SLIDESHOW_CLASS_NAMES,
    WpsPptSourceAdapter,
)


def test_wps_adapter_uses_wps_slideshow_window_classes() -> None:
    """WPS 回退枚举应同时识别 PowerPoint 兼容 class 和 WPS 专属 class。"""
    adapter = WpsPptSourceAdapter()

    assert SLIDESHOW_CLASS_NAMES.issubset(WPS_SLIDESHOW_CLASS_NAMES)
    assert "KWppShowWindow" in WPS_SLIDESHOW_CLASS_NAMES
    assert adapter._slideshow_class_names == WPS_SLIDESHOW_CLASS_NAMES
