#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
背景音频服务与 REST API 单元测试。
@Project : SCP-cv
@File : test_background_audio_service.py
@Author : Qintsg
@Date : 2026-05-31
'''
from __future__ import annotations

import json
from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client

from scp_cv.apps.playback.models import (
    BackgroundAudioCommand,
    BackgroundAudioPlaylistItem,
    BackgroundAudioState,
    MediaSource,
    PlaybackState,
)
from scp_cv.services.background_audio import (
    BackgroundAudioError,
    add_source_to_playlist,
    play_source,
    remove_playlist_item,
    resume_background_audio,
    stop_background_audio,
)
from scp_cv.services.media import add_uploaded_file


@pytest.mark.django_db
def test_play_source_adds_playlist_and_opens_audio(media_source_audio: MediaSource) -> None:
    """
    立即播放音频源时应加入列表并下发 OPEN 指令。
    :param media_source_audio: 音频媒体源
    :return: None
    """
    state = play_source(media_source_audio.pk)

    assert BackgroundAudioPlaylistItem.objects.filter(source=media_source_audio).exists()
    assert state.current_source == media_source_audio
    assert state.pending_command == BackgroundAudioCommand.OPEN
    assert state.command_args["source_id"] == media_source_audio.pk
    assert state.command_args["uri"] == media_source_audio.uri


@pytest.mark.django_db
def test_add_source_to_playlist_rejects_non_audio(media_source_video: MediaSource) -> None:
    """
    背景音乐播放列表只接受 audio 媒体源。
    :param media_source_video: 视频媒体源
    :return: None
    """
    with pytest.raises(BackgroundAudioError, match="音频源"):
        add_source_to_playlist(media_source_video.pk)


@pytest.mark.django_db
def test_remove_current_playlist_item_stops_background_audio(media_source_audio: MediaSource) -> None:
    """
    删除当前播放项时应停止并清空背景音乐当前源。
    :param media_source_audio: 音频媒体源
    :return: None
    """
    state = play_source(media_source_audio.pk)
    item = BackgroundAudioPlaylistItem.objects.get(source=media_source_audio)
    state.pending_command = BackgroundAudioCommand.NONE
    state.command_args = {}
    state.save(update_fields=["pending_command", "command_args", "updated_at"])

    next_state = remove_playlist_item(item.pk)

    assert next_state.current_source_id is None
    assert next_state.pending_command == BackgroundAudioCommand.STOP
    assert next_state.command_args == {"clear_source": True}
    assert not BackgroundAudioPlaylistItem.objects.filter(pk=item.pk).exists()


@pytest.mark.django_db
def test_stop_background_audio_deletes_temporary_audio_source(tmp_path: Path, settings) -> None:
    """
    临时上传音频进入背景音乐后，停止时应删除源记录和上传文件。
    :param tmp_path: 临时目录
    :param settings: Django settings fixture
    :return: None
    """
    settings.MEDIA_ROOT = tmp_path / "media"
    source = add_uploaded_file(SimpleUploadedFile("temp.mp3", b"fake-audio"), is_temporary=True)
    uploaded_path = Path(source.uploaded_file.path)
    play_source(source.pk)

    state = stop_background_audio()

    assert state.current_source_id is None
    assert state.command_args == {"clear_source": True}
    assert not MediaSource.objects.filter(pk=source.pk).exists()
    assert not BackgroundAudioPlaylistItem.objects.filter(source_id=source.pk).exists()
    assert not uploaded_path.exists()


@pytest.mark.django_db
def test_remove_temporary_playlist_item_deletes_source(
    media_source_audio: MediaSource,
    tmp_path: Path,
    settings,
) -> None:
    """
    删除非当前临时音频列表项时，应同步删除临时媒体源。
    :param media_source_audio: 当前播放的持久音频源
    :param tmp_path: 临时目录
    :param settings: Django settings fixture
    :return: None
    """
    settings.MEDIA_ROOT = tmp_path / "media"
    temp_source = add_uploaded_file(SimpleUploadedFile("temp.mp3", b"fake-audio"), is_temporary=True)
    uploaded_path = Path(temp_source.uploaded_file.path)
    play_source(media_source_audio.pk)
    temp_item = add_source_to_playlist(temp_source.pk)

    state = remove_playlist_item(temp_item.pk)

    assert state.current_source_id == media_source_audio.pk
    assert not MediaSource.objects.filter(pk=temp_source.pk).exists()
    assert not BackgroundAudioPlaylistItem.objects.filter(source_id=temp_source.pk).exists()
    assert not uploaded_path.exists()


@pytest.mark.django_db
def test_resume_background_audio_reopens_after_error(media_source_audio: MediaSource) -> None:
    """
    背景音频错误后点击播放应重新打开源，而不是只发送 PLAY。
    :param media_source_audio: 音频媒体源
    :return: None
    """
    state = play_source(media_source_audio.pk)
    state.playback_state = PlaybackState.ERROR
    state.error_message = "decode failed"
    state.pending_command = BackgroundAudioCommand.NONE
    state.command_args = {}
    state.save(update_fields=["playback_state", "error_message", "pending_command", "command_args", "updated_at"])

    next_state = resume_background_audio()

    assert next_state.pending_command == BackgroundAudioCommand.OPEN
    assert next_state.playback_state == PlaybackState.LOADING
    assert next_state.command_args["source_id"] == media_source_audio.pk


@pytest.mark.django_db
def test_background_audio_play_source_api(media_source_audio: MediaSource) -> None:
    """
    REST API 应返回背景音乐快照并写入播放器指令。
    :param media_source_audio: 音频媒体源
    :return: None
    """
    client = Client()

    response = client.post(
        "/api/background-audio/play-source/",
        data=json.dumps({"source_id": media_source_audio.pk}),
        content_type="application/json",
    )

    assert response.status_code == 200
    payload = response.json()["background_audio"]
    assert payload["state"]["source_id"] == media_source_audio.pk
    assert payload["state"]["pending_command"] == BackgroundAudioCommand.OPEN
    assert payload["playlist"][0]["source_id"] == media_source_audio.pk
    assert BackgroundAudioState.get_instance().current_source_id == media_source_audio.pk
