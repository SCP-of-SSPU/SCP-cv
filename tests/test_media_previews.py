#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
媒体源真实预览与网页预热链路测试。
@Project : SCP-cv
@File : test_media_previews.py
@Author : Qintsg
@Date : 2026-05-09
'''
from __future__ import annotations

from pathlib import Path

import pytest

from scp_cv.apps.playback.models import MediaSource, SourceType
from scp_cv.player.controller import PlayerController
from scp_cv.services.media import add_local_path, add_web_url, list_media_sources, replace_ppt_resources
from scp_cv.services.playback import open_source


@pytest.mark.django_db
def test_ppt_source_uses_first_slide_preview(media_source_ppt: MediaSource) -> None:
    """
    PPT 源列表预览应复用第一页 slide_image。
    :param media_source_ppt: PPT 源测试对象
    :return: None
    """
    replace_ppt_resources(media_source_ppt.pk, [{
        "page_index": 1,
        "slide_image": "/media/ppt_previews/1/slide-1.png",
    }])

    source = list_media_sources(source_type=SourceType.PPT)[0]

    assert source["preview_url"] == "/media/ppt_previews/1/slide-1.png"
    assert source["thumbnail_url"] == "/media/ppt_previews/1/slide-1.png"
    assert source["preview_kind"] == "image"


@pytest.mark.django_db
def test_file_sources_use_inline_preview_endpoint(tmp_path: Path) -> None:
    """
    图片和视频源应返回可嵌入前端缩略位的预览端点。
    :param tmp_path: 临时文件目录
    :return: None
    """
    image_file = tmp_path / "poster.png"
    video_file = tmp_path / "clip.mp4"
    image_file.write_bytes(b"fake-image")
    video_file.write_bytes(b"fake-video")
    image_source = add_local_path(str(image_file))
    video_source = add_local_path(str(video_file))

    sources = {item["id"]: item for item in list_media_sources()}

    assert sources[image_source.pk]["preview_url"] == f"/api/sources/{image_source.pk}/preview/"
    assert sources[image_source.pk]["preview_kind"] == "image"
    assert sources[video_source.pk]["thumbnail_url"] == f"/api/sources/{video_source.pk}/preview/"
    assert sources[video_source.pk]["preview_kind"] == "video"


@pytest.mark.django_db
def test_add_web_url_stores_preheat_flag() -> None:
    """
    网页源创建应把 preheat_enabled 映射到旧 keep_alive 字段。
    :return: None
    """
    source = add_web_url("example.local", display_name="预热关闭", preheat_enabled=False)

    assert source.source_type == SourceType.WEB
    assert source.keep_alive is False


@pytest.mark.django_db
def test_open_source_passes_preheat_flag_to_player() -> None:
    """
    打开网页源时应把预热开关下发给播放器 OPEN 指令。
    :return: None
    """
    source = add_web_url("example.local", display_name="预热关闭", preheat_enabled=False)

    session = open_source(1, source.pk)

    assert session.command_args["source_id"] == source.pk
    assert session.command_args["preheat_enabled"] is False


@pytest.mark.django_db
def test_player_controller_preheats_enabled_web_sources(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    播放器启动预热只应加载可用且开启预热的网页源。
    :param monkeypatch: pytest monkeypatch 工具
    :return: None
    """
    preheated_sources: list[tuple[int, str]] = []

    class FakeWebPreheatPool:
        """记录预热调用的 WebPreheatPool 替身。"""

        def preheat_source(self, source_id: int, url: str) -> None:
            """
            记录 source_id 与 URL。
            :param source_id: 媒体源 ID
            :param url: 网页 URL
            :return: None
            """
            preheated_sources.append((source_id, url))

        def close_all(self) -> None:
            """
            测试替身不需要释放 Qt 资源。
            :return: None
            """
            return

    enabled_source = add_web_url("enabled.local", display_name="启用预热", preheat_enabled=True)
    add_web_url("disabled.local", display_name="关闭预热", preheat_enabled=False)
    MediaSource.objects.create(
        source_type=SourceType.VIDEO,
        name="视频源",
        uri="C:/demo/video.mp4",
        is_available=True,
    )
    monkeypatch.setattr("scp_cv.player.web_preheat.WebPreheatPool", FakeWebPreheatPool)

    controller = PlayerController()
    controller.preheat_web_sources()

    assert preheated_sources == [(enabled_source.pk, enabled_source.uri)]
