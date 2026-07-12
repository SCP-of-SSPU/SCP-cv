#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''Django 后台播放状态模型测试。'''
from __future__ import annotations

from django.contrib import admin

from scp_cv.apps.playback.admin import (
    BackgroundAudioStateAdmin,
    PlaybackSessionAdmin,
)
from scp_cv.apps.playback.models import BackgroundAudioState, PlaybackSession


def test_legacy_command_mirrors_are_read_only_in_admin() -> None:
    """旧单槽字段只能展示迁移镜像，不得从后台改写。"""
    session_admin = PlaybackSessionAdmin(PlaybackSession, admin.site)
    background_admin = BackgroundAudioStateAdmin(BackgroundAudioState, admin.site)

    expected_fields = {"pending_command", "command_args"}
    assert expected_fields <= set(session_admin.get_readonly_fields(request=None))
    assert expected_fields <= set(background_admin.get_readonly_fields(request=None))
