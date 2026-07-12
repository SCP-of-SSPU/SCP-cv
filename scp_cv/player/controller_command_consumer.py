#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PlayerController 的持久化命令消费者深模块。

集中维护消费者身份、崩溃恢复、租约续期、历史清理和窗口命令原子认领；
轮询线程及 Qt 主线程分发仍由 PlayerController 统一编排。
@Project : SCP-cv
@File : controller_command_consumer.py
@Author : Qintsg
@Date : 2026-07-12
'''
from __future__ import annotations

import logging
import time
import uuid

logger = logging.getLogger(__name__)
_COMMAND_PRUNE_INTERVAL_SECONDS = 60 * 60
_COMMAND_CONSUMER_MAINTENANCE_INTERVAL_SECONDS = 5.0


class PlayerCommandConsumerMixin:
    """封装持久化命令消费者的身份、维护和窗口命令认领。"""

    def _initialize_command_consumer_runtime(self) -> None:
        """初始化当前播放器进程的命令消费者身份与维护时钟。"""
        from scp_cv.services.command_queue import CommandConsumerIdentity

        self._command_consumer_identity = CommandConsumerIdentity.current(
            f"player-{uuid.uuid4().hex}"
        )
        self._command_consumer_id = self._command_consumer_identity.consumer_id
        self._command_consumer_active = False
        self._dispatching_command_id = 0
        self._next_command_prune_at = (
            time.monotonic() + _COMMAND_PRUNE_INTERVAL_SECONDS
        )
        self._next_command_consumer_maintenance_at = (
            time.monotonic() + _COMMAND_CONSUMER_MAINTENANCE_INTERVAL_SECONDS
        )

    def _recover_abandoned_commands(self) -> None:
        """播放器启动时终结旧消费者遗留的执行记录，避免盲目重放。"""
        from scp_cv.services.command_queue import prune

        recovered = self._recover_registered_command_targets()
        pruned = prune()
        self._next_command_prune_at = (
            time.monotonic() + _COMMAND_PRUNE_INTERVAL_SECONDS
        )
        self._next_command_consumer_maintenance_at = (
            time.monotonic() + _COMMAND_CONSUMER_MAINTENANCE_INTERVAL_SECONDS
        )
        if recovered or pruned:
            logger.info(
                "播放器命令队列已恢复：abandoned=%d, pruned=%d",
                recovered,
                pruned,
            )

    def _recover_registered_command_targets(self) -> int:
        """恢复当前播放器负责目标中已崩溃或租约过期的执行记录。"""
        from scp_cv.apps.playback.models import ControlCommandTarget
        from scp_cv.services.command_queue import recover_abandoned, target_for_window

        recovered = sum(
            recover_abandoned(
                target_for_window(window_id),
                self._command_consumer_identity,
            )
            for window_id in self.registered_window_ids
        )
        if self._enable_background_audio:
            recovered += recover_abandoned(
                ControlCommandTarget.BACKGROUND_AUDIO,
                self._command_consumer_identity,
            )
        return recovered

    def _maintain_command_consumer_if_due(self) -> None:
        """周期续约自身记录，并回收启动后才失联的旧消费者。"""
        now = time.monotonic()
        if now < self._next_command_consumer_maintenance_at:
            return
        self._next_command_consumer_maintenance_at = (
            now + _COMMAND_CONSUMER_MAINTENANCE_INTERVAL_SECONDS
        )
        from scp_cv.services.command_queue import renew_consumer_lease

        renewed = renew_consumer_lease(self._command_consumer_identity)
        recovered = self._recover_registered_command_targets()
        if recovered:
            logger.warning(
                "播放器命令消费者维护已恢复遗留记录：renewed=%d, recovered=%d",
                renewed,
                recovered,
            )

    def _prune_command_history_if_due(self) -> None:
        """常驻轮询期间每小时至多清理一次七天前的终态命令。"""
        now = time.monotonic()
        if now < self._next_command_prune_at:
            return
        self._next_command_prune_at = now + _COMMAND_PRUNE_INTERVAL_SECONDS
        from scp_cv.services.command_queue import prune

        pruned = prune()
        if pruned:
            logger.info("播放器命令队列定时清理完成：pruned=%d", pruned)

    def _check_and_dispatch_command(self, window_id: int) -> None:
        """
        读取指定窗口 DB 中的待执行指令，通过信号发射到 Qt 主线程。
        :param window_id: 窗口编号
        """
        from scp_cv.apps.playback.models import ControlCommandTarget
        from scp_cv.services.command_queue import claim_next

        try:
            target = ControlCommandTarget(f"window:{window_id}")
        except ValueError:
            return
        queued = claim_next(target, self._command_consumer_id)
        if queued is None:
            return
        self._command_consumer_active = True

        logger.info(
            "窗口 %d 领取指令 id=%d：%s，参数=%s，发射到主线程",
            window_id,
            queued.pk,
            queued.command,
            queued.arguments,
        )

        self.sig_dispatch_queued_command.emit(
            int(queued.pk),
            window_id,
            queued.command,
            dict(queued.arguments or {}),
        )


__all__ = ["PlayerCommandConsumerMixin"]
