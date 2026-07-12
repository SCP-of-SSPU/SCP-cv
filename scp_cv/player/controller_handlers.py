#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
播放器控制器指令处理 mixin，集中维护主线程内的适配器操作。
@Project : SCP-cv
@File : controller_handlers.py
@Author : Qintsg
@Date : 2026-05-02
'''
from __future__ import annotations

import logging

from scp_cv.player.adapters import create_adapter
from scp_cv.player.controller_adapter_lifecycle import PlayerAdapterLifecycleMixin
from scp_cv.player.controller_ppt_open import PptOpenFlowMixin
from scp_cv.player.controller_window_helpers import PlayerWindowHelpersMixin

logger = logging.getLogger(__name__)


def _is_stream_source(source_type: str) -> bool:
    """
    判断媒体源是否属于直播流。
    :param source_type: MediaSource.source_type 原始值
    :return: True 表示需要等待适配器确认首帧连接
    """
    return source_type.endswith("_stream")


class PlayerCommandHandlersMixin(
    PlayerAdapterLifecycleMixin,
    PptOpenFlowMixin,
    PlayerWindowHelpersMixin,
):
    """
    PlayerController 指令处理 mixin。

    这些方法依赖 PlayerController 的窗口、适配器和状态缓存字段；
    单独拆出是为了让主控制器文件只保留轮询、信号和窗口注册职责。
    """

    def _handle_open(self, window_id: int, command_args: dict[str, object]) -> None:
        """
        处理 OPEN 指令：创建新适配器，待新内容可见后再关闭旧适配器。
        在 Qt 主线程中执行，保证 Qt widget 和适配器创建安全。
        :param window_id: 目标窗口编号
        :param command_args: 包含 source_type, uri, autoplay 的参数字典
        """
        source_type = str(command_args.get("source_type", ""))
        uri = str(command_args.get("uri", ""))
        autoplay = bool(command_args.get("autoplay", True))
        source_id = int(command_args.get("source_id") or 0)
        preheat_enabled = bool(command_args.get("preheat_enabled", False))
        target_slide = int(command_args.get("target_slide") or 0)

        if not source_type or not uri:
            raise ValueError(
                f"窗口 {window_id} OPEN 指令缺少 source_type 或 uri"
            )

        previous_adapter = self._adapters.pop(window_id, None)
        previous_source_type = self._adapter_source_types.pop(window_id, None)
        previous_source_id = self._adapter_source_ids.pop(window_id, None)
        self._last_reported_states.pop(window_id, None)
        if previous_source_type == "ppt":
            self._detach_ppt_for_fast_switch(previous_adapter)

        is_web_source = source_type == "web"
        is_ppt_source = source_type == "ppt"
        is_stream_source = _is_stream_source(source_type)
        adapter = None

        try:
            adapter_options: dict[str, object] = {}
            if is_ppt_source:
                adapter_options = {
                    "broker": self._ppt_broker,
                    "window_id": window_id,
                    "owner_prefix": self._command_consumer_id,
                }
            adapter = create_adapter(source_type, **adapter_options)
            window_handle = self.get_window_handle(window_id)
            if window_handle == 0:
                raise RuntimeError(
                    f"窗口 {window_id} 没有可用窗口句柄，无法执行 OPEN"
                )

            window = self.get_window(window_id)
            if window is not None:
                window.show_black_screen()
                window.show()
                self._set_player_window_topmost(window, True)
                window.raise_()
                if is_ppt_source:
                    self._prepare_ppt_container(window_id, window)
                elif is_stream_source:
                    self._prepare_video_render_window(window_id, window)

            self._prepare_adapter_preheat_context(
                adapter,
                source_id,
                source_type,
                preheat_enabled,
                uri,
                window,
            )
            if is_ppt_source:
                open_async = getattr(adapter, "open_async", None)
                if callable(open_async):
                    # PPT 慢操作由 Broker 串行执行，完成后经信号回主线程收尾。
                    self._begin_ppt_open_async(
                        window_id,
                        adapter,
                        window_handle,
                        command_args,
                        previous_adapter,
                        previous_source_type,
                        previous_source_id,
                    )
                    return
            adapter.open(uri=uri, window_handle=window_handle, autoplay=autoplay)
            if is_ppt_source and target_slide > 0:
                adapter.goto_item(target_slide)
            adapter.set_volume(int(command_args.get("volume", 100)))
            adapter.set_mute(bool(command_args.get("muted", False)))
        except Exception:
            if adapter is not None:
                try:
                    adapter.close()
                except Exception as close_error:
                    logger.debug("窗口 %d 打开失败后关闭新适配器异常：%s", window_id, close_error)
            self._restore_previous_adapter(
                window_id,
                previous_adapter,
                previous_source_type,
                previous_source_id,
            )
            if previous_adapter is None and is_ppt_source:
                self._restore_player_window_to_black(window_id)
            raise
        self._adapters[window_id] = adapter
        self._adapter_source_types[window_id] = source_type
        if source_id > 0:
            self._adapter_source_ids[window_id] = source_id

        if window is not None:
            if is_web_source:
                window.show_web_container()
            elif is_ppt_source:
                self._show_ppt_container(window_id)
            else:
                window.show_video_container()

        # 直播流需要等待 libVLC 完成首帧握手，不能在 OPEN 指令刚执行时提前标记 playing。
        initial_state = "loading" if is_stream_source or not autoplay else "playing"
        self._update_session_state(window_id, initial_state)
        if previous_adapter is not None:
            self._schedule_close_detached_adapter(
                window_id,
                previous_adapter,
                previous_source_type,
                previous_source_id,
                restore_window=False,
                reheat=True,
            )
        self._cleanup_temporary_source(command_args)

    def _require_adapter(self, window_id: int, command: str) -> object:
        """返回窗口当前适配器；缺失时把确定性执行错误交给确认层。"""
        adapter = self._adapters.get(window_id)
        if adapter is None:
            raise RuntimeError(
                f"窗口 {window_id} 无可用播放适配器，无法执行 {command}"
            )
        return adapter

    def _handle_play(self, window_id: int, command_args: dict[str, object]) -> None:
        """处理 PLAY 指令。"""
        adapter = self._require_adapter(window_id, "PLAY")
        adapter.play()
        if self._adapter_source_types.get(window_id) == "ppt":
            self._show_ppt_container(window_id)
        self._update_session_state(window_id, "playing")

    def _handle_pause(self, window_id: int, command_args: dict[str, object]) -> None:
        """处理 PAUSE 指令。"""
        adapter = self._require_adapter(window_id, "PAUSE")
        adapter.pause()
        self._update_session_state(window_id, "paused")

    def _handle_stop(self, window_id: int, command_args: dict[str, object]) -> None:
        """处理 STOP 指令。"""
        adapter = self._require_adapter(window_id, "STOP")
        adapter.stop()
        if self._adapter_source_types.get(window_id) == "ppt":
            self._restore_player_window_to_black(window_id)
        self._update_session_state(window_id, "stopped")

    def _handle_next(self, window_id: int, command_args: dict[str, object]) -> None:
        """处理 NEXT 指令。"""
        adapter = self._require_adapter(window_id, "NEXT")
        adapter.next_item()

    def _handle_prev(self, window_id: int, command_args: dict[str, object]) -> None:
        """处理 PREV 指令。"""
        adapter = self._require_adapter(window_id, "PREV")
        adapter.prev_item()

    def _handle_goto(self, window_id: int, command_args: dict[str, object]) -> None:
        """处理 GOTO 指令。"""
        adapter = self._require_adapter(window_id, "GOTO")
        target_index = int(command_args.get("target_index", 1))
        adapter.goto_item(target_index)

    def _handle_seek(self, window_id: int, command_args: dict[str, object]) -> None:
        """处理 SEEK 指令。"""
        adapter = self._require_adapter(window_id, "SEEK")
        position_ms = int(command_args.get("position_ms", 0))
        adapter.seek(position_ms)

    def _handle_ppt_media(self, window_id: int, command_args: dict[str, object]) -> None:
        """处理 PPT 当前页媒体播放 / 暂停 / 停止指令。"""
        adapter = self._require_adapter(window_id, "PPT_MEDIA")
        media_index = int(command_args.get("media_index", 0))
        adapter.control_media(
            str(command_args.get("media_id", "")),
            str(command_args.get("media_action", "")),
            media_index,
        )

    def _handle_set_loop(self, window_id: int, command_args: dict[str, object]) -> None:
        """
        处理 SET_LOOP 指令：切换指定窗口适配器的循环播放状态。
        :param window_id: 窗口编号
        :param command_args: 包含 enabled 字段的参数字典
        """
        adapter = self._require_adapter(window_id, "SET_LOOP")
        loop_enabled = bool(command_args.get("enabled", False))
        adapter.set_loop(loop_enabled)
        logger.info("窗口 %d 循环播放已设置为 %s", window_id, loop_enabled)

    def _handle_set_volume(self, window_id: int, command_args: dict[str, object]) -> None:
        """
        处理 SET_VOLUME 指令：调整指定窗口适配器音量。
        :param window_id: 窗口编号
        :param command_args: 包含 volume 字段的参数字典
        """
        adapter = self._require_adapter(window_id, "SET_VOLUME")
        volume = int(command_args.get("volume", 100))
        adapter.set_volume(volume)
        logger.info("窗口 %d 音量已设置为 %d", window_id, volume)

    def _handle_set_mute(self, window_id: int, command_args: dict[str, object]) -> None:
        """
        处理 SET_MUTE 指令：调整指定窗口适配器静音状态。
        :param window_id: 窗口编号
        :param command_args: 包含 muted 字段的参数字典
        """
        adapter = self._require_adapter(window_id, "SET_MUTE")
        muted = bool(command_args.get("muted", False))
        adapter.set_mute(muted)
        logger.info("窗口 %d 静音已设置为 %s", window_id, muted)

    def _handle_show_id(self, window_id: int, command_args: dict[str, object]) -> None:
        """
        处理 SHOW_ID 指令：在指定窗口显示半透明 ID 覆盖层 5 秒。
        :param window_id: 窗口编号
        :param command_args: 未使用
        """
        window = self.get_window(window_id)
        if window is None:
            raise RuntimeError(
                f"窗口 {window_id} 没有可用播放器窗口，无法执行 SHOW_ID"
            )
        window.show_id_overlay()
        logger.info("窗口 %d 触发 ID 覆盖层显示", window_id)

    def _update_session_state(self, window_id: int, playback_state: str) -> None:
        """
        更新指定窗口会话播放状态。
        :param window_id: 窗口编号
        :param playback_state: 新的播放状态值
        """
        from scp_cv.apps.playback.models import PlaybackSession
        session = PlaybackSession.objects.filter(window_id=window_id).first()
        if session is not None:
            update_fields = ["playback_state", "error_message", "last_updated_at"]
            source_id = self._adapter_source_ids.get(window_id)
            if source_id is not None and session.media_source_id != source_id:
                session.media_source_id = source_id
                update_fields.append("media_source")
            session.playback_state = playback_state
            session.error_message = ""
            session.save(update_fields=update_fields)

    def _update_session_error(self, window_id: int, error_message: str) -> None:
        """
        更新指定窗口会话为错误状态。
        :param window_id: 窗口编号
        :param error_message: 错误描述
        """
        logger.error("窗口 %d 播放会话错误：%s", window_id, error_message)
        from scp_cv.apps.playback.models import PlaybackSession
        session = PlaybackSession.objects.filter(window_id=window_id).first()
        if session is not None:
            session.playback_state = "error"
            session.error_message = error_message
            session.save(update_fields=["playback_state", "error_message", "last_updated_at"])
