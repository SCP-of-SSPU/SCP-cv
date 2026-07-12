#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PowerPoint Broker Application 创建、所有权和退出生命周期。
@Project : SCP-cv
@File : powerpoint_application.py
@Author : Qintsg
@Date : 2026-07-11
'''
from __future__ import annotations

import logging
from collections.abc import Callable, Mapping

from scp_cv.player.adapters.ppt_constants import PP_ALERTS_NONE
from scp_cv.player.ppt_broker.com_support import (
    is_released_com_object_error,
    resolve_powerpoint_process_identity,
)

logger = logging.getLogger(__name__)


class PowerPointApplicationLifecycleMixin:
    """把 Application 创建、进程归属和安全退出收进一个内部深模块。"""

    _application: object | None
    _application_factory: Callable[[], object]
    _process_id_reader: Callable[[object], int]
    _process_snapshot: Callable[[], Mapping[int, float] | set[int] | None] | None
    _process_window_probe: Callable[[int], bool | None] | None
    _process_terminator: Callable[[int, float], bool] | None
    _ownership_requires_pid_delta: bool
    _configured_owns_application: bool
    _owns_application: bool
    _process_id: int
    _process_created_at: float
    _baseline_presentation_count: int
    _original_display_alerts: object
    _has_original_display_alerts: bool
    _application_sentinel: object | None

    def _run_operation(
        self,
        operation_name: str,
        callback: Callable[[], object],
    ) -> object:
        raise NotImplementedError

    def _ensure_application(self) -> object:
        """懒创建共享 Application，并只认领唯一新增的 PowerPoint 进程。"""
        if self._application is not None:
            return self._application
        existing_processes: Mapping[int, float] | set[int] | None = None
        if self._process_snapshot is not None:
            existing_processes = self._process_snapshot()
        application = self._run_operation(
            "创建 PowerPoint Application",
            self._application_factory,
        )
        self._application = application
        try:
            self._baseline_presentation_count = int(application.Presentations.Count)  # type: ignore[attr-defined]
        except Exception:
            self._baseline_presentation_count = 0
        current_processes = (
            self._process_snapshot()
            if self._process_snapshot is not None
            else None
        )
        self._process_id, self._process_created_at = (
            resolve_powerpoint_process_identity(
                self._process_id_reader(application),
                existing_processes,
                current_processes,
            )
        )
        if self._ownership_requires_pid_delta:
            self._owns_application = bool(
                self._configured_owns_application
                and existing_processes is not None
                and self._process_id > 0
                and self._process_id not in existing_processes
            )
        else:
            self._owns_application = self._configured_owns_application
        if self._owns_application:
            try:
                self._original_display_alerts = application.DisplayAlerts  # type: ignore[attr-defined]
                self._has_original_display_alerts = True
            except Exception:
                self._original_display_alerts = None
                self._has_original_display_alerts = False
            try:
                application.DisplayAlerts = PP_ALERTS_NONE  # type: ignore[attr-defined]
            except Exception:
                pass
        return application

    def _ensure_application_sentinel(self, application: object) -> None:
        """保留无窗口、无放映的空白 Presentation 以稳定重复 Run。"""
        if self._application_sentinel is not None:
            return

        def create_sentinel() -> object:
            presentations = application.Presentations  # type: ignore[attr-defined]
            try:
                return presentations.Add(WithWindow=False)
            except TypeError:
                return presentations.Add(False)

        sentinel = self._run_operation(
            "创建 PowerPoint Application sentinel",
            create_sentinel,
        )
        self._mark_presentation_clean(sentinel)
        self._application_sentinel = sentinel

    def _log_idle_application_counts(self) -> None:
        """记录最后会话关闭后的 Application 集合状态。"""
        application = self._application
        if application is None:
            return
        try:
            presentation_count: int | str = int(application.Presentations.Count)  # type: ignore[attr-defined]
        except Exception as count_error:
            presentation_count = f"error:{count_error}"
        try:
            slideshow_count: int | str = int(application.SlideShowWindows.Count)  # type: ignore[attr-defined]
        except Exception as count_error:
            slideshow_count = f"error:{count_error}"
        logger.info(
            "ppt_broker_idle powerpoint_pid=%d presentations=%s slideshows=%s",
            self._process_id,
            presentation_count,
            slideshow_count,
        )

    @staticmethod
    def _mark_presentation_clean(presentation: object) -> None:
        try:
            presentation.Saved = True  # type: ignore[attr-defined]
        except Exception:
            pass

    def _close_presentation(self, presentation: object) -> None:
        self._mark_presentation_clean(presentation)
        try:
            close = getattr(presentation, "Close", None)
        except Exception as lookup_error:
            if is_released_com_object_error(lookup_error):
                return
            raise
        if not callable(close):
            return

        def close_once() -> object:
            try:
                return close(False)
            except TypeError:
                return close()

        try:
            self._run_operation("关闭 PowerPoint Presentation", close_once)
        except Exception as close_error:
            if is_released_com_object_error(close_error):
                return
            raise

    def _shutdown_application(self) -> None:
        """仅在没有外部文档时退出自有 Application。"""
        application = self._application
        if application is not None:
            if self._has_original_display_alerts:
                try:
                    application.DisplayAlerts = self._original_display_alerts  # type: ignore[attr-defined]
                except Exception as restore_error:
                    logger.warning(
                        "恢复 PowerPoint DisplayAlerts 失败；"
                        "请检查是否有用户文档仍在使用该实例：%s",
                        restore_error,
                    )
            if self._owns_application and self._baseline_presentation_count == 0:
                try:
                    remaining = int(application.Presentations.Count)  # type: ignore[attr-defined]
                except Exception:
                    remaining = -1
                if remaining == 0:
                    quit_failed = False
                    try:
                        application.Quit()  # type: ignore[attr-defined]
                    except Exception as quit_error:
                        quit_failed = True
                        logger.warning("退出 Broker 自有 PowerPoint 失败：%s", quit_error)
                    if quit_failed:
                        self._force_terminate_owned_process()
        self._application = None
        self._process_id = 0
        self._process_created_at = 0.0
        self._owns_application = False
        self._original_display_alerts = None
        self._has_original_display_alerts = False

    def _force_terminate_owned_process(self) -> None:
        """在所有安全前提均可证明时清理 Quit 失败的自有进程。"""
        if (
            not self._owns_application
            or self._process_id <= 0
            or self._process_created_at <= 0
            or self._process_snapshot is None
            or self._process_window_probe is None
            or self._process_terminator is None
        ):
            logger.warning("PowerPoint 进程归属信息不完整，拒绝强制终止")
            return
        current_processes = self._process_snapshot()
        current_created_at = (
            float(current_processes.get(self._process_id, 0.0) or 0.0)
            if isinstance(current_processes, Mapping)
            else 0.0
        )
        if current_created_at != self._process_created_at:
            logger.warning(
                "PowerPoint PID/创建时间不再匹配，拒绝强制终止："
                "pid=%d, expected=%.6f, actual=%.6f",
                self._process_id,
                self._process_created_at,
                current_created_at,
            )
            return
        has_windows = self._process_window_probe(self._process_id)
        if has_windows is not False:
            logger.warning(
                "PowerPoint PID=%d 仍有窗口或窗口状态无法确认，拒绝强制终止",
                self._process_id,
            )
            return
        if self._process_terminator(self._process_id, self._process_created_at):
            logger.info(
                "已精确清理 Broker 自有 PowerPoint 进程：pid=%d, created_at=%.6f",
                self._process_id,
                self._process_created_at,
            )


__all__ = ["PowerPointApplicationLifecycleMixin"]
