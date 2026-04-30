#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
系统音量服务测试。
覆盖 Windows Core Audio 成功路径和运行态回退路径。
@Project : SCP-cv
@File : test_volume_service.py
@Author : Qintsg
@Date : 2026-04-30
'''
from __future__ import annotations

from typing import Any

import pytest

from scp_cv.apps.playback.models import RuntimeState
from scp_cv.services import volume as volume_service


@pytest.mark.django_db
def test_get_system_volume_uses_windows_backend(monkeypatch: Any) -> None:
    """Core Audio 可用时应返回同步系统音量。"""
    monkeypatch.setattr(volume_service, "_get_windows_master_volume", lambda: (42, False))

    payload = volume_service.get_system_volume()

    assert payload["level"] == 42
    assert payload["muted"] is False
    assert payload["system_synced"] is True
    assert RuntimeState.get_instance().volume_level == 42
    assert RuntimeState.get_instance().volume_muted is False


@pytest.mark.django_db
def test_set_system_volume_falls_back_to_runtime(monkeypatch: Any) -> None:
    """Core Audio 不可用时应写入运行态并明确标记未同步系统。"""
    def raise_volume_error(*_args: object, **_kwargs: object) -> None:
        """
        模拟 Core Audio 调用失败。
        :return: None
        """
        raise volume_service.VolumeError("audio unavailable")

    monkeypatch.setattr(volume_service, "_set_windows_master_volume", raise_volume_error)

    payload = volume_service.set_system_volume(30, True)

    assert payload["level"] == 30
    assert payload["muted"] is True
    assert payload["system_synced"] is False
    assert RuntimeState.get_instance().volume_level == 30
    assert RuntimeState.get_instance().volume_muted is True


@pytest.mark.django_db
def test_get_system_volume_fallback_preserves_muted(monkeypatch: Any) -> None:
    """Core Audio 读取失败时应返回运行态静音状态。"""
    runtime = RuntimeState.get_instance()
    runtime.volume_level = 60
    runtime.volume_muted = True
    runtime.save(update_fields=["volume_level", "volume_muted"])

    def raise_volume_error() -> None:
        """
        模拟 Core Audio 读取失败。
        :return: None
        """
        raise volume_service.VolumeError("audio unavailable")

    monkeypatch.setattr(volume_service, "_get_windows_master_volume", raise_volume_error)

    payload = volume_service.get_system_volume()

    assert payload["level"] == 60
    assert payload["muted"] is True
    assert payload["system_synced"] is False
