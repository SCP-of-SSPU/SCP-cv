#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
gRPC 播放控制服务测试。
覆盖控制 RPC 的状态事件发布，以及状态流对 DB 快照变化的推送能力。
@Project : SCP-cv
@File : test_grpc_servicers.py
@Author : Qintsg
@Date : 2026-04-26
'''
from __future__ import annotations

from collections.abc import Generator
from concurrent import futures
from unittest.mock import patch

import grpc
import pytest

from scp_cv.apps.playback.models import MediaSource, PlaybackState
from scp_cv.grpc_generated.scp_cv.v1 import control_pb2
from scp_cv.grpc_generated.scp_cv.v1 import control_pb2_grpc
from scp_cv.grpc_servicers import PlaybackControlServicer
from scp_cv.services.playback import get_or_create_session


class _ActiveContext:
    """提供 gRPC 流测试所需的最小 is_active() 上下文。"""

    def is_active(self) -> bool:
        """
        返回客户端连接状态。
        :return: 测试期间持续保持连接
        """
        return True


@pytest.mark.django_db
def test_open_source_publishes_playback_state_event(
    media_source_ppt: MediaSource,
) -> None:
    """OpenSource 成功写入命令后应发布 playback_state 事件。"""
    servicer = PlaybackControlServicer()
    request = control_pb2.OpenSourceRequest(
        window_id=1,
        media_source_id=media_source_ppt.pk,
        autoplay=True,
    )

    with patch("scp_cv.services.sse.publish_event") as publish_event_mock:
        response = servicer.OpenSource(request, None)

    assert response.success is True
    publish_event_mock.assert_called_once()
    event_type, event_payload = publish_event_mock.call_args.args
    assert event_type == "playback_state"
    assert event_payload["sessions"]


@pytest.mark.django_db
def test_watch_playback_state_pushes_changed_db_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """状态流应在没有进程内事件时也推送 DB 快照变化。"""
    monkeypatch.setattr("scp_cv.grpc_servicers.streaming._STATE_WATCH_POLL_SECONDS", 0.01)
    servicer = PlaybackControlServicer()
    stream_generator: Generator = servicer.WatchPlaybackState(
        control_pb2.EmptyRequest(),
        _ActiveContext(),
    )

    initial_event = next(stream_generator)
    assert initial_event.event_type == "initial_state"

    session = get_or_create_session(1)
    session.playback_state = PlaybackState.PLAYING
    session.save(update_fields=["playback_state", "last_updated_at"])

    changed_event = next(stream_generator)
    try:
        assert changed_event.event_type == "playback_state"
        assert any(
            snapshot.window_id == 1
            and snapshot.playback_state == PlaybackState.PLAYING
            for snapshot in changed_event.sessions
        )
    finally:
        stream_generator.close()


@pytest.mark.django_db(transaction=True)
def test_grpc_real_channel_open_and_read_state(
    media_source_video: MediaSource,
) -> None:
    """保留 gRPC 接口应能通过真实 channel 调用。"""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=2))
    control_pb2_grpc.add_PlaybackControlServiceServicer_to_server(
        PlaybackControlServicer(), server,
    )
    port = server.add_insecure_port("127.0.0.1:0")
    server.start()

    try:
        with grpc.insecure_channel(f"127.0.0.1:{port}") as channel:
            stub = control_pb2_grpc.PlaybackControlServiceStub(channel)
            open_reply = stub.OpenSource(control_pb2.OpenSourceRequest(
                window_id=1,
                media_source_id=media_source_video.pk,
                autoplay=True,
            ))
            state_reply = stub.GetPlaybackState(control_pb2.WindowRequest(window_id=1))

        assert open_reply.success is True
        assert state_reply.source_name == media_source_video.name
        assert state_reply.playback_state == "loading"
    finally:
        server.stop(grace=0)


@pytest.mark.django_db
def test_grpc_display_rpc_uses_display_targets() -> None:
    """ListDisplayTargets 应返回显示器列表和拼接标签。"""
    servicer = PlaybackControlServicer()
    display = type("Display", (), {
        "index": 1,
        "name": "Display 1",
        "width": 1920,
        "height": 1080,
        "x": 0,
        "y": 0,
        "is_primary": True,
    })()

    with patch("scp_cv.grpc_servicers.display.list_display_targets", return_value=[display]):
        response = servicer.ListDisplayTargets(control_pb2.EmptyRequest(), None)

    assert response.targets[0].name == "Display 1"
