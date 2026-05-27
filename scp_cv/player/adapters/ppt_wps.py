#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
WPS 演示 PPT 源适配器，复用 COM 放映控制并注入 WPS 自动化入口。
@Project : SCP-cv
@File : ppt_wps.py
@Author : Qintsg
@Date : 2026-05-27
'''
from __future__ import annotations

from scp_cv.player.adapters.ppt import PptSourceAdapter
from scp_cv.player.adapters.ppt_window import SLIDESHOW_CLASS_NAMES
from scp_cv.ppt_com import WPS_COM_PROG_IDS

WPS_SLIDESHOW_CLASS_NAMES = SLIDESHOW_CLASS_NAMES | frozenset({"KWppShowWindow"})


class WpsPptSourceAdapter(PptSourceAdapter):
    """WPS 演示 COM 放映适配器。"""

    def __init__(self) -> None:
        """
        初始化 WPS 演示适配器。
        :return: None
        """
        super().__init__(
            adapter_name="ppt-wps",
            app_label="WPS 演示",
            com_prog_ids=WPS_COM_PROG_IDS,
            slideshow_class_names=WPS_SLIDESHOW_CLASS_NAMES,
        )


__all__ = [
    "WPS_SLIDESHOW_CLASS_NAMES",
    "WpsPptSourceAdapter",
]
