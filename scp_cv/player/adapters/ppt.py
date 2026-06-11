#!/user/bin/env python
# -*- coding: UTF-8 -*-
"""
PPT 源适配器，通过本机 COM 自动化控制幻灯片放映。
在指定屏幕上以放映模式展示 PPT/PPTX/PPSX 文件。
注入 COM 工作线程后，所有 PowerPoint COM 调用都在该线程串行执行，
打开/关闭等慢操作不再阻塞 Qt 主线程；状态查询走缓存即时返回。
@Project : SCP-cv
@File : ppt.py
@Author : Qintsg
@Date : 2026-04-15
"""

from __future__ import annotations

import functools
import os
import threading
from collections.abc import Callable
from collections.abc import Iterable
from typing import Optional

from scp_cv.player.adapters.base import AdapterState, SourceAdapter
from scp_cv.player.adapters.ppt_com_session import PptComSessionMixin
from scp_cv.player.adapters.ppt_constants import (
    PP_ALERTS_ALL as _PP_ALERTS_ALL,
    PP_ALERTS_NONE as _PP_ALERTS_NONE,
)
from scp_cv.player.adapters.ppt_focus import (
    conceal_ppt_editor_window,
    restore_player_foreground,
)
from scp_cv.player.adapters.ppt_navigation import PptNavigationMixin
from scp_cv.player.adapters.ppt_window import (
    close_embedded_slideshow_window,
    configure_windowed_slideshow,
    embed_slideshow_window,
    find_slideshow_hwnd,
    hide_embedded_slideshow_window,
    show_embedded_slideshow_window,
    snapshot_slideshow_hwnds,
)
from scp_cv.player.adapters.ppt_process import (
    read_ppt_app_process_id,
    record_spawned_ppt_process,
    snapshot_candidate_process_ids_for_prog_ids,
)
from scp_cv.player.adapters.ppt_preheat import PptPreheatMixin
from scp_cv.player.preheat_types import PreheatedPptApplication
from scp_cv.ppt_com import POWERPOINT_COM_PROG_IDS

_SLIDESHOW_HWND_TIMEOUT_SECONDS = 12.0
_SLIDESHOW_HWND_POLL_INTERVAL_SECONDS = 0.05
_SYNC_OPEN_WAIT_TIMEOUT_SECONDS = 90.0


