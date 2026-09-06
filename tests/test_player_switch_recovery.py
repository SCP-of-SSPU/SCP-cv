"""播放器失败切源的可见画面与会话一致性测试。"""

from __future__ import annotations

import pytest

from scp_cv.apps.playback.models import MediaSource, PlaybackCommand, PlaybackState, SourceType
from scp_cv.player.controller import PlayerController
from scp_cv.services.playback import clear_pending_command, get_session_snapshot, open_source


class _OpenAdapter:
    def open(self, uri: str, window_handle: int, autoplay: bool = True) -> None:
        return

    def close(self) -> None:
        return


class _FailingAdapter(_OpenAdapter):
    def open(self, uri: str, window_handle: int, autoplay: bool = True) -> None:
        raise RuntimeError("new source failed")


class _WindowStub:
    def show_black_screen(self) -> None:
        return

    def show(self) -> None:
        return

    def raise_(self) -> None:
        return

    def show_video_container(self) -> None:
        return


def _prepare_switch(
    controller: PlayerController,
    old_source: MediaSource,
    new_source: MediaSource,
) -> None:
    open_source(1, old_source.pk)
    clear_pending_command(1)
    open_source(1, new_source.pk)
    controller._adapters[1] = _OpenAdapter()
    controller._adapter_source_types[1] = SourceType.VIDEO
    controller._adapter_source_ids[1] = old_source.pk


@pytest.mark.django_db
def test_failed_switch_restores_session_source_to_visible_adapter(
    media_source_video: MediaSource,
    media_source_ppt: MediaSource,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """新源打开异常并恢复旧画面后，会话必须重新指向旧源。"""
    controller = PlayerController()
    _prepare_switch(controller, media_source_video, media_source_ppt)
    monkeypatch.setattr(
        "scp_cv.player.controller_handlers.create_adapter",
        lambda _source_type: _FailingAdapter(),
    )
    monkeypatch.setattr(controller, "get_window_handle", lambda _window_id: 2001)
    monkeypatch.setattr(controller, "get_window", lambda _window_id: _WindowStub())

    controller._execute_command_on_main_thread(
        1,
        PlaybackCommand.OPEN,
        {
            "source_id": media_source_ppt.pk,
            "source_type": SourceType.PPT,
            "uri": media_source_ppt.uri,
            "autoplay": True,
        },
    )

    snapshot = get_session_snapshot(1)
    assert snapshot["source_id"] == media_source_video.pk
    assert snapshot["source_type"] == SourceType.VIDEO
    assert snapshot["playback_state"] == PlaybackState.ERROR
    assert snapshot["error_message"] == "new source failed"


@pytest.mark.django_db
def test_missing_window_handle_restores_previous_session_source(
    media_source_video: MediaSource,
    media_source_ppt: MediaSource,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """窗口句柄缺失时恢复旧 adapter，也必须同步回滚会话源。"""
    controller = PlayerController()
    _prepare_switch(controller, media_source_video, media_source_ppt)
    monkeypatch.setattr(
        "scp_cv.player.controller_handlers.create_adapter",
        lambda _source_type: _OpenAdapter(),
    )
    monkeypatch.setattr(controller, "get_window_handle", lambda _window_id: 0)
    monkeypatch.setattr(controller, "get_window", lambda _window_id: _WindowStub())

    controller._handle_open(1, {
        "source_id": media_source_ppt.pk,
        "source_type": SourceType.PPT,
        "uri": media_source_ppt.uri,
        "autoplay": True,
    })

    snapshot = get_session_snapshot(1)
    assert snapshot["source_id"] == media_source_video.pk
    assert snapshot["source_type"] == SourceType.VIDEO
    assert snapshot["playback_state"] == PlaybackState.ERROR
    assert snapshot["error_message"] == "播放器窗口不可用"
