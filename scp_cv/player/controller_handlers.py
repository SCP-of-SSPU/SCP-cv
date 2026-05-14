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

logger = logging.getLogger(__name__)


def _is_stream_source(source_type: str) -> bool:
    """
    判断媒体源是否属于直播流。
    :param source_type: MediaSource.source_type 原始值
    :return: True 表示需要等待适配器确认首帧连接
    """
    return source_type.endswith("_stream")


class PlayerCommandHandlersMixin:
    """
    PlayerController 指令处理 mixin。

    这些方法依赖 PlayerController 的窗口、适配器和状态缓存字段；
    单独拆出是为了让主控制器文件只保留轮询、信号和窗口注册职责。
    """

    def _handle_open(self, window_id: int, command_args: dict[str, object]) -> None:
        """
        处理 OPEN 指令：关闭旧适配器，创建新适配器并打开源。
        在 Qt 主线程中执行，保证 Qt widget 和 COM 对象创建安全。
        :param window_id: 目标窗口编号
        :param command_args: 包含 source_type, uri, autoplay 的参数字典
        """
        source_type = str(command_args.get("source_type", ""))
        uri = str(command_args.get("uri", ""))
        autoplay = bool(command_args.get("autoplay", True))
        source_id = int(command_args.get("source_id") or 0)
        preheat_enabled = bool(command_args.get("preheat_enabled", False))

        if not source_type or not uri:
            logger.warning("窗口 %d：OPEN 指令缺少 source_type 或 uri", window_id)
            return

        self._close_adapter(window_id)
        self._cleanup_temporary_source(command_args)

        adapter = create_adapter(source_type)
        window_handle = self.get_window_handle(window_id)
        if window_handle == 0:
            logger.warning("窗口 %d 没有可用句柄，跳过 OPEN", window_id)
            return

        is_web_source = source_type == "web"
        if is_web_source:
            window = self.get_window(window_id)
            if window is not None:
                from scp_cv.player.adapters.web import WebSourceAdapter
                if isinstance(adapter, WebSourceAdapter):
                    adapter.set_parent_container(window.web_container)
                    adapter.set_preheat_context(source_id, preheat_enabled, self._web_preheat_pool)

        adapter.open(uri=uri, window_handle=window_handle, autoplay=autoplay)
        adapter.set_volume(int(command_args.get("volume", 100)))
        adapter.set_mute(bool(command_args.get("muted", False)))
        self._adapters[window_id] = adapter
        self._adapter_source_types[window_id] = source_type
        if source_id > 0:
            self._adapter_source_ids[window_id] = source_id

        window = self.get_window(window_id)
        if window is not None:
            if is_web_source:
                window.show_web_container()
            else:
                window.show_video_container()

        # 直播流需要等待 libVLC 完成首帧握手，不能在 OPEN 指令刚执行时提前标记 playing。
        initial_state = "loading" if _is_stream_source(source_type) or not autoplay else "playing"
        self._update_session_state(window_id, initial_state)

    def _handle_play(self, window_id: int, command_args: dict[str, object]) -> None:
        """处理 PLAY 指令。"""
        adapter = self._adapters.get(window_id)
        if adapter is not None:
            adapter.play()
            self._update_session_state(window_id, "playing")

    def _handle_pause(self, window_id: int, command_args: dict[str, object]) -> None:
        """处理 PAUSE 指令。"""
        adapter = self._adapters.get(window_id)
        if adapter is not None:
            adapter.pause()
            self._update_session_state(window_id, "paused")

    def _handle_stop(self, window_id: int, command_args: dict[str, object]) -> None:
        """处理 STOP 指令。"""
        adapter = self._adapters.get(window_id)
        if adapter is not None:
            adapter.stop()
            self._update_session_state(window_id, "stopped")

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

        from scp_cv.apps.playback.models import PlaybackState, PlaybackSession
        session = PlaybackSession.objects.filter(window_id=window_id).first()
        if session is not None:
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
        处理全局重置：关闭全部播放资源、替换窗口并重新建立网页预热池。
        :return: None
        """
        for adapter_window_id in list(self._adapters.keys()):
            self._close_adapter(adapter_window_id)
        self._adapter_source_types.clear()
        self._adapter_source_ids.clear()
        self._last_reported_states.clear()

        if self._web_preheat_pool is not None:
            self._web_preheat_pool.close_all()
            self._web_preheat_pool = None

        for registered_window_id in self.registered_window_ids:
            self._reset_window_session_to_idle(registered_window_id)

        self.rebuild_registered_windows()
        self.preheat_web_sources()
        logger.info("播放器已完成全部窗口重置和网页预热重建")

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

    def _handle_next(self, window_id: int, command_args: dict[str, object]) -> None:
        """处理 NEXT 指令。"""
        adapter = self._adapters.get(window_id)
        if adapter is not None:
            adapter.next_item()

    def _handle_prev(self, window_id: int, command_args: dict[str, object]) -> None:
        """处理 PREV 指令。"""
        adapter = self._adapters.get(window_id)
        if adapter is not None:
            adapter.prev_item()

    def _handle_goto(self, window_id: int, command_args: dict[str, object]) -> None:
        """处理 GOTO 指令。"""
        adapter = self._adapters.get(window_id)
        if adapter is not None:
            target_index = int(command_args.get("target_index", 1))
            adapter.goto_item(target_index)

    def _handle_seek(self, window_id: int, command_args: dict[str, object]) -> None:
        """处理 SEEK 指令。"""
        adapter = self._adapters.get(window_id)
        if adapter is not None:
            position_ms = int(command_args.get("position_ms", 0))
            adapter.seek(position_ms)

    def _handle_ppt_media(self, window_id: int, command_args: dict[str, object]) -> None:
        """处理 PPT 当前页媒体播放 / 暂停 / 停止指令。"""
        adapter = self._adapters.get(window_id)
        if adapter is not None:
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
        adapter = self._adapters.get(window_id)
        if adapter is not None:
            loop_enabled = bool(command_args.get("enabled", False))
            adapter.set_loop(loop_enabled)
            logger.info("窗口 %d 循环播放已设置为 %s", window_id, loop_enabled)

    def _handle_set_volume(self, window_id: int, command_args: dict[str, object]) -> None:
        """
        处理 SET_VOLUME 指令：调整指定窗口适配器音量。
        :param window_id: 窗口编号
        :param command_args: 包含 volume 字段的参数字典
        """
        adapter = self._adapters.get(window_id)
        if adapter is not None:
            volume = int(command_args.get("volume", 100))
            adapter.set_volume(volume)
            logger.info("窗口 %d 音量已设置为 %d", window_id, volume)

    def _handle_set_mute(self, window_id: int, command_args: dict[str, object]) -> None:
        """
        处理 SET_MUTE 指令：调整指定窗口适配器静音状态。
        :param window_id: 窗口编号
        :param command_args: 包含 muted 字段的参数字典
        """
        adapter = self._adapters.get(window_id)
        if adapter is not None:
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
        if window is not None:
            window.show_id_overlay()
            logger.info("窗口 %d 触发 ID 覆盖层显示", window_id)

    def _close_adapter(self, window_id: int) -> None:
        """
        关闭并释放指定窗口的适配器。
        :param window_id: 窗口编号
        """
        adapter = self._adapters.pop(window_id, None)
        if adapter is not None:
            try:
                adapter.close()
            except Exception as close_error:
                logger.warning("关闭窗口 %d 适配器异常：%s", window_id, close_error)
        self._adapter_source_types.pop(window_id, None)
        self._adapter_source_ids.pop(window_id, None)
        self._last_reported_states.pop(window_id, None)

    def _update_session_state(self, window_id: int, playback_state: str) -> None:
        """
        更新指定窗口会话播放状态。
        :param window_id: 窗口编号
        :param playback_state: 新的播放状态值
        """
        from scp_cv.apps.playback.models import PlaybackSession
        session = PlaybackSession.objects.filter(window_id=window_id).first()
        if session is not None:
            session.playback_state = playback_state
            session.error_message = ""
            session.save(update_fields=["playback_state", "error_message", "last_updated_at"])

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
