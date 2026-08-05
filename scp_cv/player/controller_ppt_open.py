#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
播放器控制器 PPT 异步打开流程 mixin。
PPT 打开经 COM 工作线程后台执行，完成后通过 Qt 信号回到主线程收尾；
打开期间同窗口指令进入待重放队列，避免操作半开状态的适配器。
@Project : SCP-cv
@File : controller_ppt_open.py
@Author : Qintsg
@Date : 2026-06-10
'''
from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# 打开期间单窗口最多积压的待重放指令数，超出时丢弃最早的指令
_MAX_DEFERRED_COMMANDS = 8


@dataclass
class _PendingPptOpen:
    """单窗口在途 PPT 打开请求。"""

    token: int
    adapter: object
    command_args: dict[str, object]
    previous_adapter: object | None
    previous_source_type: str | None
    previous_source_id: int | None
    previous_adapter_kind: str | None = None
    superseded: bool = False
    adapter_disposed: bool = False
    deferred: list[tuple[str, dict[str, object]]] = field(default_factory=list)


class PptOpenFlowMixin:
    """
    PlayerController 的 PPT 异步打开流程。

    依赖控制器字段：_pending_ppt_opens、_ppt_open_token_counter、
    sig_ppt_open_finished 信号，以及打开/恢复/会话更新辅助方法。
    """

    def _begin_ppt_open_async(
        self,
        window_id: int,
        adapter: object,
        window_handle: int,
        command_args: dict[str, object],
        previous_adapter: object | None,
        previous_source_type: str | None,
        previous_source_id: int | None,
        previous_adapter_kind: str | None = None,
    ) -> None:
        """
        发起 PPT 后台打开：注册在途请求并投递 open_async。
        :param window_id: 目标窗口编号
        :param adapter: 新建 PPT 适配器
        :param window_handle: 嵌入容器原生句柄
        :param command_args: OPEN 指令参数
        :param previous_adapter: 切换前的旧适配器
        :param previous_source_type: 旧源类型
        :param previous_source_id: 旧源 ID
        :return: None
        """
        token = next(self._ppt_open_token_counter)
        entry = _PendingPptOpen(
            token=token,
            adapter=adapter,
            command_args=dict(command_args),
            previous_adapter=previous_adapter,
            previous_source_type=previous_source_type,
            previous_source_id=previous_source_id,
            previous_adapter_kind=previous_adapter_kind,
        )
        self._pending_ppt_opens[window_id] = entry
        self._update_session_state(window_id, "loading")

        def report_open_finished(error: BaseException | None) -> None:
            # 可能在 COM 工作线程触发；经 Qt 信号回到主线程收尾。
            self.sig_ppt_open_finished.emit(window_id, token, error)

        try:
            adapter.open_async(
                uri=str(command_args.get("uri", "")),
                window_handle=window_handle,
                autoplay=bool(command_args.get("autoplay", True)),
                start_slide=int(command_args.get("target_slide") or 0),
                on_finished=report_open_finished,
            )
        except BaseException:
            # 同步抛错说明回调未被消费，移除在途记录后交由上层恢复旧适配器。
            current = self._pending_ppt_opens.get(window_id)
            if current is not None and current.token == token:
                self._pending_ppt_opens.pop(window_id, None)
            raise

    def _on_ppt_open_finished(
        self,
        window_id: int,
        token: int,
        error: object,
    ) -> None:
        """
        PPT 后台打开完成的主线程收尾。
        :param window_id: 窗口编号
        :param token: 在途请求 token
        :param error: None 表示成功，否则为异常对象
        :return: None
        """
        entry = self._pending_ppt_opens.get(window_id)
        if entry is None or entry.token != token:
            logger.warning(
                "窗口 %d 收到过期 PPT 打开完成通知（token=%d），忽略",
                window_id,
                token,
            )
            return
        self._pending_ppt_opens.pop(window_id, None)

        if entry.superseded:
            self._dispose_superseded_ppt_open(window_id, entry)
        elif error is not None:
            self._finish_ppt_open_failure(window_id, entry, error)
        else:
            self._finish_ppt_open_success(window_id, entry)

        deferred_commands = entry.deferred
        entry.deferred = []
        for deferred_command, deferred_args in deferred_commands:
            self._execute_command_on_main_thread(
                window_id, deferred_command, deferred_args
            )

    def _finish_ppt_open_success(self, window_id: int, entry: _PendingPptOpen) -> None:
        """
        打开成功：注册适配器、展示嵌入容器、调度旧适配器关闭。
        :param window_id: 窗口编号
        :param entry: 在途打开记录
        :return: None
        """
        command_args = entry.command_args
        source_id = int(command_args.get("source_id") or 0)
        self._adapters[window_id] = entry.adapter
        self._adapter_source_types[window_id] = "ppt"
        self._adapter_kinds[window_id] = "powerpoint"
        if source_id > 0:
            self._adapter_source_ids[window_id] = source_id
        self._show_ppt_container(window_id)
        # 与同步打开路径保持一致：成功后应用音量与静音设置
        try:
            entry.adapter.set_volume(int(command_args.get("volume", 100)))
            entry.adapter.set_mute(bool(command_args.get("muted", False)))
        except Exception as audio_error:
            logger.debug("窗口 %d 应用 PPT 音量/静音失败：%s", window_id, audio_error)
        if bool(command_args.get("autoplay", True)):
            self._update_session_state(window_id, "playing")
        if entry.previous_adapter is not None:
            self._schedule_close_detached_adapter(
                window_id,
                entry.previous_adapter,
                entry.previous_source_type,
                entry.previous_source_id,
                restore_window=False,
                reheat=True,
            )
        self._cleanup_temporary_source(command_args)
        logger.info("窗口 %d PPT 后台打开完成", window_id)

    def _finish_ppt_open_failure(
        self,
        window_id: int,
        entry: _PendingPptOpen,
        error: object,
    ) -> None:
        """
        打开失败：释放新适配器并恢复旧内容或黑屏。
        :param window_id: 窗口编号
        :param entry: 在途打开记录
        :param error: 失败原因
        :return: None
        """
        self._close_adapter_quietly(window_id, entry.adapter)
        self._restore_previous_adapter(
            window_id,
            entry.previous_adapter,
            entry.previous_source_type,
            entry.previous_source_id,
            entry.previous_adapter_kind,
        )
        if entry.previous_adapter is None:
            self._restore_player_window_to_black(window_id)
        self._update_session_error(window_id, str(error))

    def _dispose_superseded_ppt_open(
        self, window_id: int, entry: _PendingPptOpen
    ) -> None:
        """
        在途打开已被新指令取代：静默释放新旧适配器资源。
        :param window_id: 窗口编号
        :param entry: 在途打开记录
        :return: None
        """
        if not entry.adapter_disposed:
            entry.adapter_disposed = True
            self._close_adapter_quietly(window_id, entry.adapter)
        if entry.previous_adapter is not None:
            self._schedule_close_detached_adapter(
                window_id,
                entry.previous_adapter,
                entry.previous_source_type,
                entry.previous_source_id,
                restore_window=False,
                reheat=True,
            )
        logger.info("窗口 %d 在途 PPT 打开已被取代，资源已调度释放", window_id)

    def _close_adapter_quietly(self, window_id: int, adapter: object | None) -> None:
        """
        尽力关闭适配器并吞掉异常。
        :param window_id: 窗口编号（仅用于日志）
        :param adapter: 待关闭适配器
        :return: None
        """
        if adapter is None:
            return
        try:
            adapter.close()
        except Exception as close_error:
            logger.debug("窗口 %d 释放 PPT 适配器异常：%s", window_id, close_error)

    def _defer_command_during_ppt_open(
        self,
        window_id: int,
        command: str,
        command_args: dict[str, object],
    ) -> bool:
        """
        窗口存在在途 PPT 打开时，把后续指令排入待重放队列。
        后到的 OPEN 会取代在途打开：完成后直接释放在途适配器再执行新 OPEN。
        :param window_id: 窗口编号
        :param command: 播放器指令
        :param command_args: 指令参数
        :return: True 表示指令已暂存，调用方不应继续分发
        """
        entry = self._pending_ppt_opens.get(window_id)
        if entry is None:
            return False
        from scp_cv.apps.playback.models import PlaybackCommand

        terminal_commands = (
            PlaybackCommand.OPEN,
            PlaybackCommand.CLOSE,
            PlaybackCommand.RESET_PPT,
        )
        if command in terminal_commands:
            # 终止/替换类指令取代在途打开：完成后不得把会话写成 playing，
            # 否则重放的 CLOSE 会因"状态已被覆盖"跳过清空，导致会话复活。
            # 它之前排队的普通指令也随之失效，压缩队列只保留本条，
            # 确保关键指令永远不会被积压上限淘汰。
            entry.superseded = True
            if entry.deferred:
                logger.info(
                    "窗口 %d 排队指令被 %s 取代，丢弃 %d 条积压指令",
                    window_id,
                    command,
                    len(entry.deferred),
                )
            entry.deferred = [(command, dict(command_args))]
            logger.info(
                "窗口 %d PPT 打开进行中，指令 %s 已排队等待完成", window_id, command
            )
            return True

        entry.deferred.append((command, dict(command_args)))
        if len(entry.deferred) > _MAX_DEFERRED_COMMANDS:
            # 只淘汰普通控制指令；终止/替换类经上方压缩后唯一且位于队首
            for queued_index, (queued_command, _queued_args) in enumerate(entry.deferred):
                if queued_command not in terminal_commands:
                    dropped_command, _dropped_args = entry.deferred.pop(queued_index)
                    logger.warning(
                        "窗口 %d PPT 打开期间指令积压过多，丢弃最早的普通指令：%s",
                        window_id,
                        dropped_command,
                    )
                    break
        logger.info(
            "窗口 %d PPT 打开进行中，指令 %s 已排队等待完成", window_id, command
        )
        return True

    def _abort_pending_ppt_opens(self) -> None:
        """
        全局重置/退出前取消所有在途 PPT 打开。
        在途适配器的 close 立即排入 COM 工作线程（串行在 open 任务之后执行），
        资源释放不依赖 Qt 完成回调——退出阶段事件循环可能已不再派发信号。
        :return: None
        """
        for window_id, entry in self._pending_ppt_opens.items():
            entry.superseded = True
            entry.deferred.clear()
            if not entry.adapter_disposed:
                entry.adapter_disposed = True
                self._close_adapter_quietly(window_id, entry.adapter)
            if entry.previous_adapter is not None:
                self._close_adapter_quietly(window_id, entry.previous_adapter)
                entry.previous_adapter = None
            logger.info("窗口 %d 在途 PPT 打开已标记取消", window_id)


__all__ = ["PptOpenFlowMixin"]
