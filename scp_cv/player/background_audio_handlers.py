#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
播放器背景音频指令处理 mixin。
@Project : SCP-cv
@File : background_audio_handlers.py
@Author : Qintsg
@Date : 2026-05-31
'''
from __future__ import annotations

import logging

from scp_cv.player.adapters.background_audio import BackgroundAudioAdapter

logger = logging.getLogger(__name__)


class BackgroundAudioHandlersMixin:
    """PlayerController 背景音频指令与状态上报逻辑。"""

    def _check_and_dispatch_background_audio_command(self) -> None:
        """
        读取背景音频待执行指令并派发到 Qt 主线程。

        :return: None
        """
        from scp_cv.apps.playback.models import BackgroundAudioCommand, BackgroundAudioState

        state = BackgroundAudioState.objects.filter(pk=1).first()
        if state is None:
            return
        pending = state.pending_command
        if not pending or pending == BackgroundAudioCommand.NONE:
            return

        command_args = dict(state.command_args or {})
        logger.info("背景音频轮询检测到指令：%s，参数=%s", pending, command_args)
        self.sig_dispatch_background_audio_command.emit(pending, command_args)

        from scp_cv.services.background_audio import clear_background_audio_command
        clear_background_audio_command()

    def _execute_background_audio_command_on_main_thread(
        self,
        command: str,
        command_args: dict[str, object],
    ) -> None:
        """
        在 Qt 主线程执行背景音频指令。

        :param command: 指令名
        :param command_args: 指令参数
        :return: None
        """
        from scp_cv.apps.playback.models import BackgroundAudioCommand

        command_dispatch: dict[str, object] = {
            BackgroundAudioCommand.OPEN: self._handle_background_audio_open,
            BackgroundAudioCommand.PLAY: self._handle_background_audio_play,
            BackgroundAudioCommand.PAUSE: self._handle_background_audio_pause,
            BackgroundAudioCommand.STOP: self._handle_background_audio_stop,
            BackgroundAudioCommand.SEEK: self._handle_background_audio_seek,
            BackgroundAudioCommand.SET_VOLUME: self._handle_background_audio_set_volume,
            BackgroundAudioCommand.SET_MUTE: self._handle_background_audio_set_mute,
            BackgroundAudioCommand.SET_LOOP: self._handle_background_audio_set_loop,
        }
        handler = command_dispatch.get(command)
        if handler is None:
            return
        try:
            handler(command_args)
        except Exception as command_error:
            logger.error("执行背景音频指令 %s 失败：%s", command, command_error)
            from scp_cv.services.background_audio import update_background_audio_progress
            update_background_audio_progress(playback_state="error", error_message=str(command_error))

    def _handle_background_audio_open(self, command_args: dict[str, object]) -> None:
        """
        打开背景音频源。

        :param command_args: 包含 source_id、uri、autoplay、volume、muted
        :return: None
        """
        uri = str(command_args.get("uri", ""))
        if not uri:
            raise ValueError("背景音频 OPEN 指令缺少 uri")
        self._close_background_audio_adapter()
        source_id = int(command_args.get("source_id") or 0)
        preheated_audio = None
        if self._preheat_pool is not None and source_id > 0:
            take_audio = getattr(self._preheat_pool, "take_audio", None)
            if callable(take_audio):
                preheated_audio = take_audio(source_id, uri)
        adapter = BackgroundAudioAdapter(finished_callback=self._request_background_audio_advance)
        adapter.open(
            uri=uri,
            autoplay=bool(command_args.get("autoplay", True)),
            preheated_audio=preheated_audio,
        )
        adapter.set_volume(int(command_args.get("volume", 70)))
        adapter.set_mute(bool(command_args.get("muted", False)))
        self._background_audio_adapter = adapter
        self._background_audio_source_id = source_id
        self._last_reported_background_audio_state = None

        from scp_cv.services.background_audio import update_background_audio_progress
        update_background_audio_progress(playback_state="playing" if bool(command_args.get("autoplay", True)) else "paused")

    def _handle_background_audio_play(self, command_args: dict[str, object]) -> None:
        """恢复背景音频播放。"""
        if self._background_audio_adapter is not None:
            self._background_audio_adapter.play()

    def _handle_background_audio_pause(self, command_args: dict[str, object]) -> None:
        """暂停背景音频播放。"""
        if self._background_audio_adapter is not None:
            self._background_audio_adapter.pause()

    def _handle_background_audio_stop(self, command_args: dict[str, object]) -> None:
        """停止背景音频播放，必要时释放文件句柄。"""
        if bool(command_args.get("clear_source", False)):
            self._close_background_audio_adapter()
            return
        if self._background_audio_adapter is not None:
            self._background_audio_adapter.stop()

    def _handle_background_audio_seek(self, command_args: dict[str, object]) -> None:
        """跳转背景音频播放进度。"""
        if self._background_audio_adapter is not None:
            self._background_audio_adapter.seek(int(command_args.get("position_ms", 0)))

    def _handle_background_audio_set_volume(self, command_args: dict[str, object]) -> None:
        """设置背景音频音量。"""
        if self._background_audio_adapter is not None:
            self._background_audio_adapter.set_volume(int(command_args.get("volume", 70)))

    def _handle_background_audio_set_mute(self, command_args: dict[str, object]) -> None:
        """设置背景音频静音。"""
        if self._background_audio_adapter is not None:
            self._background_audio_adapter.set_mute(bool(command_args.get("muted", False)))

    def _handle_background_audio_set_loop(self, command_args: dict[str, object]) -> None:
        """列表循环由服务层推进逻辑处理，播放器侧无需额外动作。"""

    def _close_background_audio_adapter(self) -> None:
        """
        关闭背景音频适配器。

        :return: None
        """
        adapter = self._background_audio_adapter
        self._background_audio_adapter = None
        self._background_audio_source_id = 0
        self._last_reported_background_audio_state = None
        if adapter is not None:
            adapter.close()

    def _report_background_audio_state(self) -> None:
        """
        上报背景音频适配器状态。

        :return: None
        """
        adapter = self._background_audio_adapter
        if adapter is None or not adapter.is_open:
            return
        adapter_state = adapter.get_state()
        state_signature = (
            adapter_state.playback_state,
            adapter_state.error_message,
            adapter_state.position_ms,
            adapter_state.duration_ms,
        )
        if state_signature == self._last_reported_background_audio_state:
            return

        from scp_cv.services.background_audio import update_background_audio_progress
        update_background_audio_progress(
            playback_state=adapter_state.playback_state,
            error_message=adapter_state.error_message,
            position_ms=adapter_state.position_ms,
            duration_ms=adapter_state.duration_ms,
        )
        self._last_reported_background_audio_state = state_signature

    def _request_background_audio_advance(self) -> None:
        """
        当前背景音频自然结束时通知服务层推进播放列表。

        :return: None
        """
        from scp_cv.services.background_audio import advance_background_audio_on_finished
        advance_background_audio_on_finished()
