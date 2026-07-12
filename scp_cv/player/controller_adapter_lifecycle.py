#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
播放器控制器适配器生命周期 mixin。
集中维护关闭、重置、切源恢复、临时源清理与预热重建流程。
@Project : SCP-cv
@File : controller_adapter_lifecycle.py
@Author : Qintsg
@Date : 2026-07-12
'''
from __future__ import annotations

import logging

from PySide6.QtCore import QTimer

logger = logging.getLogger(__name__)
_PPT_REHEAT_DELAY_MS = 1500
_PPT_DETACHED_CLOSE_DELAY_MS = 450


class PlayerAdapterLifecycleMixin:
    """
    PlayerController 的适配器生命周期实现。

    该 mixin 依赖最终 PlayerController 组合提供的适配器映射、窗口、
    PPT 打开管理及命令分发接口。
    """

    def _handle_close(self, window_id: int, command_args: dict[str, object]) -> None:
        """处理 CLOSE 指令：关闭适配器并重置会话。"""
        from scp_cv.services.playback import RESET_ALL_WINDOWS_ARG

        if bool(command_args.get(RESET_ALL_WINDOWS_ARG)):
            self._handle_reset_all_windows()
            return

        self._close_adapter(window_id)
        self._cleanup_temporary_source(command_args)

        window = self.get_window(window_id)
        if window is not None:
            window.show_black_screen()
            window.show()
            self._set_player_window_topmost(window, True)
            window.raise_()

        from scp_cv.apps.playback.models import PlaybackState, PlaybackSession
        session = PlaybackSession.objects.filter(window_id=window_id).first()
        if session is not None:
            if session.playback_state != PlaybackState.IDLE:
                logger.debug(
                    "窗口 %d CLOSE 已被更新的播放状态 %s 覆盖，跳过清空会话源",
                    window_id,
                    session.playback_state,
                )
                return
            session.media_source = None
            session.playback_state = PlaybackState.IDLE
            session.error_message = ""
            session.current_slide = 0
            session.total_slides = 0
            session.position_ms = 0
            session.duration_ms = 0
            session.save()

    def _handle_reset_all_windows(self) -> None:
        """
        处理全局重置：关闭全部播放资源、替换窗口并重新建立媒体预热池。
        :return: None
        """
        self._abort_pending_ppt_opens()
        close_errors = self._close_adapters_for_reset(
            list(self._adapters.keys())
        )
        self._adapter_source_types.clear()
        self._adapter_source_ids.clear()
        self._last_reported_states.clear()

        if self._preheat_pool is not None:
            self._preheat_pool.close_all()
            self._preheat_pool = None

        for registered_window_id in self.registered_window_ids:
            self._reset_window_session_to_idle(registered_window_id)

        self.rebuild_registered_windows()
        self.preheat_sources()
        self._raise_reset_close_errors(close_errors)
        logger.info("播放器已完成全部窗口重置和媒体预热重建")

    def _close_adapters_for_reset(
        self,
        window_ids: list[int],
    ) -> list[tuple[int, Exception]]:
        """尽力关闭重置范围内的所有适配器，并收集真实释放失败。"""
        close_errors: list[tuple[int, Exception]] = []
        for adapter_window_id in window_ids:
            try:
                self._close_adapter(adapter_window_id, reheat=False)
            except Exception as close_error:
                logger.warning(
                    "重置时关闭窗口 %d 适配器失败：%s",
                    adapter_window_id,
                    close_error,
                )
                close_errors.append((adapter_window_id, close_error))
        return close_errors

    @staticmethod
    def _raise_reset_close_errors(
        close_errors: list[tuple[int, Exception]],
    ) -> None:
        """在其余重置清理完成后，把关闭失败交给命令确认层。"""
        if not close_errors:
            return
        details = "; ".join(
            f"窗口 {window_id}: {close_error}"
            for window_id, close_error in close_errors
        )
        raise RuntimeError(f"重置关闭适配器失败：{details}") from close_errors[0][1]

    @staticmethod
    def _reset_window_session_to_idle(window_id: int) -> None:
        """
        将播放器侧确认过的窗口会话字段保持为空闲状态。
        :param window_id: 窗口编号
        :return: None
        """
        from scp_cv.apps.playback.models import PlaybackState, PlaybackSession

        session = PlaybackSession.objects.filter(window_id=window_id).first()
        if session is None:
            return
        session.media_source = None
        session.playback_state = PlaybackState.IDLE
        session.error_message = ""
        session.current_slide = 0
        session.total_slides = 0
        session.position_ms = 0
        session.duration_ms = 0
        session.save(update_fields=[
            "media_source",
            "playback_state",
            "error_message",
            "current_slide",
            "total_slides",
            "position_ms",
            "duration_ms",
            "last_updated_at",
        ])

    @staticmethod
    def _cleanup_temporary_source(command_args: dict[str, object]) -> None:
        """
        清理已切离的临时源。
        :param command_args: 指令参数，包含 cleanup_source_id 时触发
        """
        cleanup_source_id = command_args.get("cleanup_source_id")
        if not cleanup_source_id:
            return
        from scp_cv.services.media import MediaError, delete_temporary_source_if_unused
        try:
            delete_temporary_source_if_unused(int(cleanup_source_id))
        except (ValueError, MediaError) as cleanup_error:
            logger.warning("清理临时源失败：%s", cleanup_error)

    def _handle_reset_ppt(self, window_id: int, command_args: dict[str, object]) -> None:
        """
        处理全局 PPT 放映重置：关闭所有 PPT 放映窗口并按原页码重开。
        :param window_id: 协调窗口编号
        :param command_args: 包含 restart_sessions 的参数字典
        :return: None
        """
        restart_sessions = command_args.get("restart_sessions", [])
        close_errors = self._close_adapters_for_reset(
            [
                adapter_window_id
                for adapter_window_id, source_type in self._adapter_source_types.items()
                if source_type == "ppt"
            ]
        )

        if not isinstance(restart_sessions, list):
            logger.warning("窗口 %d：RESET_PPT 参数 restart_sessions 不是列表", window_id)
            self._raise_reset_close_errors(close_errors)
            return
        from scp_cv.apps.playback.models import PlaybackCommand

        for raw_restart in restart_sessions:
            if not isinstance(raw_restart, dict):
                continue
            restart_window_id = int(raw_restart.get("window_id") or 0)
            if restart_window_id not in self.registered_window_ids:
                continue
            # 统一走指令入口：目标窗口存在在途 PPT 打开时自动排队取代，避免 pending 记录被覆盖
            self._execute_command_on_main_thread(
                restart_window_id, PlaybackCommand.OPEN, dict(raw_restart)
            )
        self._raise_reset_close_errors(close_errors)
        logger.info("播放器已完成 PPT 放映重置，重启窗口数=%d", len(restart_sessions))

    def _close_adapter(self, window_id: int, restore_window: bool = True, reheat: bool = True) -> None:
        """
        关闭并释放指定窗口的适配器。
        :param window_id: 窗口编号
        :param restore_window: PPT 关闭后是否恢复 PySide 黑屏窗口
        :param reheat: 关闭后是否按源配置重新预热
        """
        adapter = self._adapters.pop(window_id, None)
        source_type = self._adapter_source_types.get(window_id)
        source_id = self._adapter_source_ids.get(window_id)
        try:
            self._close_detached_adapter(
                window_id,
                adapter,
                source_type,
                source_id,
                restore_window,
                reheat,
            )
        finally:
            self._adapter_source_types.pop(window_id, None)
            self._adapter_source_ids.pop(window_id, None)
            self._last_reported_states.pop(window_id, None)

    def _close_detached_adapter(
        self,
        window_id: int,
        adapter: object | None,
        source_type: str | None,
        source_id: int | None,
        restore_window: bool,
        reheat: bool,
    ) -> None:
        """
        关闭已从当前窗口映射中摘除的适配器。
        :param window_id: 窗口编号
        :param adapter: 待关闭适配器
        :param source_type: 适配器源类型
        :param source_id: 适配器源 ID
        :param restore_window: 是否恢复 PySide 黑屏窗口
        :param reheat: 是否按源配置重新预热
        :return: None
        """
        if adapter is not None:
            adapter.close()
        if reheat and source_id and self._should_reheat_closed_source(window_id, int(source_id)):
            if source_type == "ppt":
                self._schedule_reheat_source_if_enabled(window_id, int(source_id))
            else:
                self._reheat_source_if_enabled(int(source_id))

    @staticmethod
    def _should_reheat_closed_source(window_id: int, source_id: int) -> bool:
        """
        判断关闭某源后是否应立即重建后台预热。
        :param window_id: 窗口编号
        :param source_id: 刚关闭的媒体源 ID
        :return: True 表示可以重建预热
        """
        from scp_cv.apps.playback.models import PlaybackSession, PlaybackState

        session = PlaybackSession.objects.filter(window_id=window_id).only(
            "media_source_id",
            "playback_state",
        ).first()
        if session is None:
            return True
        if session.media_source_id == source_id and session.playback_state != PlaybackState.IDLE:
            logger.debug(
                "窗口 %d 源 %d 当前仍处于 %s，跳过关闭后的即时预热",
                window_id,
                source_id,
                session.playback_state,
            )
            return False
        return True

    def _restore_previous_adapter(
        self,
        window_id: int,
        adapter: object | None,
        source_type: str | None,
        source_id: int | None,
    ) -> None:
        """
        新源打开失败时恢复旧适配器映射和窗口可见性。
        :param window_id: 窗口编号
        :param adapter: 旧适配器
        :param source_type: 旧源类型
        :param source_id: 旧源 ID
        :return: None
        """
        if adapter is None or source_type is None:
            return
        self._adapters[window_id] = adapter
        self._adapter_source_types[window_id] = source_type
        if source_id is not None:
            self._adapter_source_ids[window_id] = source_id
        window = self.get_window(window_id)
        if window is None:
            return
        if source_type == "ppt":
            self._restore_ppt_after_failed_switch(adapter)
            self._show_ppt_container(window_id)
        elif source_type == "web":
            window.show()
            window.raise_()
            window.show_web_container()
        else:
            window.show()
            window.raise_()
            window.show_video_container()

    def _schedule_reheat_source_if_enabled(self, window_id: int, source_id: int) -> None:
        """
        延迟重建 PPT 预热，避免 CLOSE 后立即重开时抢占主线程和 PowerPoint 资源。
        :param window_id: 窗口编号
        :param source_id: 刚关闭的媒体源 ID
        :return: None
        """
        QTimer.singleShot(
            _PPT_REHEAT_DELAY_MS,
            lambda: self._reheat_source_if_still_idle(window_id, source_id),
        )

    def _reheat_source_if_still_idle(self, window_id: int, source_id: int) -> None:
        """
        延迟回调执行前再次检查会话，确认没有同源前台打开后再预热。
        :param window_id: 窗口编号
        :param source_id: 待预热媒体源 ID
        :return: None
        """
        if self._should_reheat_closed_source(window_id, source_id):
            self._reheat_source_if_enabled(source_id)

    def _schedule_close_detached_adapter(
        self,
        window_id: int,
        adapter: object | None,
        source_type: str | None,
        source_id: int | None,
        restore_window: bool,
        reheat: bool,
    ) -> None:
        """
        将旧适配器关闭延后到当前 UI 切换完成后，PPT 额外留出新内容首帧绘制时间。
        :param window_id: 窗口编号
        :param adapter: 已从当前窗口映射中摘除的旧适配器
        :param source_type: 旧适配器源类型
        :param source_id: 旧适配器源 ID
        :param restore_window: 是否恢复 PySide 黑屏窗口
        :param reheat: 是否按源配置重新预热
        :return: None
        """
        delay_ms = (
            _PPT_DETACHED_CLOSE_DELAY_MS
            if source_type == "ppt"
            else 0
        )

        def close_after_switch() -> None:
            try:
                self._close_detached_adapter(
                    window_id,
                    adapter,
                    source_type,
                    source_id,
                    restore_window,
                    reheat,
                )
            except Exception as close_error:
                logger.warning(
                    "窗口 %d 切源后释放旧适配器失败：%s",
                    window_id,
                    close_error,
                )

        QTimer.singleShot(delay_ms, close_after_switch)

    def _prepare_adapter_preheat_context(
        self,
        adapter: object,
        source_id: int,
        source_type: str,
        preheat_enabled: bool,
        uri: str,
        window: object | None,
    ) -> None:
        """
        为适配器注入统一预热上下文。
        :param adapter: 新建适配器
        :param source_id: 媒体源 ID
        :param source_type: 媒体源类型
        :param preheat_enabled: 是否启用预热
        :param uri: 媒体 URI
        :param window: 播放窗口
        :return: None
        """
        preheat_pool = self._ensure_preheat_pool() if preheat_enabled else self._preheat_pool
        if preheat_pool is not None:
            if not preheat_enabled and source_type.endswith("_stream"):
                preheat_pool.stop_stream_preheat(source_id)
            else:
                preheat_pool.before_open(source_id, source_type)
        adapter_preheat_pool = preheat_pool if preheat_enabled else None
        if source_type == "web" and window is not None:
            from scp_cv.player.adapters.web import WebSourceAdapter

            if isinstance(adapter, WebSourceAdapter):
                adapter.set_parent_container(window.web_container)
                adapter.set_preheat_context(
                    source_id,
                    preheat_enabled,
                    adapter_preheat_pool.web_pool if adapter_preheat_pool is not None else None,
                )
                return
        set_preheat_context = getattr(adapter, "set_preheat_context", None)
        if callable(set_preheat_context):
            set_preheat_context(source_id, preheat_enabled, adapter_preheat_pool)

    def _reheat_source_if_enabled(self, source_id: int) -> None:
        """
        适配器切离后按媒体源配置重新预热。
        :param source_id: 媒体源 ID
        :return: None
        """
        from scp_cv.apps.playback.models import MediaSource

        source = MediaSource.objects.filter(
            pk=source_id,
            is_available=True,
            keep_alive=True,
            is_temporary=False,
        ).only(
            "id",
            "source_type",
            "uri",
            "metadata",
        ).first()
        if source is None:
            return
        preheat_uri = source.uri
        if source.source_type == "ppt":
            from scp_cv.services.ppt_playback_cache import resolve_ppt_playback_uri
            preheat_uri = resolve_ppt_playback_uri(source)
        self._ensure_preheat_pool().preheat_source(
            source.pk,
            source.source_type,
            preheat_uri,
            force=source.source_type != "web",
        )


__all__ = ["PlayerAdapterLifecycleMixin"]
