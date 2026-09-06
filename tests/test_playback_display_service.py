#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
播放显示目标选择服务测试，只覆盖单窗口单显示器配置。
@Project : SCP-cv
@File : test_playback_display_service.py
@Author : Qintsg
@Date : 2026-05-02
'''
from __future__ import annotations

from unittest.mock import patch

import pytest

from scp_cv.apps.playback.models import PlaybackMode
from scp_cv.services.playback import PlaybackError, select_display_target


@pytest.mark.django_db
class TestSelectDisplayTarget:
    """测试显示目标选择。"""

    def _make_display_target(
        self, name: str, index: int, is_primary: bool = False,
    ) -> object:
        """
        构造一个 DisplayTarget 数据类实例。
        :param name: 显示器名称
        :param index: 显示器索引
        :param is_primary: 是否主屏
        :return: DisplayTarget 实例
        """
        from scp_cv.services.display import DisplayTarget
        return DisplayTarget(
            name=name,
            index=index,
            is_primary=is_primary,
            x=0 if index == 0 else 1920,
            y=0,
            width=1920,
            height=1080,
        )

    @patch("scp_cv.services.playback.list_display_targets")
    def test_select_single_display(self, mock_displays: object) -> None:
        """选择单屏模式应正确设置目标显示器。"""
        mock_displays.return_value = [
            self._make_display_target("HDMI-1", 0, is_primary=True),
            self._make_display_target("HDMI-2", 1),
        ]

        session = select_display_target(1, PlaybackMode.SINGLE, "HDMI-2")

        assert session.display_mode == PlaybackMode.SINGLE
        assert session.target_display_label == "HDMI-2"

    @patch("scp_cv.services.playback.list_display_targets")
    def test_select_nonexistent_display_raises(self, mock_displays: object) -> None:
        """选择不存在的显示器应抛出 PlaybackError。"""
        mock_displays.return_value = [
            self._make_display_target("HDMI-1", 0, is_primary=True),
        ]

        with pytest.raises(PlaybackError, match="不存在"):
            select_display_target(1, PlaybackMode.SINGLE, "VGA-1")

    def test_unknown_display_mode_raises(self) -> None:
        """未知的显示模式应抛出 PlaybackError。"""
        with pytest.raises(PlaybackError, match="未知"):
            select_display_target(1, "triple_screen")
