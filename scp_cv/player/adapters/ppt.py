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

import os as os
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
from scp_cv.player.adapters.ppt_navigation import PptNavigationMixin
from scp_cv.player.adapters.ppt_window import (
    close_embedded_slideshow_window,
    embed_slideshow_window as embed_slideshow_window,
    find_slideshow_hwnd as find_slideshow_hwnd,
    hide_embedded_slideshow_window,
    show_embedded_slideshow_window,
    snapshot_slideshow_hwnds as snapshot_slideshow_hwnds,
)
from scp_cv.player.adapters.ppt_opening import (
    PptOpeningMixin,
    _SLIDESHOW_HWND_POLL_INTERVAL_SECONDS as _SLIDESHOW_HWND_POLL_INTERVAL_SECONDS,
    _SLIDESHOW_HWND_TIMEOUT_SECONDS as _SLIDESHOW_HWND_TIMEOUT_SECONDS,
)
from scp_cv.player.adapters.ppt_process import (
    read_ppt_app_process_id as read_ppt_app_process_id,
    snapshot_candidate_process_ids_for_prog_ids as snapshot_candidate_process_ids_for_prog_ids,
)
from scp_cv.player.powerpoint_slot import PowerPointSlot
from scp_cv.player.adapters.ppt_preheat import PptPreheatMixin
from scp_cv.player.preheat_types import PreheatedPptApplication
from scp_cv.ppt_com import POWERPOINT_COM_PROG_IDS

_SYNC_CLOSE_WAIT_TIMEOUT_SECONDS = 30.0


class PptSourceAdapter(
    PptOpeningMixin,
    PptNavigationMixin,
    PptComSessionMixin,
    PptPreheatMixin,
    SourceAdapter,
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
        powerpoint_slot: PowerPointSlot | None = None,
    ) -> None:
        """
        初始化 PowerPoint 放映适配器。

        :param adapter_name: 适配器注册名称
        :param app_label: 日志和错误信息中的应用名称
        :param com_prog_ids: 可尝试连接的 PowerPoint COM ProgID
        :param slideshow_class_names: 可接受的放映窗口类名集合
        :param powerpoint_slot: 跨进程 PowerPoint 独占槽位；为空时创建默认槽位
        :return: None
        """
        super().__init__(adapter_name=adapter_name)
        self._app_label = app_label
        self._com_prog_ids = tuple(com_prog_ids or POWERPOINT_COM_PROG_IDS)
        self._slideshow_class_names = (
            frozenset(slideshow_class_names) if slideshow_class_names else None
        )
        self._powerpoint_slot = powerpoint_slot or PowerPointSlot()
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

    # ═══════════════════ 关闭 ═══════════════════

    def close(self) -> None:
        """关闭 PPT 放映并释放 COM 资源；worker 模式下清理在后台执行。"""
        self._mark_closed()
        self._submit_com_command("关闭", self._close_on_com_thread)

    def close_and_wait(self) -> None:
        """
        完整关闭 PPT 放映并等待 COM 资源释放完成。
        PowerPoint 唯一槽位切换前必须调用，确保旧放映完全退出后再打开新放映。
        :return: None
        """
        self._mark_closed()
        worker = self._com_worker
        if worker is None or getattr(worker, "is_current_thread", False):
            self._close_on_com_thread()
            return
        worker.submit_and_wait(
            f"{self._app_label} 完整关闭",
            self._close_on_com_thread,
            timeout_seconds=_SYNC_CLOSE_WAIT_TIMEOUT_SECONDS,
        )
        self._mark_closed()

    def _close_on_com_thread(self) -> None:
        """
        在 COM 线程执行资源释放。
        :return: None
        """
        with self._com_lock:
            try:
                self._close_com_resources()
            finally:
                self._powerpoint_slot.release()
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
                    # PowerPoint 是进程级 COM 服务器。放映退出后，原 Application
                    # 代理可能被 Office 一并断开；把它放回预热池会让下一次打开拿到
                    # “对象没有连接到服务器”的失效代理。借出的系统预热实例若由本
                    # 系统拉起则退出进程，否则只退休当前代理，避免影响用户文档。
                    if bool(getattr(self._preheated_app, "spawned_process", False)):
                        self._quit_ppt_application_if_idle()
                elif self._owns_ppt_app:
                    # 适配器自建的 Application 同样不得跨放映复用。下一次打开会
                    # DispatchEx 一个新代理；空闲预热由控制器在离场后另行重建。
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
