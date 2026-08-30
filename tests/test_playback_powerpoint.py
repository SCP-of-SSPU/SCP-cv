#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PowerPoint 播放服务测试，覆盖全局单槽位、重置、媒体控制和关闭流程。
@Project : SCP-cv
@File : test_playback_powerpoint.py
@Author : Qintsg
@Date : 2026-08-23
'''
from __future__ import annotations

from pathlib import Path

import pytest

from scp_cv.apps.playback.models import (
    MediaSource,
    PlaybackCommand,
    PlaybackState,
)
from scp_cv.services.playback import (
    PlaybackError,
    clear_pending_command,
    close_source,
    control_ppt_media,
    get_or_create_session,
    open_source,
    reset_ppt_playback,
    stop_current_content,
    update_playback_progress,
)
from scp_cv.services.ppt_playback_cache import PPT_PLAYBACK_METADATA_KEY


@pytest.mark.django_db
def test_open_powerpoint_does_not_preempt_other_powerpoint_window(
    media_source_ppt: MediaSource,
) -> None:
    """
    第二个 PowerPoint 请求不能抢占其它窗口；运行时槽位冲突后应选择 PDF。

    :param media_source_ppt: PowerPoint 媒体源
    :return: None
    """
    open_source(1, media_source_ppt.pk)
    target_session = open_source(2, media_source_ppt.pk)
    previous_session = get_or_create_session(1)
    assert previous_session.pending_command == PlaybackCommand.OPEN
    assert previous_session.playback_state == PlaybackState.LOADING
    assert target_session.pending_command == PlaybackCommand.OPEN


@pytest.mark.django_db
def test_open_pdf_slides_keeps_other_powerpoint_window(
    media_source_ppt: MediaSource,
    tmp_path: Path,
) -> None:
    """
    PDF 演示文稿不占用 PowerPoint 槽位。

    :param media_source_ppt: PowerPoint 媒体源
    :param tmp_path: PDF 测试文件目录
    :return: None
    """
    open_source(1, media_source_ppt.pk)
    pdf_path = tmp_path / "slides.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")
    pdf_source = MediaSource.objects.create(
        source_type="ppt",
        name="PDF 演示文稿",
        uri=str(pdf_path),
        metadata={"playback_mode": "pdf"},
    )
    open_source(2, pdf_source.pk)
    assert get_or_create_session(1).pending_command == PlaybackCommand.OPEN


@pytest.mark.django_db
class TestControlPptMedia:
    """测试 PowerPoint 当前页媒体逐项控制。"""

    def test_control_ppt_media_command(self, media_source_ppt: MediaSource) -> None:
        """
        媒体控制应写入专用指令和参数。

        :param media_source_ppt: PowerPoint 媒体源
        :return: None
        """
        open_source(1, media_source_ppt.pk)
        session = control_ppt_media(1, PlaybackCommand.PLAY, media_id="m1", media_index=2)
        assert session.pending_command == PlaybackCommand.PPT_MEDIA
        assert session.command_args["media_action"] == PlaybackCommand.PLAY
        assert session.command_args["media_id"] == "m1"
        assert session.command_args["media_index"] == 2

    def test_ppt_media_command_after_powerpoint_open(
        self,
        media_source_ppt: MediaSource,
    ) -> None:
        """
        PowerPoint 源应下发媒体控制指令。

        :param media_source_ppt: PowerPoint 媒体源
        :return: None
        """
        open_source(1, media_source_ppt.pk)
        session = control_ppt_media(1, PlaybackCommand.PLAY, media_id="m1", media_index=1)
        assert session.pending_command == PlaybackCommand.PPT_MEDIA
        assert session.command_args["media_action"] == PlaybackCommand.PLAY

    def test_rejects_non_ppt_source(self, media_source_video: MediaSource) -> None:
        """
        非 PowerPoint 源不应接受媒体控制。

        :param media_source_video: 视频媒体源
        :return: None
        """
        open_source(1, media_source_video.pk)
        with pytest.raises(PlaybackError, match="未打开 PPT"):
            control_ppt_media(1, PlaybackCommand.PLAY, media_id="m1", media_index=1)


@pytest.mark.django_db
class TestPptResetOperations:
    """测试 PowerPoint 放映重置。"""

    def test_reset_keeps_current_slide(self, media_source_ppt: MediaSource) -> None:
        """
        重置应保留当前页码。

        :param media_source_ppt: PowerPoint 媒体源
        :return: None
        """
        open_source(1, media_source_ppt.pk)
        update_playback_progress(1, current_slide=5, total_slides=10)
        clear_pending_command(1)
        reset_ppt_playback()
        session = get_or_create_session(1)
        restart_sessions = session.command_args["restart_sessions"]
        assert session.pending_command == PlaybackCommand.RESET_PPT
        assert restart_sessions[0]["source_id"] == media_source_ppt.pk
        assert restart_sessions[0]["target_slide"] == 5
        assert "reset_token" in session.command_args

    def test_reset_only_targets_current_powerpoint_window(
        self,
        media_source_ppt: MediaSource,
    ) -> None:
        """
    多窗口请求由运行时单槽位区分；服务层不得预先假定哪个窗口持有 COM。

        :param media_source_ppt: PowerPoint 媒体源
        :return: None
        """
        open_source(1, media_source_ppt.pk)
        open_source(2, media_source_ppt.pk)
        clear_pending_command(1)
        clear_pending_command(2)
        reset_ppt_playback()
        assert get_or_create_session(1).pending_command == PlaybackCommand.RESET_PPT
        assert get_or_create_session(2).pending_command == PlaybackCommand.RESET_PPT

    def test_reset_uses_ready_playback_cache(
        self,
        media_source_ppt: MediaSource,
        tmp_path: Path,
    ) -> None:
        """
        重置时继续使用已就绪的放映缓存。

        :param media_source_ppt: PowerPoint 媒体源
        :param tmp_path: 缓存测试目录
        :return: None
        """
        cached_file = tmp_path / "cached.ppsx"
        cached_file.write_bytes(b"cached-show")
        media_source_ppt.metadata = {
            PPT_PLAYBACK_METADATA_KEY: {"status": "ready", "path": str(cached_file)}
        }
        media_source_ppt.save(update_fields=["metadata"])
        open_source(1, media_source_ppt.pk)
        update_playback_progress(1, current_slide=2, total_slides=5)
        clear_pending_command(1)
        reset_ppt_playback()
        restart_args = get_or_create_session(1).command_args["restart_sessions"][0]
        assert restart_args["uri"] == str(cached_file)
        assert restart_args["original_uri"] == media_source_ppt.uri

    def test_reset_ignores_pdf_slides(self, tmp_path: Path) -> None:
        """
        PowerPoint 重置不得关闭或重开 PDF 演示文稿。

        :param tmp_path: PDF 测试文件目录
        :return: None
        """
        pdf_path = tmp_path / "slides.pdf"
        pdf_path.write_bytes(b"%PDF-1.4")
        pdf_source = MediaSource.objects.create(
            source_type="ppt",
            name="PDF 演示文稿",
            uri=str(pdf_path),
            metadata={"playback_mode": "pdf"},
        )
        open_source(1, pdf_source.pk)
        clear_pending_command(1)
        reset_ppt_playback()
        session = get_or_create_session(1)
        assert session.pending_command == PlaybackCommand.NONE
        assert session.playback_state == PlaybackState.LOADING


@pytest.mark.django_db
class TestCloseSource:
    """测试源关闭和会话重置。"""

    def test_close_with_active_source(self, media_source_video: MediaSource) -> None:
        """
        有活跃源时关闭应发出 CLOSE 指令。

        :param media_source_video: 视频媒体源
        :return: None
        """
        open_source(1, media_source_video.pk)
        assert close_source(1).pending_command == PlaybackCommand.CLOSE

    def test_close_marks_temporary_source_for_cleanup(
        self,
        media_source_video: MediaSource,
    ) -> None:
        """
        关闭临时源时应下发清理 ID。

        :param media_source_video: 视频媒体源
        :return: None
        """
        media_source_video.is_temporary = True
        media_source_video.save(update_fields=["is_temporary"])
        open_source(1, media_source_video.pk)
        assert close_source(1).command_args["cleanup_source_id"] == media_source_video.pk

    def test_close_without_source_resets(self) -> None:
        """
        无活跃源时关闭应直接重置为 IDLE。

        :return: None
        """
        get_or_create_session(1)
        session = close_source(1)
        assert session.playback_state == PlaybackState.IDLE
        assert session.pending_command == PlaybackCommand.NONE

    def test_stop_current_content_delegates(self, media_source_video: MediaSource) -> None:
        """
        停止当前内容应委托给关闭流程。

        :param media_source_video: 视频媒体源
        :return: None
        """
        open_source(1, media_source_video.pk)
        assert stop_current_content(1).pending_command == PlaybackCommand.CLOSE


@pytest.mark.django_db
def test_clear_pending_command_and_args(media_source_ppt: MediaSource) -> None:
    """
    播放器消费指令后应同时清除指令和参数。

    :param media_source_ppt: PowerPoint 媒体源
    :return: None
    """
    open_source(1, media_source_ppt.pk)
    session = clear_pending_command(1)
    assert session.pending_command == PlaybackCommand.NONE
    assert session.command_args == {}
