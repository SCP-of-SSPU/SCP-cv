"""播放器数据库轮询、指令投递与状态上报。"""

from __future__ import annotations

import logging
import time

from PySide6.QtCore import Slot

logger = logging.getLogger(__name__)


class PlayerPollingMixin:
    """隔离 PlayerController 的数据库轮询边界。"""

    def _poll_loop(self, interval_seconds: float) -> None:
        """轮询已注册窗口的指令并请求 Qt 主线程上报状态。"""
        import django

        django.setup()
        safe_interval_seconds = max(0.01, float(interval_seconds))
        stop_event = getattr(self, "_poll_stop_event", None)
        while self._poll_running and (stop_event is None or not stop_event.is_set()):
            try:
                for window_id in self.registered_window_ids:
                    self._check_and_dispatch_command(window_id)
                self._check_display_position_changes()
                self._touch_player_heartbeats_if_due()
                if self._enable_background_audio:
                    self._check_and_dispatch_background_audio_command()
                self._request_adapter_state_report()
            except Exception as poll_error:
                logger.error("轮询处理异常：%s", poll_error)
            if stop_event is None:
                time.sleep(safe_interval_seconds)
            else:
                stop_event.wait(safe_interval_seconds)

    def _touch_player_heartbeats_if_due(self) -> None:
        """每两秒上报一次当前进程实际托管的播放器窗口。"""
        now = time.monotonic()
        if now - self._last_player_heartbeat_monotonic < 2.0:
            return
        from scp_cv.services.playback_sessions import touch_player_heartbeats

        touch_player_heartbeats(tuple(self.registered_window_ids))
        self._last_player_heartbeat_monotonic = now

    def _check_display_position_changes(self) -> None:
        """轮询显示配置并通过 Qt 信号立即移动运行中的窗口。"""
        try:
            from PySide6.QtCore import QRect
            from scp_cv.services.display import list_display_targets
            from scp_cv.services.playback_sessions import get_or_create_session

            targets = {target.name: target for target in list_display_targets()}
            for window_id in self.registered_window_ids:
                session = get_or_create_session(window_id)
                label = str(session.target_display_label or "")
                if not label or self._last_display_labels.get(window_id) == label:
                    continue
                target = targets.get(label)
                if target is None:
                    continue
                self._last_display_labels[window_id] = label
                self.sig_reposition.emit(window_id, QRect(target.x, target.y, target.width, target.height))
        except Exception as display_error:
            logger.debug("显示目标轮询暂不可用：%s", display_error)

    def _request_adapter_state_report(self) -> None:
        """请求 Qt 主线程上报适配器状态，避免跨线程访问 COM/Qt 对象。"""
        with self._state_report_lock:
            if self._state_report_pending:
                return
            self._state_report_pending = True
        self.sig_report_states.emit()

    def _check_and_dispatch_command(self, window_id: int) -> None:
        """按顺序领取窗口指令并投递给 Qt 主线程。"""
        from scp_cv.apps.playback.models import PlaybackCommand, PlaybackSession
        from scp_cv.services.playback_commands import claim_next_playback_command, enqueue_playback_command

        queued_command = claim_next_playback_command(window_id, self._consumer_id)
        if queued_command is not None:
            logger.info(
                "窗口 %d 队列领取指令：%s，参数=%s，发射到主线程",
                window_id,
                queued_command.command,
                queued_command.command_args,
            )
            self.sig_dispatch_command.emit(
                window_id,
                queued_command.command,
                dict(queued_command.command_args),
                queued_command.id,
                queued_command.consumer_id,
            )
            return

        session = PlaybackSession.objects.filter(window_id=window_id).first()
        if session is None:
            return
        pending = session.pending_command
        if not pending or pending == PlaybackCommand.NONE:
            return
        command_args = dict(session.command_args or {})
        if not session.command_queue.exists():
            enqueue_playback_command(session, pending, command_args)
        queued_command = claim_next_playback_command(window_id, self._consumer_id)
        if queued_command is None:
            return
        logger.info("窗口 %d 轮询检测到兼容指令：%s，参数=%s，发射到主线程", window_id, queued_command.command, queued_command.command_args)
        self.sig_dispatch_command.emit(
            window_id,
            queued_command.command,
            dict(queued_command.command_args),
            queued_command.id,
            queued_command.consumer_id,
        )

    @Slot()
    def _report_all_adapter_states(self) -> None:
        """在 Qt 主线程读取所有活跃适配器状态并回写到 DB。"""
        from scp_cv.services.playback import update_playback_progress

        try:
            if self._preheat_pool is not None:
                maintain = getattr(self._preheat_pool, "maintain", None)
                if callable(maintain):
                    maintain()
            for window_id, adapter in self._adapters.items():
                if adapter is None or not adapter.is_open:
                    continue
                if not self._adapter_matches_current_session(window_id):
                    logger.debug("窗口 %d adapter 源已过期，跳过本次状态上报", window_id)
                    continue
                try:
                    adapter_state = adapter.get_state()
                except Exception as state_error:
                    logger.warning("窗口 %d 读取适配器状态失败：%s", window_id, state_error)
                    continue
                state_signature = (
                    adapter_state.playback_state,
                    adapter_state.error_message,
                    adapter_state.current_slide,
                    adapter_state.total_slides,
                    adapter_state.position_ms,
                    adapter_state.duration_ms,
                )
                if state_signature == self._last_reported_states.get(window_id):
                    continue
                update_playback_progress(
                    window_id=window_id,
                    playback_state=adapter_state.playback_state,
                    error_message=adapter_state.error_message,
                    current_slide=adapter_state.current_slide,
                    total_slides=adapter_state.total_slides,
                    position_ms=adapter_state.position_ms,
                    duration_ms=adapter_state.duration_ms,
                )
                self._last_reported_states[window_id] = state_signature
            if self._enable_background_audio:
                self._report_background_audio_state()
        finally:
            with self._state_report_lock:
                self._state_report_pending = False

    def _adapter_matches_current_session(self, window_id: int) -> bool:
        """返回 adapter 是否仍对应当前会话源。"""
        expected_source_id = self._adapter_source_ids.get(window_id)
        if expected_source_id is None:
            return True
        from scp_cv.apps.playback.models import PlaybackSession

        session = PlaybackSession.objects.filter(window_id=window_id).only("media_source_id").first()
        return session is not None and session.media_source_id == expected_source_id


__all__ = ["PlayerPollingMixin"]
