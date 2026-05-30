#!/user/bin/env python
# -*- coding: UTF-8 -*-
"""
PPT 源适配器，通过本机 COM 自动化控制幻灯片放映。
在指定屏幕上以放映模式展示 PPT/PPTX/PPSX 文件。
@Project : SCP-cv
@File : ppt.py
@Author : Qintsg
@Date : 2026-04-15
"""

from __future__ import annotations

import os
import threading
from collections.abc import Iterable
from typing import Optional

from scp_cv.player.adapters.base import AdapterState, SourceAdapter
from scp_cv.player.adapters.ppt_constants import (
    PP_ALERTS_ALL as _PP_ALERTS_ALL,
    PP_ALERTS_NONE as _PP_ALERTS_NONE,
    PP_SLIDE_SHOW_DONE as _PP_SLIDE_SHOW_DONE,
    PP_SLIDE_SHOW_PAUSED as _PP_SLIDE_SHOW_PAUSED,
    PP_SLIDE_SHOW_RUNNING as _PP_SLIDE_SHOW_RUNNING,
)
from scp_cv.player.adapters.ppt_media import control_slide_media
from scp_cv.player.adapters.ppt_external_window import (
    present_external_slideshow_window,
    release_external_slideshow_window,
)
from scp_cv.player.adapters.ppt_window import (
    configure_windowed_slideshow,
    find_slideshow_hwnd,
    snapshot_slideshow_hwnds,
)
from scp_cv.player.adapters.ppt_process import (
    read_ppt_app_process_id,
    snapshot_candidate_process_ids,
)
from scp_cv.player.preheat_types import PreheatedPptApplication
from scp_cv.ppt_com import POWERPOINT_COM_PROG_IDS

_SLIDESHOW_HWND_TIMEOUT_SECONDS = 12.0


