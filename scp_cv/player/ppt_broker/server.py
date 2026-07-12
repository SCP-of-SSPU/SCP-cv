#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PowerPoint Broker 独立进程入口。
@Project : SCP-cv
@File : server.py
@Author : Qintsg
@Date : 2026-07-11
'''
from __future__ import annotations

import argparse
import logging
from collections.abc import Sequence

from scp_cv.player.ppt_broker.engine import PptBackend, PptBrokerEngine
from scp_cv.player.ppt_broker.powerpoint import PowerPointComBackend
from scp_cv.player.ppt_broker.runtime import (
    BrokerInstanceLock,
    clear_runtime_metadata,
    default_pipe_address,
    load_or_create_authkey,
    write_runtime_metadata,
)
from scp_cv.player.ppt_broker.transport import PptBrokerServer

logger = logging.getLogger(__name__)


def serve_broker(
    address: str | None = None,
    authkey: bytes | None = None,
    backend: PptBackend | None = None,
) -> None:
    """运行唯一的本地 PowerPoint Broker，直至收到 shutdown。"""
    selected_address = address or default_pipe_address()
    selected_authkey = authkey or load_or_create_authkey()
    with BrokerInstanceLock(selected_address):
        broker = PptBrokerEngine(backend or PowerPointComBackend())
        generation = broker.health().generation
        write_runtime_metadata(selected_address, broker.health())
        logger.info(
            "PowerPoint Broker 已启动：address=%s, generation=%s",
            selected_address,
            generation,
        )
        try:
            PptBrokerServer(broker, selected_address, selected_authkey).serve_forever()
        finally:
            clear_runtime_metadata(generation)
            logger.info("PowerPoint Broker 已停止：generation=%s", generation)


def main(argv: Sequence[str] | None = None) -> int:
    """解析独立进程参数并启动 Broker。"""
    parser = argparse.ArgumentParser(description="运行 SCP-cv PowerPoint Broker")
    parser.add_argument("--pipe-address", default=None, help="覆盖默认 AF_PIPE 地址")
    arguments = parser.parse_args(argv)
    serve_broker(address=arguments.pipe_address)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["main", "serve_broker"]