class PptSourceAdapter(
    PptNavigationMixin, PptComSessionMixin, PptPreheatMixin, SourceAdapter
):
    """
    本机 PPT COM 放映适配器。

    通过 win32com 操控 PowerPoint 应用程序，在指定屏幕上进行幻灯片放映。
    PPT 窗口定位到 PySide 播放器窗口所在的屏幕区域。

    线程模型：
    - 注入 PptComWorker 后，COM 对象统一创建并运行在该 STA 线程；
      open_async 后台执行，导航指令后台投递，get_state 返回缓存快照。
    - 未注入 worker 时（单元测试）所有方法内联同步执行，行为与历史一致。
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
        self._spawned_ppt_process: bool = False
        self._source_id: int = 0
        self._is_paused: bool = False
        self._last_slide_index: int = 1
        self._owns_ppt_app: bool = False
        self._preheated_app: PreheatedPptApplication | None = None
        self._preheat_enabled: bool = False
        self._preheat_pool: object | None = None
        # COM 线程锁（所有 COM 调用须串行）
        self._com_lock = threading.Lock()
        # COM 工作线程；未注入时内联执行
        self._com_worker: object | None = None
        # 嵌入窗口归属 token，防止旧适配器误关被复用的放映窗口
        self._embed_owner_token: int = (id(self) & 0x7FFFFFFF) or 1
        # 状态缓存：worker 模式下 get_state 即时返回缓存
        self._state_cache_lock = threading.Lock()
        self._cached_state = AdapterState()
        self._state_refresh_pending = False

    def set_preheat_context(self, source_id: int, preheat_enabled: bool, preheat_pool: object | None) -> None:
        """
        注入 PPT 应用预热上下文。
        :param source_id: 媒体源 ID，COM 应用预热按后端共享，当前仅保留接口一致性
        :param preheat_enabled: 是否启用预热复用
        :param preheat_pool: 统一预热池
        :return: None
        """
        self._source_id = source_id
        self._preheat_enabled = preheat_enabled
        self._preheat_pool = preheat_pool

    def set_com_worker(self, com_worker: object | None) -> None:
        """
        注入共享 PPT COM 工作线程。
        :param com_worker: PptComWorker 实例；None 表示内联执行
        :return: None
        """
        self._com_worker = com_worker

    def _submit_com_command(self, description: str, command: Callable[[], None]) -> None:
        """
        将 COM 操作投递到工作线程；未注入 worker 时内联执行。
        :param description: 操作描述，用于日志
        :param command: 待执行操作
        :return: None
        """
        worker = self._com_worker
        if worker is None or getattr(worker, "is_current_thread", False):
            command()
            return
        worker.submit(f"{self._app_label} {description}", command)

    # ═══════════════════ 打开 ═══════════════════

    def open(self, uri: str, window_handle: int, autoplay: bool = True) -> None:
        """
        同步打开 PPT 文件并启动幻灯片放映。
        放映窗口定位到 window_handle 所在屏幕。
        :param uri: PPT 文件绝对路径
        :param window_handle: PySide 窗口原生句柄（用于定位屏幕）
        :param autoplay: 是否立即开始放映
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
        异步打开 PPT 文件，完成后通过回调通知结果。
        注入 worker 时本方法立即返回，COM 慢操作在工作线程执行；
        未注入 worker 时内联同步执行并同步回调。
        :param uri: PPT 文件绝对路径
        :param window_handle: PySide 窗口原生句柄
        :param autoplay: 是否立即开始放映
        :param start_slide: 起始页码；0 表示从第 1 页开始
        :param on_finished: 完成回调，参数为 None（成功）或异常对象
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
            if on_finished is not None:
                on_finished(error)

        worker.submit(
            f"{self._app_label} 打开 {uri}",
            open_job,
            on_done=report_completion,
        )

    @staticmethod
    def _validate_ppt_file(uri: str) -> None:
        """
        校验 PPT 文件存在性，让明显错误在调用线程立即失败。
        :param uri: PPT 文件路径
        :raises FileNotFoundError: 文件不存在时
        """
        if not os.path.isfile(uri):
            raise FileNotFoundError(f"PPT 文件不存在：{uri}")

    def _open_on_com_thread(self, uri: str, autoplay: bool, start_slide: int) -> None:
        """
        在 COM 线程执行完整打开流程并刷新状态缓存。
        :param uri: PPT 文件路径
        :param autoplay: 是否自动放映
        :param start_slide: 起始页码（1-based）
        :return: None
        """
        with self._com_lock:
            self._init_com_and_open(uri, autoplay, start_slide)
        self._mark_open()
        self._refresh_cached_state()
        self._logger.info("PPT 已打开：%s（%d 页）", uri, self._total_slides)

    def _init_com_and_open(self, file_path: str, autoplay: bool, start_slide: int = 1) -> None:
        """
        初始化 COM 环境并打开 PPT 文件。
        :param file_path: PPT 文件路径
        :param autoplay: 是否自动开始放映
        :param start_slide: 起始页码（1-based）
        """
        import pythoncom
        import win32com.client

        pythoncom.CoInitialize()

        self._owns_ppt_app = False
        existing_process_ids = snapshot_candidate_process_ids_for_prog_ids(
            self._com_prog_ids,
            self._active_com_prog_id,
        )
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

        # 仅隐藏本系统拉起的编辑窗口，避免任务栏残留按钮；不打扰用户已有窗口。
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

        slideshow_window = self._run_powerpoint_operation(
            "启动幻灯片放映",
            settings.Run,
        )
        self._mark_presentation_clean()
        if slideshow_window is None:
            raise RuntimeError(f"{self._app_label} SlideShowSettings.Run 未返回放映窗口")
        slideshow_view = slideshow_window.View

        # 获取 PPT 放映窗口的 HWND
        ppt_hwnd = find_slideshow_hwnd(
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
            raise RuntimeError(
                f"未找到 {self._app_label} 放映窗口句柄，无法嵌入播放器容器"
            )

        container_width, container_height = embed_slideshow_window(
            ppt_hwnd, self._window_handle, self._embed_owner_token
        )
        # Run() 抢前台会让全屏播放窗口被任务栏盖住，嵌入完成后立即夺回。
        restore_player_foreground(self._window_handle, self._ppt_process_id, self._logger)
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

    # ═══════════════════ 关闭 ═══════════════════

    def close(self) -> None:
        """关闭 PPT 放映并释放 COM 资源；worker 模式下清理在后台执行。"""
        self._mark_closed()
        self._submit_com_command("关闭", self._close_on_com_thread)

    def _close_on_com_thread(self) -> None:
        """
        在 COM 线程执行资源释放。
        :return: None
        """
        with self._com_lock:
            self._close_com_resources()
        # close 任务可能排在在途 open 任务之后执行（取消场景），
        # open 末尾的 _mark_open 会翻转状态，这里复位为最终关闭态。
        self._mark_closed()
        self._logger.info("PPT 已关闭")

    def _close_com_resources(self) -> None:
        """释放所有 COM 资源，并关闭嵌入式 PPT 放映子窗口。"""
        import pythoncom

        try:
            self._set_powerpoint_alerts(_PP_ALERTS_NONE)
            if self._slideshow_view is not None:
                try:
                    self._mark_presentation_clean()
                    self._slideshow_view.Exit()
                except Exception:
                    pass
                self._slideshow_view = None
                self._slideshow_window = None

            if self._ppt_hwnd != 0:
                try:
                    close_embedded_slideshow_window(
                        self._ppt_hwnd, self._embed_owner_token
                    )
                except Exception:
                    pass
                self._ppt_hwnd = 0

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
                    if not self._return_owned_application_to_preheat_pool():
                        self._quit_ppt_application_if_idle()
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

    def _return_owned_application_to_preheat_pool(self) -> bool:
        """
        将当前适配器创建的空闲 PowerPoint 应用移交给预热池，减少切源时退出 Office 的卡顿。
        :return: True 表示已移交，调用方不应再 Quit 该应用
        """
        if (
            not self._preheat_enabled
            or self._preheat_pool is None
            or self._ppt_app is None
        ):
            return False
        return_application = getattr(self._preheat_pool, "return_ppt_application", None)
        if not callable(return_application):
            return False
        if self._spawned_ppt_process:
            conceal_ppt_editor_window(self._ppt_app, self._logger)
        return_application(
            PreheatedPptApplication(
                "powerpoint",
                self._ppt_app,
                self._active_com_prog_id,
                process_id=self._ppt_process_id,
                spawned_process=self._spawned_ppt_process,
            )
        )
        self._owns_ppt_app = False
        return True

    # ═══════════════════ 快速切源 ═══════════════════

    def detach_for_fast_switch(self) -> None:
        """
        切换到其它内容前立即隐藏嵌入式 PPT 子窗口，避免旧画面阻塞新内容显示。
        纯 Win32 操作，可在任意线程调用。
        :return: None
        """
        if self._ppt_hwnd == 0:
            return
        try:
            hide_embedded_slideshow_window(self._ppt_hwnd)
        except Exception:
            pass

    def restore_after_failed_switch(self) -> None:
        """
        新源打开失败后恢复已隐藏的嵌入式 PPT 子窗口。
        :return: None
        """
        if self._ppt_hwnd == 0:
            return
        try:
            show_embedded_slideshow_window(self._ppt_hwnd, self._window_handle)
        except Exception:
            pass

    # ═══════════════════ 状态获取 ═══════════════════

    def get_state(self) -> AdapterState:
        """
        获取 PPT 放映状态。
        worker 模式下返回缓存快照并在后台调度刷新，避免 COM 调用阻塞调用线程。
        :return: 包含当前页码和总页数的状态快照
        """
        worker = self._com_worker
        if worker is None or getattr(worker, "is_current_thread", False):
            return self._refresh_cached_state()
        self._schedule_state_refresh()
        with self._state_cache_lock:
            return self._cached_state

    def _refresh_cached_state(self) -> AdapterState:
        """
        通过 COM 采集状态并更新缓存（须在 COM 线程调用）。
        :return: 最新状态快照
        """
        adapter_state = self._collect_state_via_com()
        with self._state_cache_lock:
            self._cached_state = adapter_state
        return adapter_state

    def _schedule_state_refresh(self) -> None:
        """
        投递一次后台状态刷新；已有刷新在途时跳过。
        :return: None
        """
        if not self._is_open or self._com_worker is None:
            return
        with self._state_cache_lock:
            if self._state_refresh_pending:
                return
            self._state_refresh_pending = True
        self._com_worker.submit(
            f"{self._app_label} 刷新状态", self._refresh_state_job
        )

    def _refresh_state_job(self) -> None:
        """
        后台状态刷新任务。
        :return: None
        """
        try:
            if self._is_open:
                self._refresh_cached_state()
        finally:
            with self._state_cache_lock:
                self._state_refresh_pending = False

