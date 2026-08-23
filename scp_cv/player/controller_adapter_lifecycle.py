#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
播放器适配器生命周期 mixin，负责关闭、恢复、预热与会话状态回写。
@Project : SCP-cv
@File : controller_adapter_lifecycle.py
@Author : Qintsg
@Date : 2026-08-23
'''
from __future__ import annotations

import logging

from PySide6.QtCore import QTimer

logger = logging.getLogger(__name__)
_PPT_REHEAT_DELAY_MS = 1500
_PPT_DETACHED_CLOSE_DELAY_MS = 450


class PlayerAdapterLifecycleMixin:
    """集中维护播放器适配器离场、恢复和预热生命周期。"""

    def _close_adapter(
        self,
        window_id: int,
        restore_window: bool = True,
        reheat: bool = True,
    ) -> None:
        """
        关闭并释放指定窗口的适配器。
        :param window_id: 窗口编号
        :param restore_window: PPT 关闭后是否恢复 PySide 黑屏窗口
        :param reheat: 关闭后是否按源配置重新预热
        """
        adapter = self._adapters.pop(window_id, None)
        source_type = self._adapter_source_types.get(window_id)
        source_id = self._adapter_source_ids.get(window_id)
        self._close_detached_adapter(
            window_id,
            adapter,
            source_type,
            source_id,
            restore_window,
            reheat,
        )
        self._adapter_source_types.pop(window_id, None)
        self._adapter_source_ids.pop(window_id, None)
        self._adapter_kinds.pop(window_id, None)
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
            try:
                adapter.close()
            except Exception as close_error:
                logger.warning("关闭窗口 %d 适配器异常：%s", window_id, close_error)
        if source_type == "ppt":
            # 本轮已停用 PowerPoint 预热；保留统一预热池扩展点，后续按预建窗口模型恢复。
            logger.debug("窗口 %d 演示文稿离场，跳过后台预热", window_id)
        elif (
            reheat
            and source_id
            and self._should_reheat_closed_source(window_id, int(source_id))
        ):
            self._reheat_source_if_enabled(int(source_id))

    def _close_powerpoint_adapter_sync(
        self,
        window_id: int,
        adapter: object | None,
        source_type: str | None,
        source_id: int | None,
        reset_session: bool,
    ) -> None:
        """
        完整关闭指定窗口的 PowerPoint 适配器并等待资源释放。
        :param window_id: 窗口编号
        :param adapter: PowerPoint 适配器
        :param source_type: 旧源类型
        :param source_id: 旧源 ID
        :param reset_session: 是否将会话重置为 idle
        :return: None
        """
        if adapter is not None:
            try:
                close_and_wait = getattr(adapter, "close_and_wait", None)
                if callable(close_and_wait):
                    close_and_wait()
                else:
                    adapter.close()
            except Exception as close_error:
                logger.warning(
                    "完整关闭窗口 %d PowerPoint 适配器异常：%s",
                    window_id,
                    close_error,
                )
        window = self.get_window(window_id)
        if window is not None:
            window.show_black_screen()
            window.show()
            self._set_player_window_topmost(window, True)
            window.raise_()
        if reset_session:
            self._reset_window_session_to_idle(window_id)
        if source_id:
            try:
                from scp_cv.services.media import delete_temporary_source_if_unused

                delete_temporary_source_if_unused(int(source_id))
            except Exception:
                pass
        logger.info("窗口 %d PowerPoint 已完整关闭", window_id)

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
        if (
            session.media_source_id == source_id
            and session.playback_state != PlaybackState.IDLE
        ):
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
        adapter_kind: str | None = None,
    ) -> None:
        """
        新源打开失败时恢复旧适配器映射和窗口可见性。
        :param window_id: 窗口编号
        :param adapter: 旧适配器
        :param source_type: 旧源类型
        :param source_id: 旧源 ID
        :param adapter_kind: 旧适配器放映模式
        :return: None
        """
        if adapter is None or source_type is None:
            return
        self._adapters[window_id] = adapter
        self._adapter_source_types[window_id] = source_type
        self._adapter_kinds[window_id] = adapter_kind or ""
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

    def _schedule_reheat_source_if_enabled(
        self,
        window_id: int,
        source_id: int,
    ) -> None:
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
        将旧适配器关闭延后到当前 UI 切换完成后。
        :param window_id: 窗口编号
        :param adapter: 已从当前窗口映射中摘除的旧适配器
        :param source_type: 旧适配器源类型
        :param source_id: 旧适配器源 ID
        :param restore_window: 是否恢复 PySide 黑屏窗口
        :param reheat: 是否按源配置重新预热
        :return: None
        """
        delay_ms = _PPT_DETACHED_CLOSE_DELAY_MS if source_type == "ppt" else 0
        QTimer.singleShot(
            delay_ms,
            lambda: self._close_detached_adapter(
                window_id,
                adapter,
                source_type,
                source_id,
                restore_window,
                reheat,
            ),
        )

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
        preheat_pool = (
            self._ensure_preheat_pool() if preheat_enabled else self._preheat_pool
        )
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
                    adapter_preheat_pool.web_pool
                    if adapter_preheat_pool is not None
                    else None,
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
            from scp_cv.services.slides_pdf import resolve_slide_playback_uri

            preheat_uri = resolve_slide_playback_uri(source)
        self._ensure_preheat_pool().preheat_source(
            source.pk,
            source.source_type,
            preheat_uri,
            force=source.source_type != "web",
        )

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
            update_fields = ["playback_state", "error_message", "last_updated_at"]
            visible_source_id = self._adapter_source_ids.get(window_id)
            if (
                visible_source_id is not None
                and session.media_source_id != visible_source_id
            ):
                session.media_source_id = visible_source_id
                update_fields.append("media_source")
            session.playback_state = "error"
            session.error_message = error_message
            session.save(update_fields=update_fields)


__all__ = ["PlayerAdapterLifecycleMixin"]
