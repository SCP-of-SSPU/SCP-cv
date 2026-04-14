#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PPT 源适配器，通过 PowerPoint COM 自动化控制幻灯片放映。
在指定屏幕上以放映模式展示 PPT/PPTX/PPSX 文件。
@Project : SCP-cv
@File : ppt.py
@Author : Qintsg
@Date : 2026-04-15
'''
from __future__ import annotations

import logging
import os
import threading
from typing import Optional

from scp_cv.player.adapters.base import AdapterState, SourceAdapter

logger = logging.getLogger(__name__)

# PowerPoint 放映推进类型常量
_PP_ADVANCE_MODE_ON_CLICK = 1  # ppAdvanceOnClick
_PP_SLIDE_SHOW_WINDOW = 1      # ppShowTypeWindow
_PP_SLIDE_SHOW_SPEAKER = 1     # ppShowTypeSpeaker
_PP_SLIDE_SHOW_KIOSK = 3       # ppShowTypeKiosk

# 放映状态常量
_PP_SLIDE_SHOW_RUNNING = 1     # ppSlideShowRunning
_PP_SLIDE_SHOW_PAUSED = 2      # ppSlideShowPaused
_PP_SLIDE_SHOW_DONE = 5        # ppSlideShowDone


class PptSourceAdapter(SourceAdapter):
    """
    PowerPoint COM 放映适配器。

    通过 win32com 操控 PowerPoint 应用程序，在指定屏幕上进行幻灯片放映。
    PPT 窗口定位到 PySide 播放器窗口所在的屏幕区域。

    线程安全说明：
    - COM 操作必须在创建 COM 对象的同一线程中执行
    - 使用 pythoncom.CoInitialize/CoUninitialize 管理 COM 线程
    """

    def __init__(self) -> None:
        super().__init__(adapter_name="ppt")
        self._ppt_app: Optional[object] = None        # PowerPoint.Application COM 对象
        self._presentation: Optional[object] = None    # Presentation 对象
        self._slideshow_view: Optional[object] = None  # SlideShowView 对象
        self._slideshow_window: Optional[object] = None  # SlideShowWindow 对象
        self._total_slides: int = 0
        self._file_path: str = ""
        self._window_handle: int = 0
        self._is_paused: bool = False
        # COM 线程锁（所有 COM 调用须串行）
        self._com_lock = threading.Lock()

    def open(self, uri: str, window_handle: int, autoplay: bool = True) -> None:
        """
        打开 PPT 文件并启动幻灯片放映。
        放映窗口定位到 window_handle 所在屏幕。
        :param uri: PPT 文件绝对路径
        :param window_handle: PySide 窗口原生句柄（用于定位屏幕）
        :param autoplay: 是否立即开始放映
        """
        if not os.path.isfile(uri):
            raise FileNotFoundError(f"PPT 文件不存在：{uri}")

        self._file_path = uri
        self._window_handle = window_handle

        with self._com_lock:
            self._init_com_and_open(uri, autoplay)

        self._mark_open()
        self._logger.info("PPT 已打开：%s（%d 页）", uri, self._total_slides)

    def _init_com_and_open(self, file_path: str, autoplay: bool) -> None:
        """
        初始化 COM 环境并打开 PPT 文件。
        :param file_path: PPT 文件路径
        :param autoplay: 是否自动开始放映
        """
        import pythoncom
        import win32com.client

        pythoncom.CoInitialize()

        # 获取或创建 PowerPoint 实例
        try:
            self._ppt_app = win32com.client.GetActiveObject("PowerPoint.Application")
        except Exception:
            self._ppt_app = win32com.client.Dispatch("PowerPoint.Application")

        # 最小化 PowerPoint 编辑窗口
        self._ppt_app.WindowState = 2  # ppWindowMinimized

        # 打开演示文稿（只读）
        self._presentation = self._ppt_app.Presentations.Open(
            file_path,
            ReadOnly=True,   # 只读
            Untitled=False,
            WithWindow=False,  # 不显示编辑窗口
        )
        self._total_slides = self._presentation.Slides.Count

        if autoplay:
            self._start_slideshow()

    def _start_slideshow(self) -> None:
        """启动幻灯片放映并定位到目标屏幕。"""
        if self._presentation is None:
            return

        # 配置放映参数
        settings = self._presentation.SlideShowSettings
        settings.ShowType = _PP_SLIDE_SHOW_SPEAKER
        settings.StartingSlide = 1
        settings.EndingSlide = self._total_slides

        # 定位放映到目标屏幕（通过 PySide 窗口句柄查找屏幕编号）
        screen_index = self._find_screen_index_for_handle(self._window_handle)
        if screen_index > 0:
            settings.ShowPresenterView = False
            # COM 屏幕编号从 1 开始
            try:
                settings.PrimaryMonitor = screen_index
            except Exception as monitor_error:
                self._logger.warning(
                    "设置目标屏幕失败（index=%d）：%s", screen_index, monitor_error,
                )

        # 启动放映
        self._slideshow_window = settings.Run()
        self._slideshow_view = self._slideshow_window.View
        self._is_paused = False

        self._logger.info(
            "PPT 放映已启动（屏幕=%d，共 %d 页）", screen_index, self._total_slides,
        )

    @staticmethod
    def _find_screen_index_for_handle(window_handle: int) -> int:
        """
        通过窗口句柄查找所在屏幕的 COM 编号（1-based）。
        :param window_handle: 原生窗口句柄
        :return: 屏幕编号（1-based），找不到返回 1（主屏幕）
        """
        try:
            from PySide6.QtWidgets import QApplication
            from PySide6.QtGui import QWindow

            # 通过 Qt 获取窗口所在屏幕
            app = QApplication.instance()
            if app is None:
                return 1

            screens = app.screens()
            # 尝试通过 winId 关联找到目标窗口
            for widget in app.topLevelWidgets():
                if int(widget.winId()) == window_handle:
                    window_screen = widget.screen()
                    if window_screen is not None:
                        for screen_index, screen in enumerate(screens, start=1):
                            if screen.name() == window_screen.name():
                                return screen_index
            return 1
        except Exception:
            return 1

    def close(self) -> None:
        """关闭 PPT 放映并释放 COM 资源。"""
        with self._com_lock:
            self._close_com_resources()
        self._mark_closed()
        self._logger.info("PPT 已关闭")

    def _close_com_resources(self) -> None:
        """释放所有 COM 资源。"""
        import pythoncom

        try:
            if self._slideshow_view is not None:
                try:
                    self._slideshow_view.Exit()
                except Exception:
                    pass
                self._slideshow_view = None
                self._slideshow_window = None

            if self._presentation is not None:
                try:
                    self._presentation.Close()
                except Exception:
                    pass
                self._presentation = None

            self._ppt_app = None
        finally:
            try:
                pythoncom.CoUninitialize()
            except Exception:
                pass

        self._total_slides = 0
        self._is_paused = False

    # ═══════════════════ 播放控制 ═══════════════════

    def play(self) -> None:
        """恢复放映（从暂停状态）。"""
        with self._com_lock:
            if self._slideshow_view is not None and self._is_paused:
                try:
                    self._slideshow_view.State = _PP_SLIDE_SHOW_RUNNING
                    self._is_paused = False
                except Exception as resume_error:
                    self._logger.warning("恢复放映失败：%s", resume_error)

    def pause(self) -> None:
        """暂停放映。"""
        with self._com_lock:
            if self._slideshow_view is not None and not self._is_paused:
                try:
                    self._slideshow_view.State = _PP_SLIDE_SHOW_PAUSED
                    self._is_paused = True
                except Exception as pause_error:
                    self._logger.warning("暂停放映失败：%s", pause_error)

    def stop(self) -> None:
        """停止放映（退出放映模式，但不关闭文件）。"""
        with self._com_lock:
            if self._slideshow_view is not None:
                try:
                    self._slideshow_view.Exit()
                except Exception:
                    pass
                self._slideshow_view = None
                self._slideshow_window = None
                self._is_paused = False

    # ═══════════════════ 幻灯片导航 ═══════════════════

    def next_item(self) -> None:
        """下一页。"""
        with self._com_lock:
            if self._slideshow_view is not None:
                try:
                    self._slideshow_view.Next()
                except Exception as nav_error:
                    self._logger.warning("PPT 翻页（下一页）失败：%s", nav_error)

    def prev_item(self) -> None:
        """上一页。"""
        with self._com_lock:
            if self._slideshow_view is not None:
                try:
                    self._slideshow_view.Previous()
                except Exception as nav_error:
                    self._logger.warning("PPT 翻页（上一页）失败：%s", nav_error)

    def goto_item(self, index: int) -> None:
        """
        跳转到指定页。
        :param index: 页码（1-based）
        """
        if index < 1 or index > self._total_slides:
            self._logger.warning("无效页码 %d（总计 %d 页）", index, self._total_slides)
            return

        with self._com_lock:
            if self._slideshow_view is not None:
                try:
                    self._slideshow_view.GotoSlide(index)
                except Exception as goto_error:
                    self._logger.warning("PPT 跳转到第 %d 页失败：%s", index, goto_error)

    # ═══════════════════ 状态获取 ═══════════════════

    def get_state(self) -> AdapterState:
        """
        获取 PPT 放映状态。
        :return: 包含当前页码和总页数的状态快照
        """
        current_slide = 0
        playback_state = "idle"

        with self._com_lock:
            if self._slideshow_view is not None:
                try:
                    slideshow_state = self._slideshow_view.State
                    current_slide = self._slideshow_view.CurrentShowPosition

                    if slideshow_state == _PP_SLIDE_SHOW_RUNNING:
                        playback_state = "playing"
                    elif slideshow_state == _PP_SLIDE_SHOW_PAUSED:
                        playback_state = "paused"
                    elif slideshow_state == _PP_SLIDE_SHOW_DONE:
                        playback_state = "stopped"
                    else:
                        playback_state = "playing"
                except Exception:
                    playback_state = "error"
            elif self._presentation is not None:
                # 文件已打开但未在放映
                playback_state = "stopped"

        return AdapterState(
            playback_state=playback_state,
            current_slide=current_slide,
            total_slides=self._total_slides,
        )