class PptSourceAdapter(SourceAdapter):
    """
    本机 PPT COM 放映适配器。

    通过 win32com 操控 PowerPoint/WPS 演示应用程序，在指定屏幕上进行幻灯片放映。
    PPT 窗口定位到 PySide 播放器窗口所在的屏幕区域。

    线程安全说明：
    - COM 操作必须在创建 COM 对象的同一线程中执行
    - 使用 pythoncom.CoInitialize/CoUninitialize 管理 COM 线程
    """

    def __init__(
        self,
        adapter_name: str = "ppt",
        app_label: str = "PowerPoint",
        com_prog_ids: Optional[Iterable[str]] = None,
        slideshow_class_names: Optional[Iterable[str]] = None,
    ) -> None:
        super().__init__(adapter_name=adapter_name)
        self._app_label = app_label
        self._com_prog_ids = tuple(com_prog_ids or POWERPOINT_COM_PROG_IDS)
        self._slideshow_class_names = (
            frozenset(slideshow_class_names) if slideshow_class_names else None
        )
        self._active_com_prog_id = ""
        self._ppt_app: Optional[object] = None  # PPT 应用 COM 对象
        self._presentation: Optional[object] = None  # Presentation 对象
        self._slideshow_view: Optional[object] = None  # SlideShowView 对象
        self._slideshow_window: Optional[object] = None  # SlideShowWindow 对象
        self._total_slides: int = 0
        self._file_path: str = ""
        self._window_handle: int = 0
        self._ppt_hwnd: int = 0
        self._ppt_process_id: int = 0
        self._is_paused: bool = False
        self._last_slide_index: int = 1
        self._owns_ppt_app: bool = False
        self._preheated_app: PreheatedPptApplication | None = None
        self._preheat_enabled: bool = False
        self._preheat_pool: object | None = None
        # COM 线程锁（所有 COM 调用须串行）
        self._com_lock = threading.Lock()

    @property
    def has_external_slideshow_window(self) -> bool:
        """
        当前是否存在已铺满目标区域的外部 PPT 放映窗口。
        :return: True 表示外部放映窗口正在承担显示输出
        """
        return self._ppt_hwnd != 0

    def set_preheat_context(self, source_id: int, preheat_enabled: bool, preheat_pool: object | None) -> None:
        """
        注入 PPT 应用预热上下文。
        :param source_id: 媒体源 ID，COM 应用预热按后端共享，当前仅保留接口一致性
        :param preheat_enabled: 是否启用预热复用
        :param preheat_pool: 统一预热池
        :return: None
        """
        self._preheat_enabled = preheat_enabled
        self._preheat_pool = preheat_pool

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
        existing_process_ids = snapshot_candidate_process_ids(self._active_com_prog_id)
        self._preheated_app = self._take_preheated_application()
        if self._preheated_app is not None:
            self._ppt_app = self._preheated_app.app
            self._active_com_prog_id = self._preheated_app.prog_id
            self._logger.info("已复用预热 %s COM 应用：%s", self._app_label, self._active_com_prog_id)
        else:
            self._ppt_app = self._dispatch_ppt_application(win32com.client)
            self._owns_ppt_app = True
        self._ppt_process_id = read_ppt_app_process_id(
            self._ppt_app,
            self._active_com_prog_id,
            existing_process_ids,
        )
        self._set_powerpoint_alerts(_PP_ALERTS_NONE)

        # 最小化编辑窗口；WPS 部分版本可能不支持该属性，失败时不影响放映。
        try:
            self._ppt_app.WindowState = 2  # ppWindowMinimized
        except Exception as minimize_error:
            self._logger.debug("%s 编辑窗口最小化失败：%s", self._app_label, minimize_error)

        self._presentation = self._open_presentation_for_slideshow(file_path)
        self._mark_presentation_clean()
        self._total_slides = self._presentation.Slides.Count

        if autoplay:
            self._start_slideshow()

    def _dispatch_ppt_application(self, win32com_client: object) -> object:
        """
        按候选 ProgID 创建 PPT COM 应用实例。
        :param win32com_client: win32com.client 模块对象
        :return: PPT 应用 COM 对象
        :raises RuntimeError: 所有 ProgID 均不可用时
        """
        last_error: Optional[Exception] = None
        for prog_id in self._com_prog_ids:
            try:
                app = win32com_client.DispatchEx(prog_id)
                self._active_com_prog_id = prog_id
                self._logger.info("已创建 %s COM 应用：%s", self._app_label, prog_id)
                return app
            except Exception as dispatch_error:
                last_error = dispatch_error
                self._logger.debug(
                    "%s COM ProgID 不可用：%s，原因：%s",
                    self._app_label,
                    prog_id,
                    dispatch_error,
                )
        supported_prog_ids = ", ".join(self._com_prog_ids)
        raise RuntimeError(
            f"未找到 {self._app_label} COM 自动化对象：{supported_prog_ids}"
        ) from last_error

    def _open_presentation_for_slideshow(self, file_path: str) -> object:
        """
        以可配置放映设置但不显示编辑窗口的方式打开演示文稿副本。
        :param file_path: PPT 文件路径
        :return: Presentation COM 对象
        """
        if self._ppt_app is None:
            raise RuntimeError(f"{self._app_label} COM 应用尚未初始化")
        presentations = self._ppt_app.Presentations
        try:
            return presentations.Open(
                file_path,
                ReadOnly=False,
                Untitled=True,
                WithWindow=False,
            )
        except Exception as keyword_error:
            try:
                return presentations.Open(file_path, False, True, False)
            except Exception:
                raise keyword_error

    def _start_slideshow(self, start_slide: int = 1) -> None:
        """
        启动幻灯片放映并将外部放映窗口铺满目标显示区域。
        :param start_slide: 起始页码
        """
        if self._presentation is None:
            return

        # 仅更新必要的页码范围，尽量减少对演示文稿持久化设置的改写。
        settings = configure_windowed_slideshow(
            self._presentation.SlideShowSettings,
            start_slide,
            self._total_slides,
        )
        self._mark_presentation_clean()

        # COM 无法直接给出 HWND 时，Win32 回退只能接受本次 Run 后新增的窗口。
        existing_hwnds = snapshot_slideshow_hwnds(
            self._logger,
            class_names=self._slideshow_class_names,
            process_id=self._ppt_process_id or None,
        )

        # 启动放映
        self._slideshow_window = settings.Run()
        self._mark_presentation_clean()
        self._slideshow_view = self._slideshow_window.View
        self._is_paused = False

        # 获取 PPT 放映窗口的 HWND
        ppt_hwnd = find_slideshow_hwnd(
            self._slideshow_window,
            self._logger,
            existing_hwnds,
            class_names=self._slideshow_class_names,
            timeout_seconds=_SLIDESHOW_HWND_TIMEOUT_SECONDS,
            process_id=self._ppt_process_id or None,
            allow_existing_when_unique=True,
        )
        if ppt_hwnd == 0:
            self._logger.warning("未找到 %s 放映窗口句柄，无法铺满目标显示区域", self._app_label)
            return

        container_width, container_height = present_external_slideshow_window(
            ppt_hwnd, self._window_handle
        )
        self._ppt_hwnd = ppt_hwnd
        self._logger.debug(
            "%s 外部放映窗口已铺满目标区域：%dx%d",
            self._app_label,
            container_width,
            container_height,
        )

        self._logger.info(
            "%s 放映已启动为外部顶层窗口（HWND=%d，共 %d 页）",
            self._app_label,
            ppt_hwnd,
            self._total_slides,
        )

    def close(self) -> None:
        """关闭 PPT 放映并释放 COM 资源。"""
        with self._com_lock:
            self._close_com_resources()
        self._mark_closed()
        self._logger.info("PPT 已关闭")

    def _close_com_resources(self) -> None:
        """释放所有 COM 资源，并解除 PPT 外部窗口置顶。"""
        import pythoncom

        try:
            self._set_powerpoint_alerts(_PP_ALERTS_NONE)
            # 先释放外部窗口置顶关系，避免 PPT 应用关闭时影响其它窗口层级。
            if self._ppt_hwnd != 0:
                try:
                    release_external_slideshow_window(self._ppt_hwnd)
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

            self._set_powerpoint_alerts(_PP_ALERTS_ALL)
            if self._ppt_app is not None:
                if self._preheated_app is not None:
                    self._return_preheated_application()
                elif self._owns_ppt_app:
                    try:
                        self._ppt_app.Quit()
                    except Exception:
                        pass
            self._ppt_app = None
            self._owns_ppt_app = False
            self._ppt_process_id = 0
            self._preheated_app = None
        finally:
            try:
                pythoncom.CoUninitialize()
            except Exception:
                pass

        self._total_slides = 0
        self._is_paused = False

    def _take_preheated_application(self) -> PreheatedPptApplication | None:
        """
        从统一预热池取出已启动的 PowerPoint/WPS 应用。
        :return: 预热应用或 None
        """
        if not self._preheat_enabled or self._preheat_pool is None:
            return None
        take_application = getattr(self._preheat_pool, "take_ppt_application", None)
        if not callable(take_application):
            return None
        backend = "wps" if self._adapter_name == "ppt-wps" else "powerpoint"
        return take_application(backend)

    def _return_preheated_application(self) -> bool:
        """
        将借出的 PowerPoint/WPS 应用归还预热池。
        :return: True 表示已归还
        """
        if self._preheated_app is None or self._preheat_pool is None:
            return False
        return_application = getattr(self._preheat_pool, "return_ppt_application", None)
        if not callable(return_application):
            return False
        return_application(self._preheated_app)
        return True

    def _set_powerpoint_alerts(self, alert_level: int) -> None:
        """
        设置 PPT 应用提示级别，避免关闭只读文件时弹出保存对话框。
        :param alert_level: PowerPoint/WPS 兼容的 PpAlertLevel 常量值
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
                    self._last_slide_index = int(
                        self._slideshow_view.CurrentShowPosition
                        or self._last_slide_index
                    )
                    self._mark_presentation_clean()
                    if self._ppt_hwnd != 0:
                        try:
                            release_external_slideshow_window(self._ppt_hwnd)
                        except Exception:
                            pass
                        self._ppt_hwnd = 0
                    self._slideshow_view.Exit()
                except Exception:
                    pass
                self._slideshow_view = None
                self._slideshow_window = None
                self._is_paused = False

    # ═══════════════════ 幻灯片导航 ═══════════════════

    def next_item(self) -> None:
        """下一动画或下一页。"""
        with self._com_lock:
            if self._slideshow_view is None or self._slideshow_is_finished():
                return
            try:
                self._goto_next_click()
                self._last_slide_index = self._current_show_position()
            except Exception as nav_error:
                self._logger.warning("PPT 下一动画/页失败：%s", nav_error)

    def prev_item(self) -> None:
        """上一动画或上一页。"""
        with self._com_lock:
            if self._slideshow_view is None or self._slideshow_is_finished():
                return
            try:
                self._goto_previous_click()
                self._last_slide_index = self._current_show_position()
            except Exception as nav_error:
                self._logger.warning("PPT 上一动画/页失败：%s", nav_error)

    def _goto_next_click(self) -> None:
        """
        优先推进到下一动画点击，接口不可用时回退到下一页。
        :return: None
        """
        if self._slideshow_view is None:
            return
        current_position = self._current_show_position()
        goto_next_click = getattr(self._slideshow_view, "GotoNextClick", None)
        if callable(goto_next_click):
            has_next_click = self._has_remaining_next_click()
            if has_next_click is not False:
                try:
                    goto_next_click()
                    return
                except Exception as click_error:
                    self._logger.debug("PPT 下一动画接口不可用，回退到下一页：%s", click_error)
        if self._total_slides > 0 and current_position >= self._total_slides:
            self._last_slide_index = self._total_slides
            self._logger.info("PPT 已在最后一页，忽略继续下一页指令")
            return
        self._slideshow_view.Next()

    def _goto_previous_click(self) -> None:
        """
        优先回退到上一动画点击，接口不可用时回退到上一页。
        :return: None
        """
        if self._slideshow_view is None:
            return
        current_position = self._current_show_position()
        goto_previous_click = getattr(self._slideshow_view, "GotoPreClick", None)
        if callable(goto_previous_click):
            has_previous_click = self._has_previous_click()
            if has_previous_click is not False:
                try:
                    goto_previous_click()
                    return
                except Exception as click_error:
                    self._logger.debug("PPT 上一动画接口不可用，回退到上一页：%s", click_error)
        if current_position <= 1:
            self._last_slide_index = 1
            return
        self._slideshow_view.Previous()

    def _has_remaining_next_click(self) -> Optional[bool]:
        """
        判断当前页是否仍有可推进的动画点击。
        :return: True/False 表示已确认；None 表示后端不支持读取
        """
        click_count = self._read_slideshow_click_value("GetClickCount")
        click_index = self._read_slideshow_click_value("GetClickIndex")
        if click_count is None or click_index is None:
            return None
        return click_index < click_count

    def _has_previous_click(self) -> Optional[bool]:
        """
        判断当前页是否有可回退的动画点击。
        :return: True/False 表示已确认；None 表示后端不支持读取
        """
        click_index = self._read_slideshow_click_value("GetClickIndex")
        if click_index is None:
            return None
        return click_index > 0

    def _read_slideshow_click_value(self, method_name: str) -> Optional[int]:
        """
        读取 SlideShowView 的动画点击计数。
        :param method_name: COM 方法名
        :return: 计数值；不可读取时返回 None
        """
        if self._slideshow_view is None:
            return None
        method = getattr(self._slideshow_view, method_name, None)
        if not callable(method):
            return None
        try:
            return int(method())
        except Exception:
            return None

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
                self._goto_slide(index)
                self._last_slide_index = index
            except Exception as goto_error:
                self._logger.warning("PPT 跳转到第 %d 页失败：%s", index, goto_error)

    def _goto_slide(self, index: int) -> None:
        """
        跳转到指定页，兼容 WPS/PowerPoint 可能不同的 COM 参数签名。
        :param index: 目标页码，1-based
        :return: None
        """
        if self._slideshow_view is None:
            return
        try:
            self._slideshow_view.GotoSlide(index)
        except TypeError:
            self._slideshow_view.GotoSlide(index, False)

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
        with self._com_lock:
            control_slide_media(
                self._slideshow_view,
                self._presentation,
                self._logger,
                media_id,
                action,
                media_index,
            )

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
                        current_slide = (
                            self._last_slide_index if self._total_slides else 0
                        )
                        playback_state = (
                            "stopped" if self._presentation is not None else "idle"
                        )
            elif self._presentation is not None:
                # 文件已打开但未在放映
                playback_state = "stopped"
                current_slide = self._last_slide_index if self._total_slides else 0

        return AdapterState(
            playback_state=playback_state,
            current_slide=current_slide,
            total_slides=self._total_slides,
        )
