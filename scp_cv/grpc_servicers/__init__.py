#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
gRPC servicer 包入口，重新导出 PlaybackControlServicer 以保持向后兼容。
@Project : SCP-cv
@File : __init__.py
@Author : Qintsg
@Date : 2026-04-29
'''
from __future__ import annotations

from .servicer import PlaybackControlServicer

__all__ = ("PlaybackControlServicer",)
