#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PowerPoint 适配器打开流程，负责文件校验、COM 初始化和放映窗口嵌入。
@Project : SCP-cv
@File : ppt_opening.py
@Author : Qintsg
@Date : 2026-08-23
'''
from __future__ import annotations

import functools
from collections.abc import Callable
from typing import Optional

from scp_cv.player.adapters.ppt_constants import PP_ALERTS_NONE
from scp_cv.player.adapters.ppt_focus import (
    conceal_ppt_editor_window,
    restore_player_foreground,
)
from scp_cv.player.adapters.ppt_process import (
    record_spawned_ppt_process,
)
from scp_cv.player.adapters.ppt_window import (
    configure_windowed_slideshow,
)

_SLIDESHOW_HWND_TIMEOUT_SECONDS = 8.0
_SLIDESHOW_HWND_POLL_INTERVAL_SECONDS = 0.05
_SYNC_OPEN_WAIT_TIMEOUT_SECONDS = 90.0
_POWERPOINT_SLOT_WAIT_TIMEOUT_SECONDS = 0.0


class PptOpeningMixin:
    """封装 PowerPoint 文件打开及放映窗口嵌入生命周期。"""

    def open(self, uri: str, window_handle: int, autoplay: bool = True) -> None:
        """
        同步打开 PowerPoint 文件并启动幻灯片放映。

        :param uri: PowerPoint 文件绝对路径
        :param window_handle: PySide 窗口原生句柄
        :param autoplay: 是否立即开始放映
        :return: None
        """
        self._validate_ppt_file(uri)
        self._file_path = uri
        self._window_handle = window_handle
        worker = self._com_worker
        if worker is not None and not getattr(worker, "is_current_thread", False):
            worker.submit_and_wait(
                f"{self._app_label} 打开 {uri}",
                functools.partial(self._open_on_com_thread, uri, autoplay, 1),
                timeout_seconds=_SYNC_OPEN_WAIT_TIMEOUT_SECONDS,
            )
            return
        self._open_on_com_thread(uri, autoplay, 1)

    def open_async(
        self,
        uri: str,
        window_handle: int,
        autoplay: bool = True,
        start_slide: int = 0,
        on_finished: Optional[Callable[[Optional[BaseException]], None]] = None,
    ) -> None:
        """
        异步打开 PowerPoint 文件，完成后通过回调通知结果。

        :param uri: PowerPoint 文件绝对路径
        :param window_handle: PySide 窗口原生句柄
        :param autoplay: 是否立即开始放映
        :param start_slide: 起始页码；0 表示第 1 页
        :param on_finished: 完成回调，参数为异常或 None
        :return: None
        """
        try:
            self._validate_ppt_file(uri)
        except Exception as validation_error:
            if on_finished is not None:
                on_finished(validation_error)
                return
            raise
        self._file_path = uri
        self._window_handle = window_handle
        open_job = functools.partial(
            self._open_on_com_thread, uri, autoplay, max(1, start_slide or 1)
        )
        worker = self._com_worker
        if worker is None or getattr(worker, "is_current_thread", False):
            open_error: Optional[BaseException] = None
            try:
                open_job()
            except BaseException as inline_error:
                open_error = inline_error
            if on_finished is not None:
                on_finished(open_error)
            elif open_error is not None:
                raise open_error
            return

        def report_completion(_result: object, error: Optional[BaseException]) -> None:
            """
            转发 COM 工作线程的完成结果。

            :param _result: 未使用的任务结果
            :param error: 任务异常或 None
            :return: None
            """
            if on_finished is not None:
                on_finished(error)

        worker.submit(f"{self._app_label} 打开 {uri}", open_job, on_done=report_completion)

    @staticmethod
    def _validate_ppt_file(uri: str) -> None:
        """
        校验 PowerPoint 文件存在性。

        :param uri: PowerPoint 文件路径
        :return: None
        :raises FileNotFoundError: 文件不存在时
        """
        from scp_cv.player.adapters import ppt as ppt_module

        if not ppt_module.os.path.isfile(uri):
            raise FileNotFoundError(f"PPT 文件不存在：{uri}")

    def _open_on_com_thread(self, uri: str, autoplay: bool, start_slide: int) -> None:
        """
        在 COM 线程执行完整打开流程并刷新状态缓存。

        :param uri: PowerPoint 文件路径
        :param autoplay: 是否自动放映
        :param start_slide: 起始页码
        :return: None
        """
        self._powerpoint_slot.acquire(_POWERPOINT_SLOT_WAIT_TIMEOUT_SECONDS)
        try:
            with self._com_lock:
                self._init_com_and_open(uri, autoplay, start_slide)
            self._mark_open()
            self._refresh_cached_state()
            self._logger.info("PPT 已打开：%s（%d 页）", uri, self._total_slides)
        except BaseException:
            with self._com_lock:
                try:
                    self._close_com_resources()
                finally:
                    self._powerpoint_slot.release()
            raise

    def _init_com_and_open(
        self,
        file_path: str,
        autoplay: bool,
        start_slide: int = 1,
    ) -> None:
        """
        初始化 COM 环境并打开 PowerPoint 文件。

        :param file_path: PowerPoint 文件路径
        :param autoplay: 是否自动开始放映
        :param start_slide: 起始页码
        :return: None
        """
        import pythoncom
        import win32com.client

        pythoncom.CoInitialize()
        self._owns_ppt_app = False
        from scp_cv.player.adapters import ppt as ppt_module

        existing_process_ids = ppt_module.snapshot_candidate_process_ids_for_prog_ids(
            self._com_prog_ids, self._active_com_prog_id
        )
        self._preheated_app = self._take_preheated_application()
        if self._preheated_app is not None:
            self._ppt_app = self._preheated_app.app
            self._active_com_prog_id = self._preheated_app.prog_id
            try:
                self._ppt_app.Presentations
            except Exception as stale_error:
                self._logger.warning(
                    "预热 %s COM 应用已失效，重新创建：%s",
                    self._app_label,
                    stale_error,
                )
                self._preheated_app = None
                self._ppt_app = None
            else:
                self._logger.info(
                    "已复用预热 %s COM 应用：%s",
                    self._app_label,
                    self._active_com_prog_id,
                )
        if self._ppt_app is None:
            self._ppt_app = self._dispatch_ppt_application(win32com.client)
            self._owns_ppt_app = True
        self._ppt_process_id = ppt_module.read_ppt_app_process_id(
            self._ppt_app, self._active_com_prog_id, existing_process_ids
        )
        self._set_powerpoint_alerts(PP_ALERTS_NONE)
        self._spawned_ppt_process = (
            self._ppt_process_id != 0
            and self._ppt_process_id not in existing_process_ids
        )
        if self._spawned_ppt_process:
            record_spawned_ppt_process(self._ppt_process_id)
        preheated_spawned = bool(
            self._preheated_app is not None
            and getattr(self._preheated_app, "spawned_process", False)
        )
        if self._spawned_ppt_process or preheated_spawned:
            conceal_ppt_editor_window(self._ppt_app, self._logger)
        self._presentation = self._take_preheated_presentation(file_path)
        if self._presentation is None:
            self._presentation = self._open_presentation_for_slideshow(file_path)
        self._mark_presentation_clean()
        self._total_slides = self._presentation.Slides.Count
        if autoplay:
            self._start_slideshow(start_slide)

    def _start_slideshow(self, start_slide: int = 1) -> None:
        """
        启动幻灯片放映并嵌入 PySide 播放器容器。

        :param start_slide: 起始页码
        :return: None
        """
        if self._presentation is None:
            return
        from scp_cv.player.adapters import ppt as ppt_module

        settings = configure_windowed_slideshow(
            self._presentation.SlideShowSettings, start_slide, self._total_slides
        )
        self._mark_presentation_clean()
        existing_hwnds = ppt_module.snapshot_slideshow_hwnds(
            self._logger,
            class_names=self._slideshow_class_names,
            process_id=self._ppt_process_id or None,
        )
        slideshow_window = self._run_powerpoint_operation(
            "启动幻灯片放映", settings.Run
        )
        self._mark_presentation_clean()
        if slideshow_window is None:
            raise RuntimeError(f"{self._app_label} SlideShowSettings.Run 未返回放映窗口")
        slideshow_view = slideshow_window.View
        ppt_hwnd = ppt_module.find_slideshow_hwnd(
            slideshow_window,
            self._logger,
            existing_hwnds,
            class_names=self._slideshow_class_names,
            timeout_seconds=_SLIDESHOW_HWND_TIMEOUT_SECONDS,
            poll_interval_seconds=_SLIDESHOW_HWND_POLL_INTERVAL_SECONDS,
            process_id=self._ppt_process_id or None,
            allow_existing_when_unique=not existing_hwnds,
        )
        if ppt_hwnd == 0:
            raise RuntimeError(f"未找到 {self._app_label} 放映窗口句柄，无法嵌入播放器容器")
        container_width, container_height = ppt_module.embed_slideshow_window(
            ppt_hwnd, self._window_handle, self._embed_owner_token
        )
        restore_player_foreground(
            self._window_handle, self._ppt_process_id, self._logger
        )
        self._slideshow_window = slideshow_window
        self._slideshow_view = slideshow_view
        self._ppt_hwnd = ppt_hwnd
        self._is_paused = False
        self._logger.debug(
            "%s 放映窗口已嵌入 PySide 容器：%dx%d",
            self._app_label,
            container_width,
            container_height,
        )
        self._logger.info(
            "%s 放映已嵌入播放器窗口（HWND=%d，共 %d 页）",
            self._app_label,
            ppt_hwnd,
            self._total_slides,
        )
