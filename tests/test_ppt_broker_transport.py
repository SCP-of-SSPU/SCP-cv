#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PowerPoint Broker AF_PIPE 传输测试。
@Project : SCP-cv
@File : test_ppt_broker_transport.py
@Author : Qintsg
@Date : 2026-07-11
'''
from __future__ import annotations

import threading
import time
import uuid
from multiprocessing.connection import Client
from pathlib import Path

from scp_cv.player.ppt_broker import (
    InMemoryPptBroker,
    PptBrokerEngine,
    PptBrokerClient,
    PptBrokerServer,
    PptCommand,
    PptCommandRequest,
    PptOpenRequest,
    PptPreheatRequest,
    PptSessionKey,
    PptShowExportRequest,
    PptShowFormat,
    PptSlideExportRequest,
    PptState,
    wait_for_broker,
)


class _BlockingOpenBackend:
    """用事件控制 OPEN 完成时机的测试后端。"""

    def __init__(self) -> None:
        self.open_started = threading.Event()
        self.release_open = threading.Event()
        self.shutdown_calls = 0

    def open(self, request: PptOpenRequest) -> object:
        self.open_started.set()
        if not self.release_open.wait(5.0):
            raise TimeoutError("test open was not released")
        return request

    def command(self, handle: object, request: PptCommandRequest) -> None:
        del handle, request

    def get_state(self, handle: object) -> PptState:
        if not isinstance(handle, PptOpenRequest):
            raise TypeError("invalid test handle")
        return PptState(
            playback_state="playing",
            current_slide=handle.start_slide,
            total_slides=10,
            parent_hwnd=handle.parent_hwnd,
        )

    def hide(self, handle: object) -> None:
        del handle

    def show(self, handle: object) -> None:
        del handle

    def close(self, handle: object) -> None:
        del handle

    def preheat(self, request: PptPreheatRequest) -> None:
        del request

    def shutdown(self) -> None:
        self.shutdown_calls += 1


def test_af_pipe_client_exercises_broker_with_json_messages(tmp_path: Path) -> None:
    """AF_PIPE 客户端应经 JSON bytes 完成健康检查、打开、控制和关闭。"""
    address = rf"\\.\pipe\scp-cv-ppt-broker-test-{uuid.uuid4().hex}"
    authkey = b"test-ppt-broker-authkey"
    server = PptBrokerServer(InMemoryPptBroker(), address, authkey)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    health = wait_for_broker(address, authkey, timeout_seconds=5.0)
    client = PptBrokerClient(address, authkey, timeout_seconds=5.0)
    session = PptSessionKey(3, "pipe-player")
    try:
        opened = client.open(
            PptOpenRequest(session, "C:/slides/pipe.pptx", 3003, start_slide=5)
        )
        advanced = client.command(PptCommandRequest(session, PptCommand.NEXT))

        assert health.ready is True
        assert opened.current_slide == 5
        assert advanced.current_slide == 6
        assert client.get_state(session).parent_hwnd == 3003
        show_result = client.export_show(
            PptShowExportRequest(
                "C:/slides/pipe.pptx",
                str(tmp_path / "pipe.ppsx"),
                PptShowFormat.PPSX,
            )
        )
        slide_result = client.export_slides(
            PptSlideExportRequest(
                "C:/slides/pipe.pptx",
                str(tmp_path),
            )
        )
        assert show_result.paths == (str(tmp_path / "pipe.ppsx"),)
        assert slide_result.paths[0] == str(tmp_path / "slide-1.png")
        client.close(session)
    finally:
        client.shutdown()
        server_thread.join(5.0)
    assert not server_thread.is_alive()


def test_long_open_does_not_block_health_from_another_pipe_client() -> None:
    """长 OPEN 占用 STA 时，服务端仍应并发接收并回答轻量 health。"""
    address = rf"\\.\pipe\scp-cv-ppt-broker-concurrency-{uuid.uuid4().hex}"
    authkey = b"test-ppt-broker-concurrency"
    backend = _BlockingOpenBackend()
    server = PptBrokerServer(PptBrokerEngine(backend), address, authkey)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    wait_for_broker(address, authkey, timeout_seconds=5.0)
    open_client = PptBrokerClient(address, authkey, timeout_seconds=5.0)
    health_client = PptBrokerClient(address, authkey, timeout_seconds=0.4)
    session = PptSessionKey(1, "blocking-open-player")
    open_errors: list[BaseException] = []

    def open_slideshow() -> None:
        try:
            open_client.open(PptOpenRequest(session, "C:/slides/slow.pptx", 1001))
        except BaseException as open_error:
            open_errors.append(open_error)

    open_thread = threading.Thread(target=open_slideshow)
    open_thread.start()
    assert backend.open_started.wait(2.0)
    try:
        started_at = time.monotonic()
        health = health_client.health()
        elapsed = time.monotonic() - started_at

        assert health.ready is True
        assert elapsed < 0.4
    finally:
        backend.release_open.set()
        open_thread.join(5.0)
        shutdown_client = PptBrokerClient(address, authkey, timeout_seconds=5.0)
        shutdown_client.shutdown()
        server_thread.join(5.0)

    assert open_errors == []
    assert not server_thread.is_alive()
    assert backend.shutdown_calls == 1


def test_shutdown_has_bounded_wait_for_idle_pipe_connection() -> None:
    """空闲客户端不发送请求体时，Broker shutdown 也必须在有界时间内退出。"""
    address = rf"\\.\pipe\scp-cv-ppt-broker-idle-{uuid.uuid4().hex}"
    authkey = b"test-ppt-broker-idle-client"
    server = PptBrokerServer(InMemoryPptBroker(), address, authkey)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    wait_for_broker(address, authkey, timeout_seconds=5.0)
    idle_connection = Client(address, family="AF_PIPE", authkey=authkey)
    shutdown_client = PptBrokerClient(address, authkey, timeout_seconds=5.0)
    try:
        time.sleep(0.05)
        shutdown_client.shutdown()
        server_thread.join(1.5)

        assert not server_thread.is_alive()
    finally:
        idle_connection.close()
        server_thread.join(5.0)
