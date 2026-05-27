#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
本机 PPT COM 自动化入口常量。
@Project : SCP-cv
@File : ppt_com.py
@Author : Qintsg
@Date : 2026-05-27
'''
from __future__ import annotations

POWERPOINT_COM_PROG_IDS = ("PowerPoint.Application",)
WPS_COM_PROG_IDS = ("KWPP.Application", "WPP.Application")

__all__ = [
    "POWERPOINT_COM_PROG_IDS",
    "WPS_COM_PROG_IDS",
]
