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
        处理 OPEN 指令：创建新适配器，待新内容可见后再关闭旧适配器。
        在 Qt 主线程中执行，保证 Qt widget 和 COM 对象创建安全。
        :param window_id: 目标窗口编号
        :param command_args: 包含 source_type, uri, autoplay 的参数字典
        """
        source_type = str(command_args.get("source_type", ""))
        uri = str(command_args.get("uri", ""))
        autoplay = bool(command_args.get("autoplay", True))
        source_id = int(command_args.get("source_id") or 0)
        preheat_enabled = bool(command_args.get("preheat_enabled", False))
        ppt_backend = str(command_args.get("ppt_backend", "")).strip()
        target_slide = int(command_args.get("target_slide") or 0)

        if not source_type or not uri:
            logger.warning("窗口 %d：OPEN 指令缺少 source_type 或 uri", window_id)
            return

        previous_adapter = self._adapters.pop(window_id, None)
        previous_source_type = self._adapter_source_types.pop(window_id, None)
        previous_source_id = self._adapter_source_ids.pop(window_id, None)
        self._last_reported_states.pop(window_id, None)

        is_web_source = source_type == "web"
        is_ppt_source = source_type == "ppt"
        adapter = None
        preclosed_source_id: int | None = None
        preclosed_source_type: str | None = None
        should_preclose_previous = self._should_close_previous_before_open(
            previous_adapter,
            previous_source_type,
            source_type,
        )

        try:
            adapter_options = {"ppt_backend": ppt_backend} if source_type == "ppt" and ppt_backend else {}
            adapter = create_adapter(source_type, **adapter_options)
            window_handle = self.get_window_handle(window_id)
            if window_handle == 0:
                try:
                    adapter.close()
                except Exception as close_error:
                    logger.debug("窗口 %d 缺少句柄时关闭新适配器异常：%s", window_id, close_error)
                self._restore_previous_adapter(
                    window_id,
                    previous_adapter,
                    previous_source_type,
                    previous_source_id,
                )
                logger.warning("窗口 %d 没有可用句柄，跳过 OPEN", window_id)
                return

            if should_preclose_previous:
                self._close_detached_adapter(
                    window_id,
                    previous_adapter,
                    previous_source_type,
                    previous_source_id,
                    restore_window=True,
                    reheat=False,
                )
                preclosed_source_id = previous_source_id
                preclosed_source_type = previous_source_type
                previous_adapter = None
                previous_source_type = None
                previous_source_id = None

            window = self.get_window(window_id)
            if window is not None:
                window.show_black_screen()
                window.show()
                window.raise_()

            self._prepare_adapter_preheat_context(
                adapter,
                source_id,
                source_type,
                preheat_enabled,
                ppt_backend,
                uri,
                window,
            )
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
            if previous_adapter is None and (is_ppt_source or preclosed_source_type == "ppt"):
                self._restore_player_window_to_black(window_id)
            if preclosed_source_id and preclosed_source_id != source_id:
                self._reheat_source_if_enabled(int(preclosed_source_id))
            raise
        self._adapters[window_id] = adapter
        self._adapter_source_types[window_id] = source_type
        if source_id > 0:
            self._adapter_source_ids[window_id] = source_id

        if window is not None:
            if is_web_source:
                window.show_web_container()
            elif is_ppt_source:
                self._sync_ppt_window_visibility(window_id, adapter)
            else:
                window.show_video_container()

        # 直播流需要等待 libVLC 完成首帧握手，不能在 OPEN 指令刚执行时提前标记 playing。
        initial_state = "loading" if _is_stream_source(source_type) or not autoplay else "playing"
        self._update_session_state(window_id, initial_state)
        if previous_adapter is not None:
            self._close_detached_adapter(
                window_id,
                previous_adapter,
                previous_source_type,
                previous_source_id,
                restore_window=False,
                reheat=True,
            )
        if preclosed_source_id and preclosed_source_id != source_id:
            self._reheat_source_if_enabled(int(preclosed_source_id))
        self._cleanup_temporary_source(command_args)

    def _handle_play(self, window_id: int, command_args: dict[str, object]) -> None:
        """处理 PLAY 指令。"""
        adapter = self._adapters.get(window_id)
        if adapter is not None:
            adapter.play()
            if self._adapter_source_types.get(window_id) == "ppt":
                self._sync_ppt_window_visibility(window_id, adapter)
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
            if self._adapter_source_types.get(window_id) == "ppt":
                self._restore_player_window_to_black(window_id)
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
            window.show()
            window.raise_()
            window.show_black_screen()

        from scp_cv.apps.playback.models import PlaybackState, PlaybackSession, PptPlaybackBackend
        session = PlaybackSession.objects.filter(window_id=window_id).first()
        if session is not None:
            session.media_source = None
            session.playback_state = PlaybackState.IDLE
            session.error_message = ""
            session.current_slide = 0
            session.total_slides = 0
            session.ppt_backend = PptPlaybackBackend.LIBREOFFICE
            session.position_ms = 0
            session.duration_ms = 0
            session.save()

    def _handle_reset_all_windows(self) -> None:
        """
        处理全局重置：关闭全部播放资源、替换窗口并重新建立媒体预热池。
        :return: None
        """
        for adapter_window_id in list(self._adapters.keys()):
            self._close_adapter(adapter_window_id, reheat=False)
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
        logger.info("播放器已完成全部窗口重置和媒体预热重建")

    @staticmethod
    def _reset_window_session_to_idle(window_id: int) -> None:
        """
        将播放器侧确认过的窗口会话字段保持为空闲状态。
        :param window_id: 窗口编号
        :return: None
        """
        from scp_cv.apps.playback.models import PlaybackState, PlaybackSession, PptPlaybackBackend

        session = PlaybackSession.objects.filter(window_id=window_id).first()
        if session is None:
            return
        session.media_source = None
        session.playback_state = PlaybackState.IDLE
        session.error_message = ""
        session.current_slide = 0
        session.total_slides = 0
        session.ppt_backend = PptPlaybackBackend.LIBREOFFICE
        session.position_ms = 0
        session.duration_ms = 0
        session.save(update_fields=[
            "media_source",
            "playback_state",
            "error_message",
            "current_slide",
            "total_slides",
            "ppt_backend",
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

    def _handle_reset_ppt(self, window_id: int, command_args: dict[str, object]) -> None:
        """
        处理全局 PPT 放映重置：关闭所有 PPT 放映窗口并按原页码重开。
        :param window_id: 协调窗口编号
        :param command_args: 包含 restart_sessions 的参数字典
        :return: None
        """
        restart_sessions = command_args.get("restart_sessions", [])
        for adapter_window_id, source_type in list(self._adapter_source_types.items()):
            if source_type == "ppt":
                self._close_adapter(adapter_window_id, reheat=False)

        if not isinstance(restart_sessions, list):
            logger.warning("窗口 %d：RESET_PPT 参数 restart_sessions 不是列表", window_id)
            return
        for raw_restart in restart_sessions:
            if not isinstance(raw_restart, dict):
                continue
            restart_window_id = int(raw_restart.get("window_id") or 0)
            if restart_window_id not in self.registered_window_ids:
                continue
            self._handle_open(restart_window_id, dict(raw_restart))
        logger.info("播放器已完成 PPT 放映重置，重启窗口数=%d", len(restart_sessions))

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
        self._close_detached_adapter(window_id, adapter, source_type, source_id, restore_window, reheat)
        self._adapter_source_types.pop(window_id, None)
        self._adapter_source_ids.pop(window_id, None)
        self._last_reported_states.pop(window_id, None)

    @staticmethod
    def _should_close_previous_before_open(
        previous_adapter: object | None,
        previous_source_type: str | None,
        next_source_type: str,
    ) -> bool:
        """
        判断旧适配器是否必须在新源打开前释放。
        :param previous_adapter: 已从当前窗口摘除的旧适配器
        :param previous_source_type: 旧源类型
        :param next_source_type: 即将打开的新源类型
        :return: True 表示先关闭旧源，避免后端互相竞争或阻塞主线程
        """
        if previous_adapter is None or previous_source_type != "ppt":
            return False
        if next_source_type == "ppt":
            return True
        return not bool(getattr(previous_adapter, "has_external_slideshow_window", False))

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
            try:
                adapter.close()
            except Exception as close_error:
                logger.warning("关闭窗口 %d 适配器异常：%s", window_id, close_error)
        if restore_window and source_type == "ppt":
            self._restore_player_window_to_black(window_id)
        if reheat and source_id:
            self._reheat_source_if_enabled(int(source_id))

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
            self._sync_ppt_window_visibility(window_id, adapter)
        elif source_type == "web":
            window.show()
            window.raise_()
            window.show_web_container()
        else:
            window.show()
            window.raise_()
            window.show_video_container()

    def _prepare_adapter_preheat_context(
        self,
        adapter: object,
        source_id: int,
        source_type: str,
        preheat_enabled: bool,
        ppt_backend: str,
        uri: str,
        window: object | None,
    ) -> None:
        """
        为适配器注入统一预热上下文。
        :param adapter: 新建适配器
        :param source_id: 媒体源 ID
        :param source_type: 媒体源类型
        :param preheat_enabled: 是否启用预热
        :param ppt_backend: PPT 后端
        :param uri: 媒体 URI
        :param window: 播放窗口
        :return: None
        """
        preheat_pool = self._ensure_preheat_pool() if preheat_enabled else self._preheat_pool
        if preheat_pool is not None:
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
            "ppt_backend",
        ).first()
        if source is None:
            return
        self._ensure_preheat_pool().preheat_source(
            source.pk,
            source.source_type,
            source.uri,
            getattr(source, "ppt_backend", ""),
            force=source.source_type != "web",
        )

    def _sync_ppt_window_visibility(self, window_id: int, adapter: object) -> None:
        """
        根据 PPT 外部放映窗口是否存在切换 PySide 播放窗口可见性。
        :param window_id: 窗口编号
        :param adapter: 当前 PPT 适配器
        :return: None
        """
        if bool(getattr(adapter, "has_external_slideshow_window", False)):
            window = self.get_window(window_id)
            if window is not None:
                window.hide_window()
            return
        self._restore_player_window_to_black(window_id)

    def _restore_player_window_to_black(self, window_id: int) -> None:
        """
        恢复 PySide 播放窗口并显示黑屏。
        :param window_id: 窗口编号
        :return: None
        """
        window = self.get_window(window_id)
        if window is None:
            return
        window.show()
        window.raise_()
        window.show_black_screen()

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
