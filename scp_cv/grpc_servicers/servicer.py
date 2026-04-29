#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PlaybackControlServicer 主类，组合所有功能 mixin 与 proto 基类。
@Project : SCP-cv
@File : servicer.py
@Author : Qintsg
@Date : 2026-04-29
'''
from scp_cv.grpc_generated.scp_cv.v1 import control_pb2_grpc

from .display import DisplayMixin
from .media import MediaSourceServicerMixin
from .playback import PlaybackControlMixin
from .scenario import ScenarioMixin
from .streaming import StreamingMixin


class PlaybackControlServicer(
    MediaSourceServicerMixin,
    PlaybackControlMixin,
    DisplayMixin,
    ScenarioMixin,
    StreamingMixin,
    control_pb2_grpc.PlaybackControlServiceServicer,
):
    """PlaybackControlService 的具体实现，委托 Django 服务层处理业务逻辑。"""
