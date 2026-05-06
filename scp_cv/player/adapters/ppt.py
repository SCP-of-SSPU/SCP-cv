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
from scp_cv.player.adapters.ppt_constants import (
    PP_ALERTS_ALL as _PP_ALERTS_ALL,
    PP_ALERTS_NONE as _PP_ALERTS_NONE,
    PP_SLIDE_SHOW_DONE as _PP_SLIDE_SHOW_DONE,
    PP_SLIDE_SHOW_PAUSED as _PP_SLIDE_SHOW_PAUSED,
    PP_SLIDE_SHOW_RUNNING as _PP_SLIDE_SHOW_RUNNING,
)
from scp_cv.player.adapters.ppt_window import (
    detach_slideshow_window,
    embed_slideshow_window,
    find_slideshow_hwnd,
    resize_slideshow_window,
)

logger = logging.getLogger(__name__)


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
        self._last_slide_index: int = 1
        self._owns_ppt_app: bool = False
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

        self._owns_ppt_app = False
        self._ppt_app = win32com.client.DispatchEx("PowerPoint.Application")
        self._owns_ppt_app = True
        self._ppt_app.DisplayAlerts = _PP_ALERTS_NONE

        # 最小化 PowerPoint 编辑窗口
        self._ppt_app.WindowState = 2  # ppWindowMinimized

        # 打开演示文稿（只读）
        self._presentation = self._ppt_app.Presentations.Open(
            file_path,
            ReadOnly=True,
            Untitled=False,
            WithWindow=False,
        )
        self._mark_presentation_clean()
        self._total_slides = self._presentation.Slides.Count

        if autoplay:
            self._start_slideshow()

    def _start_slideshow(self, start_slide: int = 1) -> None:
        """
        启动幻灯片放映并嵌入到 PySide 播放器窗口中。
        :param start_slide: 起始页码
        """
        if self._presentation is None:
            return

        # 仅更新必要的页码范围，尽量减少对演示文稿持久化设置的改写。
        settings = self._presentation.SlideShowSettings
        settings.StartingSlide = max(1, min(start_slide, self._total_slides or 1))
        settings.EndingSlide = self._total_slides
        self._mark_presentation_clean()

        # 启动放映
        self._slideshow_window = settings.Run()
        self._mark_presentation_clean()
        self._slideshow_view = self._slideshow_window.View
        self._is_paused = False

        # 获取 PowerPoint 放映窗口的 HWND
        ppt_hwnd = find_slideshow_hwnd(self._slideshow_window, self._logger)
        if ppt_hwnd == 0:
            self._logger.warning("未找到 PowerPoint 放映窗口句柄，无法嵌入")
            return

        self._ppt_hwnd = ppt_hwnd
        embed_slideshow_window(ppt_hwnd, self._window_handle)
        container_width, container_height = resize_slideshow_window(ppt_hwnd, self._window_handle)
        self._logger.debug("PPT 窗口已调整大小：%dx%d", container_width, container_height)

        self._logger.info(
            "PPT 放映已启动并嵌入到播放器窗口（HWND=%d，共 %d 页）",
            ppt_hwnd, self._total_slides,
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
            self._set_powerpoint_alerts(_PP_ALERTS_NONE)
            # 先解除父窗口关系，避免 PowerPoint 关闭时影响 PySide 窗口
            if self._ppt_hwnd != 0:
                try:
                    detach_slideshow_window(self._ppt_hwnd)
                except Exception:
                    pass
                self._ppt_hwnd = 0

            if self._slideshow_view is not None:
                try:
                    self._mark_presentation_clean()
                    self._slideshow_view.Exit()
                except Exception:
                    pass
                self._slideshow_view = None
                self._slideshow_window = None

            if self._presentation is not None:
                try:
                    self._close_presentation_without_save()
                except Exception:
                    pass
                self._presentation = None

            if self._ppt_app is not None and self._owns_ppt_app:
                try:
                    self._ppt_app.Quit()
                except Exception:
                    pass
            self._set_powerpoint_alerts(_PP_ALERTS_ALL)
            self._ppt_app = None
            self._owns_ppt_app = False
        finally:
            try:
                pythoncom.CoUninitialize()
            except Exception:
                pass

        self._total_slides = 0
        self._is_paused = False

    def _set_powerpoint_alerts(self, alert_level: int) -> None:
        """
        设置 PowerPoint 提示级别，避免关闭只读文件时弹出保存对话框。
        :param alert_level: PowerPoint PpAlertLevel 常量值
        :return: None
        """
        if self._ppt_app is None:
            return
        try:
            self._ppt_app.DisplayAlerts = alert_level
        except Exception:
            pass

    def _mark_presentation_clean(self) -> None:
        """
        将演示文稿标记为已保存，关闭只读文件时不再触发保存提示。
        :return: None
        """
        if self._presentation is None:
            return
        try:
            self._presentation.Saved = True
        except Exception:
            pass

    def _close_presentation_without_save(self) -> None:
        """
        关闭演示文稿时显式选择不保存，避免 PowerPoint 弹出保存对话框。
        :return: None
        """
        if self._presentation is None:
            return
        self._mark_presentation_clean()
        close_method = getattr(self._presentation, "Close", None)
        if close_method is None:
            return
        try:
            close_method(False)
            return
        except TypeError:
            close_method()

    # ═══════════════════ 播放控制 ═══════════════════

    def play(self) -> None:
        """恢复放映（从暂停状态）。"""
        with self._com_lock:
            if self._slideshow_view is None and self._presentation is not None:
                self._start_slideshow(self._last_slide_index)
                return
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
                    self._last_slide_index = int(self._slideshow_view.CurrentShowPosition or self._last_slide_index)
                    self._mark_presentation_clean()
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
            if self._slideshow_view is None or self._slideshow_is_finished():
                return
            current_position = self._current_show_position()
            if self._total_slides > 0 and current_position >= self._total_slides:
                self._last_slide_index = self._total_slides
                self._logger.info("PPT 已在最后一页，忽略继续下一页指令")
                return
            try:
                self._slideshow_view.Next()
                self._last_slide_index = self._current_show_position()
            except Exception as nav_error:
                self._logger.warning("PPT 翻页（下一页）失败：%s", nav_error)

    def prev_item(self) -> None:
        """上一页。"""
        with self._com_lock:
            if self._slideshow_view is None or self._slideshow_is_finished():
                return
            current_position = self._current_show_position()
            if current_position <= 1:
                self._last_slide_index = 1
                return
            try:
                self._slideshow_view.Previous()
                self._last_slide_index = self._current_show_position()
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
            if self._slideshow_view is None or self._slideshow_is_finished():
                return
            try:
                self._slideshow_view.GotoSlide(index)
                self._last_slide_index = index
            except Exception as goto_error:
                self._logger.warning("PPT 跳转到第 %d 页失败：%s", index, goto_error)

    def _slideshow_is_finished(self) -> bool:
        """
        判断当前放映是否已经结束或 COM 视图已失效。
        :return: True 表示不应再向 PowerPoint 下发翻页指令
        """
        if self._slideshow_view is None:
            return True
        try:
            return int(self._slideshow_view.State) == _PP_SLIDE_SHOW_DONE
        except Exception:
            return self._read_current_show_position() is None

    def _current_show_position(self) -> int:
        """
        安全读取当前页码，失败时使用最近一次成功读取的页码。
        :return: 当前页码（从 1 开始）
        """
        current_position = self._read_current_show_position()
        if current_position is None:
            return self._last_slide_index
        self._last_slide_index = current_position
        return current_position

    def _read_current_show_position(self) -> Optional[int]:
        """
        读取当前页码，读取失败时返回 None 而不修改内部状态。
        :return: 当前页码；COM 视图不可读时返回 None
        """
        if self._slideshow_view is None:
            return None
        try:
            current_position = int(self._slideshow_view.CurrentShowPosition or 0)
        except Exception:
            return None
        return current_position if current_position > 0 else None

    def control_media(self, media_id: str, action: str, media_index: int = 0) -> None:
        """
        控制当前页中的音视频媒体对象。
        :param media_id: 媒体对象标识，可为 PowerPoint shape id
        :param action: 控制动作（play / pause / stop）
        :param media_index: 当前页媒体序号（从 1 开始）
        :return: None
        """
        normalized_action = action.strip().lower()
        if normalized_action not in {"play", "pause", "stop"}:
            self._logger.warning("未知 PPT 媒体控制动作：%s", action)
            return
        with self._com_lock:
            if self._slideshow_view is None:
                self._logger.warning("PPT 放映未运行，无法控制页面媒体")
                return
            player = self._resolve_media_player(media_id, media_index)
            if player is None:
                self._logger.warning("未找到 PPT 页面媒体：media_id=%s, index=%d", media_id, media_index)
                return
            try:
                getattr(player, normalized_action.capitalize())()
            except Exception as media_error:
                self._logger.warning("PPT 页面媒体 %s 执行 %s 失败：%s", media_id, action, media_error)

    def _resolve_media_player(self, media_id: str, media_index: int) -> Optional[object]:
        """
        根据 shape id 或当前页媒体序号获取 PowerPoint Player 对象。
        :param media_id: 媒体对象标识
        :param media_index: 媒体序号
        :return: PowerPoint Player COM 对象；找不到时返回 None
        """
        for shape_id in self._candidate_media_shape_ids(media_id, media_index):
            try:
                return self._slideshow_view.Player(shape_id)
            except Exception:
                continue
        return None

    def _candidate_media_shape_ids(self, media_id: str, media_index: int) -> list[int]:
        """
        生成可尝试的媒体 shape id 列表。
        :param media_id: 前端媒体对象标识
        :param media_index: 当前页媒体序号
        :return: shape id 列表
        """
        candidate_ids: list[int] = []
        try:
            parsed_media_id = int(media_id)
        except (TypeError, ValueError):
            parsed_media_id = 0
        if parsed_media_id > 0:
            candidate_ids.append(parsed_media_id)
        candidate_ids.extend(self._current_slide_media_shape_ids())
        if media_index > 0 and len(candidate_ids) >= media_index:
            return [candidate_ids[media_index - 1]] + candidate_ids
        return candidate_ids

    def _current_slide_media_shape_ids(self) -> list[int]:
        """
        枚举当前页可作为媒体控制目标的 shape id。
        :return: 当前页媒体 shape id 列表
        """
        if self._presentation is None or self._slideshow_view is None:
            return []
        try:
            current_slide = self._presentation.Slides(self._slideshow_view.CurrentShowPosition)
        except Exception:
            return []
        shape_ids: list[int] = []
        for shape_index in range(1, int(current_slide.Shapes.Count) + 1):
            shape = current_slide.Shapes(shape_index)
            try:
                _ = shape.MediaFormat
                shape_ids.append(int(shape.Id))
            except Exception:
                continue
        return shape_ids

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
                    slideshow_state = int(self._slideshow_view.State)
                    if slideshow_state == _PP_SLIDE_SHOW_DONE:
                        current_slide = self._last_slide_index or self._total_slides
                        playback_state = "stopped"
                    else:
                        current_slide = self._current_show_position()

                        if slideshow_state == _PP_SLIDE_SHOW_RUNNING:
                            playback_state = "playing"
                        elif slideshow_state == _PP_SLIDE_SHOW_PAUSED:
                            playback_state = "paused"
                        else:
                            playback_state = "playing"
                except Exception as state_error:
                    self._logger.debug("读取 PPT 放映状态失败：%s", state_error)
                    current_position = self._read_current_show_position()
                    if current_position is not None:
                        current_slide = current_position
                        self._last_slide_index = current_position
                        playback_state = "playing" if not self._is_paused else "paused"
                    else:
                        self._slideshow_view = None
                        self._slideshow_window = None
                        current_slide = self._last_slide_index if self._total_slides else 0
                        playback_state = "stopped" if self._presentation is not None else "idle"
            elif self._presentation is not None:
                # 文件已打开但未在放映
                playback_state = "stopped"
                current_slide = self._last_slide_index if self._total_slides else 0

        return AdapterState(
            playback_state=playback_state,
            current_slide=current_slide,
            total_slides=self._total_slides,
        )
