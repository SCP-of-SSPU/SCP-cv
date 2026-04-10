from __future__ import annotations

import grpc

from scp_cv.grpc_generated.scp_cv.v1.control_pb2_grpc import (
    add_PlaybackControlServiceServicer_to_server,
)
from scp_cv.grpc_servicers import PlaybackControlServicer


def grpc_handlers(server: grpc.Server) -> None:
    """
    gRPC 服务注册入口，将所有 Servicer 绑定到 gRPC Server 实例。
    :param server: gRPC Server 实例
    """
    add_PlaybackControlServiceServicer_to_server(
        PlaybackControlServicer(), server,
    )
