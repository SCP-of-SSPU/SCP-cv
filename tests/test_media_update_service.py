#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
媒体源更新服务单元测试。
覆盖安全可编辑字段的部分更新、网页 URL 规范化和预热开关兼容行为。
@Project : SCP-cv
@File : test_media_update_service.py
@Author : Qintsg
@Date : 2026-05-15
'''
from __future__ import annotations

import pytest

from scp_cv.apps.playback.models import MediaSource
from scp_cv.services.media import MediaError, add_web_url, update_source


@pytest.mark.django_db
def test_update_source_updates_web_uri_and_preheat_flag() -> None:
    """
    网页源更新应规范化 URI，并同步写入预热开关。
    :return: None
    """
    source = add_web_url("old.local", display_name="旧网页", preheat_enabled=True)

    updated = update_source(
        source.pk,
        name="新网页",
        uri="new.local:8080",
        preheat_enabled=False,
    )

    assert updated.name == "新网页"
    assert updated.uri == "http://new.local:8080"
    assert updated.keep_alive is False


@pytest.mark.django_db
def test_update_source_rejects_empty_name(media_source_video: MediaSource) -> None:
    """
    显示名称显式传空时应返回业务错误。
    :param media_source_video: 视频源测试对象
    :return: None
    """
    with pytest.raises(MediaError, match="显示名称不能为空"):
        update_source(media_source_video.pk, name="  ")


@pytest.mark.django_db
def test_update_source_omitted_fields_keep_existing_values() -> None:
    """
    未传字段表示不修改，避免部分更新误清空已有值。
    :return: None
    """
    source = add_web_url("stable.local", display_name="稳定网页", preheat_enabled=False)

    updated = update_source(source.pk)

    assert updated.name == "稳定网页"
    assert updated.uri == "http://stable.local"
    assert updated.keep_alive is False


@pytest.mark.django_db
def test_update_source_keep_alive_compatibility_flag() -> None:
    """
    旧 keep_alive 字段仍可兼容切换网页预热开关。
    :return: None
    """
    source = add_web_url("compat.local", display_name="兼容网页", preheat_enabled=True)

    updated = update_source(source.pk, keep_alive=False)

    assert updated.keep_alive is False
