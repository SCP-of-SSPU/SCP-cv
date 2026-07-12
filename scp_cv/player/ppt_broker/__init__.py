#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PowerPoint Broker 深模块公共入口。
@Project : SCP-cv
@File : __init__.py
@Author : Qintsg
@Date : 2026-07-11
'''
from scp_cv.player.ppt_broker.contracts import (
    BrokerHealth,
    PptBroker,
    PptCommand,
    PptCommandRequest,
    PptExportResult,
    PptOpenRequest,
    PptPreheatRequest,
    PptSessionKey,
    PptSessionNotFoundError,
    PptShowExportRequest,
    PptShowFormat,
    PptSlideExportRequest,
    PptState,
)
from scp_cv.player.ppt_broker.engine import PptBackend, PptBrokerEngine
from scp_cv.player.ppt_broker.memory import InMemoryPptBroker
from scp_cv.player.ppt_broker.powerpoint import PowerPointComBackend
from scp_cv.player.ppt_broker.runtime import (
    BrokerAlreadyRunningError,
    authkey_path,
    connect_or_start,
    default_pipe_address,
    load_or_create_authkey,
    metadata_path,
    runtime_directory,
    wait_for_broker,
)
from scp_cv.player.ppt_broker.server import serve_broker
from scp_cv.player.ppt_broker.transport import (
    PptBrokerClient,
    PptBrokerRemoteError,
    PptBrokerServer,
)

__all__ = [
    "BrokerHealth",
    "BrokerAlreadyRunningError",
    "InMemoryPptBroker",
    "PptBackend",
    "PptBroker",
    "PptBrokerClient",
    "PptBrokerEngine",
    "PptBrokerRemoteError",
    "PptBrokerServer",
    "PptCommand",
    "PptCommandRequest",
    "PptExportResult",
    "PptOpenRequest",
    "PptPreheatRequest",
    "PowerPointComBackend",
    "PptSessionKey",
    "PptSessionNotFoundError",
    "PptShowExportRequest",
    "PptShowFormat",
    "PptSlideExportRequest",
    "PptState",
    "authkey_path",
    "connect_or_start",
    "default_pipe_address",
    "load_or_create_authkey",
    "metadata_path",
    "runtime_directory",
    "serve_broker",
    "wait_for_broker",
]
