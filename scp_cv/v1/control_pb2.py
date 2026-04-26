#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
gRPC protobuf 消息兼容转发模块。
复用实际生成在 scp_cv.grpc_generated.scp_cv.v1 下的 control_pb2。
@Project : SCP-cv
@File : control_pb2.py
@Author : Qintsg
@Date : 2026-04-26
'''
from __future__ import annotations

# 生成的 control_pb2_grpc.py 使用 scp_cv.v1.control_pb2 作为导入路径。
from scp_cv.grpc_generated.scp_cv.v1.control_pb2 import *  # noqa: F403
