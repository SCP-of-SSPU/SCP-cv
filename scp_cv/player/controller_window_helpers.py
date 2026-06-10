#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
播放器控制器窗口显示辅助 mixin。
@Project : SCP-cv
@File : controller_window_helpers.py
@Author : Qintsg
@Date : 2026-06-10
'''
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class PlayerWindowHelpersMixin:
    """封装 PlayerController 的窗口显示和 PPT 嵌入容器辅助逻辑。"""

    def _show_ppt_container(self, window_id: int) -> None:
        """
        切换到嵌入式 PPT 显示容器，并保持 PySide 播放窗口可见和置顶。
        :param window_id: 窗口编号
        :return: None
        """
        window = self.get_window(window_id)
        if window is None:
            return
        show_video_container = getattr(window, "show_video_container", None)
        if callable(show_video_container):
            show_video_container()
        window.show()
        self._set_player_window_topmost(window, True)
        window.raise_()

    def _restore_player_window_to_black(self, window_id: int) -> None:
        """
        恢复 PySide 播放窗口并显示黑屏。
        :param window_id: 窗口编号
        :return: None
        """
        window = self.get_window(window_id)
        if window is None:
            return
        window.show_black_screen()
        window.show()
        self._set_player_window_topmost(window, True)
        window.raise_()

    @staticmethod
    def _prepare_ppt_container(window_id: int, window: object) -> None:
        """
        首次打开 PPT 前激活嵌入容器，避免 PowerPoint 读取到未 show 的小矩形。
        :param window_id: 窗口编号
        :param window: PlayerWindow 或测试替身
        :return: None
        """
        try:
            prepare_container = getattr(window, "prepare_ppt_container", None)
            if callable(prepare_container):
                prepare_container()
                return
            show_video_container = getattr(window, "show_video_container", None)
            if callable(show_video_container):
                show_video_container()
                window.show()
                window.raise_()
        except Exception as prepare_error:
            logger.debug("窗口 %d PPT 嵌入容器激活失败：%s", window_id, prepare_error)

    @staticmethod
    def _prepare_video_render_window(window_id: int, window: object) -> None:
        """
        前台打开直播/视频前激活原生渲染容器，确保 libVLC 绑定的 HWND 可见。
        :param window_id: 窗口编号
        :param window: PlayerWindow 或测试替身
        :return: None
        """
        try:
            show_video_container = getattr(window, "show_video_container", None)
            if callable(show_video_container):
                show_video_container()
            window.show()
            window.raise_()
        except Exception as prepare_error:
            logger.debug("窗口 %d 视频渲染容器激活失败：%s", window_id, prepare_error)

    @staticmethod
    def _detach_ppt_for_fast_switch(adapter: object | None) -> None:
        """
        切离 PPT 前先隐藏嵌入式子窗口，让新内容可以尽快接管 PySide 容器。
        :param adapter: 旧 PPT 适配器
        :return: None
        """
        detach = getattr(adapter, "detach_for_fast_switch", None)
        if not callable(detach):
            return
        try:
            detach()
        except Exception as detach_error:
            logger.debug("切离 PPT 时隐藏嵌入窗口失败：%s", detach_error)

    @staticmethod
    def _restore_ppt_after_failed_switch(adapter: object | None) -> None:
        """
        新源打开失败后恢复已隐藏的 PPT 嵌入子窗口。
        :param adapter: 待恢复的旧 PPT 适配器
        :return: None
        """
        restore = getattr(adapter, "restore_after_failed_switch", None)
        if not callable(restore):
            return
        try:
            restore()
        except Exception as restore_error:
            logger.debug("恢复 PPT 嵌入窗口失败：%s", restore_error)

    @staticmethod
    def _set_player_window_topmost(window: object, enabled: bool) -> None:
        """
        调整播放器窗口置顶状态，兼容测试替身。
        :param window: PlayerWindow 或测试替身
        :param enabled: 是否置顶
        :return: None
        """
        set_topmost = getattr(window, "set_always_on_top", None)
        if callable(set_topmost):
            set_topmost(enabled)


__all__ = ["PlayerWindowHelpersMixin"]
