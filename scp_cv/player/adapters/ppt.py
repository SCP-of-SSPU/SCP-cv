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
        self._ppt_hwnd: int = 0
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
        """启动幻灯片放映并嵌入到 PySide 播放器窗口中。"""
        if self._presentation is None:
            return

        import win32gui
        import win32con

        # 配置放映参数：使用窗口模式，不占满独立屏幕
        settings = self._presentation.SlideShowSettings
        settings.ShowType = _PP_SLIDE_SHOW_SPEAKER
        settings.StartingSlide = 1
        settings.EndingSlide = self._total_slides
        settings.ShowPresenterView = False

        # 启动放映
        self._slideshow_window = settings.Run()
        self._slideshow_view = self._slideshow_window.View
        self._is_paused = False

        # 获取 PowerPoint 放映窗口的 HWND
        ppt_hwnd = self._find_slideshow_hwnd()
        if ppt_hwnd == 0:
            self._logger.warning("未找到 PowerPoint 放映窗口句柄，无法嵌入")
            return

        self._ppt_hwnd = ppt_hwnd

        # 将 PPT 放映窗口嵌入到 PySide 视频容器中
        # 移除窗口边框和标题栏
        original_style = win32gui.GetWindowLong(ppt_hwnd, win32con.GWL_STYLE)
        embedded_style = (
            original_style
            & ~win32con.WS_OVERLAPPEDWINDOW  # 移除标题栏、边框
            | win32con.WS_CHILD              # 设为子窗口
        )
        win32gui.SetWindowLong(ppt_hwnd, win32con.GWL_STYLE, embedded_style)

        # 移除扩展窗口样式中的顶层属性
        extended_style = win32gui.GetWindowLong(ppt_hwnd, win32con.GWL_EXSTYLE)
        extended_style &= ~win32con.WS_EX_TOPMOST
        extended_style &= ~win32con.WS_EX_APPWINDOW
        win32gui.SetWindowLong(ppt_hwnd, win32con.GWL_EXSTYLE, extended_style)

        # 设置父窗口为 PySide 视频容器
        win32gui.SetParent(ppt_hwnd, self._window_handle)

        # 调整 PPT 窗口大小填满容器
        self._resize_ppt_to_container()

        self._logger.info(
            "PPT 放映已启动并嵌入到播放器窗口（HWND=%d，共 %d 页）",
            ppt_hwnd, self._total_slides,
        )

    def _find_slideshow_hwnd(self) -> int:
        """
        查找 PowerPoint 放映窗口的 HWND。
        优先通过 COM 对象获取，回退到枚举窗口查找。
        :return: 放映窗口句柄，找不到返回 0
        """
        # 方法1：通过 COM SlideShowWindow 获取 HWND
        if self._slideshow_window is not None:
            try:
                ppt_hwnd = self._slideshow_window.HWND
                if ppt_hwnd and ppt_hwnd > 0:
                    self._logger.debug("通过 COM 获取到放映 HWND=%d", ppt_hwnd)
                    return int(ppt_hwnd)
            except Exception as com_error:
                self._logger.debug("COM 获取 HWND 失败：%s，尝试枚举窗口", com_error)

        # 方法2：枚举 Windows 窗口查找 PowerPoint 放映窗口
        import win32gui

        found_hwnd = 0
        # PowerPoint 放映窗口类名为 "screenClass"
        slideshow_class_names = ["screenClass", "paneClassDC"]

        def enum_callback(hwnd: int, _extra: object) -> bool:
            nonlocal found_hwnd
            if win32gui.IsWindowVisible(hwnd):
                class_name = win32gui.GetClassName(hwnd)
                if class_name in slideshow_class_names:
                    found_hwnd = hwnd
                    return False  # 停止枚举
            return True

        try:
            win32gui.EnumWindows(enum_callback, None)
        except Exception:
            # EnumWindows 在回调返回 False 时会抛异常，正常行为
            pass

        if found_hwnd > 0:
            self._logger.debug("通过枚举窗口找到放映 HWND=%d", found_hwnd)
        else:
            self._logger.warning("未能找到 PowerPoint 放映窗口")

        return found_hwnd

    def _resize_ppt_to_container(self) -> None:
        """
        调整 PPT 放映窗口大小以填满 PySide 视频容器。
        通过 Qt 获取容器尺寸，再用 Win32 API 设置 PPT 窗口位置和大小。
        """
        if not hasattr(self, '_ppt_hwnd') or self._ppt_hwnd == 0:
            return

        import win32gui
        import win32con

        # 获取容器尺寸
        container_rect = win32gui.GetClientRect(self._window_handle)
        container_width = container_rect[2] - container_rect[0]
        container_height = container_rect[3] - container_rect[1]

        # 移动并调整大小
        win32gui.SetWindowPos(
            self._ppt_hwnd,
            win32con.HWND_TOP,
            0, 0,
            container_width, container_height,
            win32con.SWP_NOZORDER | win32con.SWP_SHOWWINDOW,
        )
        self._logger.debug(
            "PPT 窗口已调整大小：%dx%d", container_width, container_height,
        )

    def close(self) -> None:
        """关闭 PPT 放映并释放 COM 资源。"""
        with self._com_lock:
            self._close_com_resources()
        self._mark_closed()
        self._logger.info("PPT 已关闭")

    def _close_com_resources(self) -> None:
        """释放所有 COM 资源，并解除 PPT 窗口嵌入。"""
        import pythoncom

        try:
            # 先解除父窗口关系，避免 PowerPoint 关闭时影响 PySide 窗口
            if self._ppt_hwnd != 0:
                try:
                    import win32gui
                    win32gui.SetParent(self._ppt_hwnd, 0)  # 还原为顶层窗口
                except Exception:
                    pass
                self._ppt_hwnd = 0

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
