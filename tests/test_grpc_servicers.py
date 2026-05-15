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
from pathlib import Path
from unittest.mock import patch

import grpc
import pytest

from scp_cv.apps.playback.models import MediaSource, PlaybackState, SourceType
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


@pytest.mark.django_db
def test_list_sources_returns_extended_payload(
    media_source_ppt: MediaSource,
) -> None:
    """ListSources 应返回与 REST 源 payload 对齐的扩展字段。"""
    media_source_ppt.metadata = {"total_slides": 3}
    media_source_ppt.original_filename = "demo.pptx"
    media_source_ppt.file_size = 4096
    media_source_ppt.mime_type = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    media_source_ppt.save(update_fields=[
        "metadata",
        "original_filename",
        "file_size",
        "mime_type",
    ])
    servicer = PlaybackControlServicer()

    response = servicer.ListSources(
        control_pb2.ListSourcesRequest(source_type=SourceType.PPT),
        None,
    )

    assert response.success is True
    assert len(response.sources) == 1
    source = response.sources[0]
    assert source.id == media_source_ppt.pk
    assert source.original_filename == "demo.pptx"
    assert source.file_size == 4096
    assert source.metadata.fields["total_slides"].number_value == 3
    assert source.preheat_enabled is True


@pytest.mark.django_db
def test_add_web_url_source_returns_preheat_and_preview_fields() -> None:
    """AddWebUrlSource 应返回完整 SourceItem，并尊重新预热字段。"""
    servicer = PlaybackControlServicer()

    response = servicer.AddWebUrlSource(
        control_pb2.AddWebUrlSourceRequest(
            url="panel.local",
            name="现场面板",
            preheat_enabled=False,
        ),
        None,
    )

    assert response.success is True
    assert response.source.name == "现场面板"
    assert response.source.uri == "http://panel.local"
    assert response.source.source_type == SourceType.WEB
    assert response.source.keep_alive is False
    assert response.source.preheat_enabled is False
    assert response.source.preview_kind


@pytest.mark.django_db
def test_update_source_updates_web_source_and_rejects_invalid_id() -> None:
    """UpdateSource 应支持部分更新，并稳定拒绝非法 source_id。"""
    servicer = PlaybackControlServicer()
    create_response = servicer.AddWebUrlSource(
        control_pb2.AddWebUrlSourceRequest(url="old.local", name="旧面板"),
        None,
    )

    invalid_response = servicer.UpdateSource(
        control_pb2.UpdateSourceRequest(media_source_id=0, name="无效"),
        None,
    )
    update_response = servicer.UpdateSource(
        control_pb2.UpdateSourceRequest(
            media_source_id=create_response.source.id,
            name="新面板",
            uri="new.local:9000",
            preheat_enabled=False,
        ),
        None,
    )

    assert invalid_response.success is False
    assert "media_source_id" in invalid_response.message
    assert update_response.success is True
    assert update_response.source.name == "新面板"
    assert update_response.source.uri == "http://new.local:9000"
    assert update_response.source.preheat_enabled is False


@pytest.mark.django_db
def test_runtime_status_endpoint_uses_client_visible_host(settings) -> None:
    """GetRuntimeStatus 不应返回不可连接的 wildcard 监听地址。"""
    settings.GRPC_HOST = "0.0.0.0"
    settings.GRPC_PORT = 50051
    servicer = PlaybackControlServicer()

    response = servicer.GetRuntimeStatus(control_pb2.WindowRequest(window_id=1), None)

    assert response.grpc_endpoint == "127.0.0.1:50051"


@pytest.mark.django_db(transaction=True)
def test_grpc_real_channel_source_create_list_update(tmp_path: Path) -> None:
    """真实 channel 应支持媒体源 create/list/update 完整往返。"""
    local_file = tmp_path / "channel-video.mp4"
    local_file.write_bytes(b"fake-video")
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=2))
    control_pb2_grpc.add_PlaybackControlServiceServicer_to_server(
        PlaybackControlServicer(), server,
    )
    port = server.add_insecure_port("127.0.0.1:0")
    server.start()

    try:
        with grpc.insecure_channel(f"127.0.0.1:{port}") as channel:
            stub = control_pb2_grpc.PlaybackControlServiceStub(channel)
            add_reply = stub.AddLocalPathSource(control_pb2.AddLocalPathSourceRequest(
                path=str(local_file),
                name="Channel Video",
            ))
            list_reply = stub.ListSources(control_pb2.ListSourcesRequest(source_type=SourceType.VIDEO))
            update_reply = stub.UpdateSource(control_pb2.UpdateSourceRequest(
                media_source_id=add_reply.source.id,
                name="Updated Channel Video",
            ))

        assert add_reply.success is True
        assert add_reply.source.original_filename == "channel-video.mp4"
        assert any(source.id == add_reply.source.id for source in list_reply.sources)
        assert update_reply.success is True
        assert update_reply.source.name == "Updated Channel Video"
    finally:
        server.stop(grace=0)
