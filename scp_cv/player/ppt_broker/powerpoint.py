#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PowerPoint Broker 的 Microsoft PowerPoint COM 后端 Adapter。
@Project : SCP-cv
@File : powerpoint.py
@Author : Qintsg
@Date : 2026-07-11
'''
from __future__ import annotations

import logging
from collections.abc import Callable, Iterable, Mapping
from pathlib import Path
from typing import cast

from scp_cv.player.adapters.ppt_constants import (
    PP_SLIDE_SHOW_DONE,
    PP_SLIDE_SHOW_PAUSED,
    PP_SLIDE_SHOW_RUNNING,
    PP_SLIDE_SHOW_WINDOW,
)
from scp_cv.player.adapters.ppt_media import control_slide_media
from scp_cv.player.ppt_broker.com_support import (
    dispatch_powerpoint,
    is_released_com_object_error,
    owner_token,
    process_has_top_level_windows,
    read_powerpoint_process_id,
    snapshot_powerpoint_processes,
    terminate_powerpoint_process,
)
from scp_cv.player.ppt_broker.contracts import (
    PptCommand,
    PptCommandRequest,
    PptExportResult,
    PptOpenRequest,
    PptPreheatRequest,
    PptShowExportRequest,
    PptSlideExportRequest,
    PptState,
)
from scp_cv.player.ppt_broker.powerpoint_exports import (
    export_show as export_show_task,
    export_slides as export_slides_task,
)
from scp_cv.player.ppt_broker.powerpoint_application import (
    PowerPointApplicationLifecycleMixin,
)
from scp_cv.player.ppt_broker.powerpoint_navigation import (
    goto_slide,
    next_slide,
    previous_slide,
)
from scp_cv.player.ppt_broker.powerpoint_operations import (
    PowerPointOperationRunnerMixin,
)
from scp_cv.player.ppt_broker.powerpoint_session import (
    PowerPointComSession,
    preheat_key,
    presentation_window_name,
)
from scp_cv.player.ppt_broker.windows import (
    SlideshowWindowPort,
    SystemWindowPort,
)

logger = logging.getLogger(__name__)


def _is_file(path: str) -> bool:
    """使用 pathlib 检查 PowerPoint 源文件。"""
    return Path(path).is_file()


class PowerPointComBackend(
    PowerPointOperationRunnerMixin,
    PowerPointApplicationLifecycleMixin,
):
    """在一个 Application 内管理全部窗口化 PowerPoint 放映。"""

    requires_com = True

    def __init__(
        self,
        *,
        application_factory: Callable[[], object] | None = None,
        process_id_reader: Callable[[object], int] | None = None,
        process_snapshot: Callable[
            [], Mapping[int, float] | set[int] | None
        ] | None = None,
        process_window_probe: Callable[[int], bool | None] | None = None,
        process_terminator: Callable[[int, float], bool] | None = None,
        window_port: SlideshowWindowPort | None = None,
        file_exists: Callable[[str], bool] | None = None,
        retry_delays: Iterable[float] = (0.15, 0.35, 0.8),
        owns_application: bool = True,
    ) -> None:
        self._application_factory = application_factory or dispatch_powerpoint
        self._process_id_reader = process_id_reader or read_powerpoint_process_id
        self._process_snapshot = process_snapshot
        if self._process_snapshot is None and application_factory is None:
            self._process_snapshot = snapshot_powerpoint_processes
        self._process_window_probe = process_window_probe
        if self._process_window_probe is None and application_factory is None:
            self._process_window_probe = process_has_top_level_windows
        self._process_terminator = process_terminator
        if self._process_terminator is None and application_factory is None:
            self._process_terminator = terminate_powerpoint_process
        self._ownership_requires_pid_delta = self._process_snapshot is not None
        self._window_port = window_port or SystemWindowPort()
        self._file_exists = file_exists or _is_file
        self._retry_delays = tuple(max(0.0, delay) for delay in retry_delays)
        self._configured_owns_application = owns_application
        self._owns_application = False
        self._application: object | None = None
        self._process_id = 0
        self._process_created_at = 0.0
        self._baseline_presentation_count = 0
        self._original_display_alerts: object = None
        self._has_original_display_alerts = False
        self._sessions: dict[int, PowerPointComSession] = {}
        self._application_sentinel: object | None = None
        self._preheated: dict[tuple[int, str], object] = {}

    @property
    def powerpoint_pid(self) -> int:
        """返回当前共享 PowerPoint Application 的 PID，未启动时为 0。"""
        return self._process_id

    def open(self, request: PptOpenRequest) -> object:
        """打开独立的 untitled Presentation 副本并按需启动放映。"""
        if not self._file_exists(request.uri):
            raise FileNotFoundError(f"PPT 文件不存在：{request.uri}")
        application = self._ensure_application()
        cached_key = preheat_key(request.source_id, request.uri)
        presentation = self._preheated.pop(cached_key, None)
        if presentation is None:
            presentation = self._open_presentation(application, request.uri)
        try:
            total_slides = int(presentation.Slides.Count)  # type: ignore[attr-defined]
            session = PowerPointComSession(
                request=request,
                presentation=presentation,
                total_slides=total_slides,
                owner_token=owner_token(request.session.owner_token),
                current_slide=min(request.start_slide, max(1, total_slides)),
            )
            if request.autoplay:
                self._start_slideshow(session, session.current_slide)
            self._sessions[id(session)] = session
            logger.info(
                "PPT Broker 已打开会话：request_id=%s, window_id=%d, source_id=%d, "
                "pid=%d, hwnd=%d",
                request.request_id,
                request.session.window_id,
                request.source_id,
                self._process_id,
                session.hwnd,
            )
            return session
        except BaseException:
            self._close_presentation(presentation)
            raise

    def command(self, handle: object, request: PptCommandRequest) -> None:
        """执行单个 PowerPoint 放映指令。"""
        session = self._session(handle)
        command = request.command
        if command is PptCommand.PLAY:
            if session.view is None:
                self._start_slideshow(session, session.current_slide)
            else:
                self._run_operation(
                    "继续 PowerPoint 放映",
                    lambda: setattr(
                        session.view,
                        "State",
                        PP_SLIDE_SHOW_RUNNING,
                    ),
                )
                session.playback_state = "playing"
        elif command is PptCommand.PAUSE:
            if session.view is not None:
                self._run_operation(
                    "暂停 PowerPoint 放映",
                    lambda: setattr(
                        session.view,
                        "State",
                        PP_SLIDE_SHOW_PAUSED,
                    ),
                )
                session.playback_state = "paused"
        elif command is PptCommand.STOP:
            self._stop_slideshow(session)
        elif command is PptCommand.NEXT:
            self._run_operation("PowerPoint 下一动画或下一页", lambda: next_slide(session))
        elif command is PptCommand.PREVIOUS:
            self._run_operation(
                "PowerPoint 上一动画或上一页",
                lambda: previous_slide(session),
            )
        elif command is PptCommand.GOTO:
            self._run_operation(
                "跳转 PowerPoint 页码",
                lambda: goto_slide(session, request.slide_index),
            )
        elif command is PptCommand.RESIZE:
            if session.hwnd:
                self._window_port.resize(
                    session.hwnd,
                    session.request.parent_hwnd,
                )
        elif command is PptCommand.CONTROL_MEDIA:
            self._run_operation(
                "控制 PowerPoint 页面媒体",
                lambda: control_slide_media(
                    session.view,
                    session.presentation,
                    logger,
                    request.media_id,
                    request.media_action,
                    request.media_index,
                ),
            )

    def get_state(self, handle: object) -> PptState:
        """读取会话状态；COM 视图失效时向调用方暴露错误。"""
        session = self._session(handle)
        if session.view is not None:
            def read_state() -> tuple[int, int]:
                return (
                    int(session.view.State),  # type: ignore[attr-defined]
                    int(
                        session.view.CurrentShowPosition  # type: ignore[attr-defined]
                        or session.current_slide
                    ),
                )

            state, current_slide = cast(
                tuple[int, int],
                self._run_operation("读取 PowerPoint 放映状态", read_state),
            )
            session.current_slide = current_slide
            if state == PP_SLIDE_SHOW_DONE:
                session.playback_state = "stopped"
            elif state == PP_SLIDE_SHOW_PAUSED:
                session.playback_state = "paused"
            else:
                session.playback_state = "playing"
        return PptState(
            playback_state=session.playback_state,
            current_slide=session.current_slide,
            total_slides=session.total_slides,
            powerpoint_pid=self._process_id,
            slideshow_hwnd=session.hwnd,
            parent_hwnd=session.request.parent_hwnd,
        )

    def hide(self, handle: object) -> None:
        """在事务式切源期间隐藏旧会话。"""
        session = self._session(handle)
        if session.hwnd:
            self._window_port.hide(session.hwnd)

    def show(self, handle: object) -> None:
        """新会话打开失败时恢复旧会话。"""
        session = self._session(handle)
        if session.hwnd:
            self._window_port.show(session.hwnd, session.request.parent_hwnd)

    def close(self, handle: object) -> None:
        """幂等关闭单个放映和 Presentation，不退出共享 Application。"""
        session = self._session(handle)
        if len(self._sessions) == 1 and id(session) in self._sessions:
            application = self._application
            if application is None:
                raise RuntimeError("PowerPoint Application 已失效，无法创建关闭 sentinel")
            self._ensure_application_sentinel(application)
        self._close_session_resources(session)
        self._sessions.pop(id(session), None)
        if not self._sessions:
            self._log_idle_application_counts()

    def preheat(self, request: PptPreheatRequest) -> None:
        """共享 Application；文件级预热按 source_id 与路径去重。"""
        application = self._ensure_application()
        if not request.uri:
            return
        if not self._file_exists(request.uri):
            raise FileNotFoundError(f"PPT 文件不存在：{request.uri}")
        key = preheat_key(request.source_id, request.uri)
        if key in self._preheated:
            return
        presentation = self._open_presentation(application, request.uri)
        self._preheated[key] = presentation

    def export_show(self, request: PptShowExportRequest) -> PptExportResult:
        """用共享 Application 把独立任务 Presentation 导出为放映文件。"""
        return export_show_task(self, request)

    def export_slides(self, request: PptSlideExportRequest) -> PptExportResult:
        """用共享 Application 把独立任务 Presentation 逐页导出为 PNG。"""
        return export_slides_task(self, request)

    def shutdown(self) -> None:
        """释放 Broker 自有资源，仅在确认无外部文档时退出 Application。"""
        for session in list(self._sessions.values()):
            try:
                self.close(session)
            except Exception as close_error:
                logger.warning("关闭 PowerPoint Broker 会话失败：%s", close_error)
        for presentation in list(self._preheated.values()):
            self._close_presentation(presentation)
        self._preheated.clear()
        sentinel = self._application_sentinel
        self._application_sentinel = None
        if sentinel is not None:
            self._close_presentation(sentinel)
        self._shutdown_application()

    def _open_presentation(
        self,
        application: object,
        uri: str,
        *,
        read_only: bool = False,
    ) -> object:
        def open_once() -> object:
            presentations = application.Presentations  # type: ignore[attr-defined]
            try:
                return presentations.Open(
                    uri,
                    ReadOnly=read_only,
                    Untitled=True,
                    WithWindow=False,
                )
            except TypeError:
                return presentations.Open(uri, read_only, True, False)

        return self._run_operation("打开 PowerPoint Presentation", open_once)

    def _start_slideshow(self, session: PowerPointComSession, start_slide: int) -> None:
        if self._process_id <= 0:
            raise RuntimeError(
                "无法确定 PowerPoint 进程 ID，拒绝认领可能属于其它进程的放映窗口；"
                "请确认 PowerPoint 已在当前交互桌面启动，并检查 pywin32。"
            )
        settings = session.presentation.SlideShowSettings  # type: ignore[attr-defined]
        settings.ShowType = PP_SLIDE_SHOW_WINDOW
        settings.StartingSlide = max(1, min(start_slide, session.total_slides or 1))
        settings.EndingSlide = session.total_slides
        try:
            settings.ShowPresenterView = False
        except Exception:
            pass
        before = self._window_port.snapshot(self._process_id)
        slideshow_window = self._run_operation("启动 PowerPoint 放映", settings.Run)
        if slideshow_window is None:
            raise RuntimeError("PowerPoint SlideShowSettings.Run 未返回放映窗口")
        session.slideshow_window = slideshow_window
        session.view = slideshow_window.View  # type: ignore[attr-defined]
        if settings.StartingSlide > 1:
            self._run_operation(
                "定位 PowerPoint 初始页",
                lambda: goto_slide(session, settings.StartingSlide),
            )
        forbidden_hwnds = [
            active.hwnd
            for active in self._sessions.values()
            if active.hwnd
        ]
        hwnd = self._window_port.resolve(
            slideshow_window,
            before,
            self._process_id,
            forbidden_hwnds,
            expected_presentation_name=presentation_window_name(
                session.presentation, session.request.uri
            ),
        )
        self._window_port.embed(
            hwnd,
            session.request.parent_hwnd,
            session.owner_token,
        )
        session.hwnd = hwnd
        session.playback_state = "playing"

    def _stop_slideshow(self, session: PowerPointComSession) -> None:
        if session.view is not None:
            try:
                session.current_slide = int(
                    session.view.CurrentShowPosition or session.current_slide  # type: ignore[attr-defined]
                )
            except Exception:
                pass
            if session.hwnd:
                prepare_close = getattr(self._window_port, "prepare_close", None)
                if callable(prepare_close):
                    prepare_close(session.hwnd, session.owner_token)
            try:
                self._run_operation(
                    "退出 PowerPoint 放映",
                    session.view.Exit,  # type: ignore[attr-defined]
                )
            except Exception as exit_error:
                if not is_released_com_object_error(exit_error):
                    raise
        if session.hwnd:
            self._window_port.close(session.hwnd, session.owner_token)
        session.slideshow_window = None
        session.view = None
        session.hwnd = 0
        session.playback_state = "stopped"

    def _close_session_resources(self, session: PowerPointComSession) -> None:
        """释放一个 COM 会话的放映窗口和 Presentation。"""
        self._stop_slideshow(session)
        presentation = session.presentation
        self._close_presentation(presentation)
        session.presentation = None
        del presentation

    @staticmethod
    def _session(handle: object) -> PowerPointComSession:
        if not isinstance(handle, PowerPointComSession):
            raise TypeError("无效的 PowerPoint Broker COM 会话")
        return handle

__all__ = ["PowerPointComBackend"]
