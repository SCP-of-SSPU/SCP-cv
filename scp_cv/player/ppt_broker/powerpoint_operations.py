#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PowerPoint Broker COM 操作的有限瞬时重试策略。
@Project : SCP-cv
@File : powerpoint_operations.py
@Author : Qintsg
@Date : 2026-07-11
'''
from __future__ import annotations

import logging
import time
from collections.abc import Callable

from scp_cv.player.ppt_broker.com_support import (
    com_error_hresult,
    is_released_com_object_error,
    is_transient_com_error,
)

logger = logging.getLogger(__name__)


class PowerPointOperationRunnerMixin:
    """只重试 RPC 瞬时拒绝，并统一记录 HRESULT 与最终结果。"""

    _retry_delays: tuple[float, ...]

    def _run_operation(
        self,
        operation_name: str,
        callback: Callable[[], object],
    ) -> object:
        delays = (0.0, *self._retry_delays)
        for attempt, delay in enumerate(delays, start=1):
            if delay:
                time.sleep(delay)
            try:
                return callback()
            except Exception as operation_error:
                if attempt >= len(delays) or not is_transient_com_error(
                    operation_error
                ):
                    hresult = com_error_hresult(operation_error)
                    hresult_label = (
                        f"0x{hresult:08X}" if hresult is not None else "unknown"
                    )
                    if is_released_com_object_error(operation_error):
                        logger.debug(
                            "PowerPoint COM 对象已释放：operation=%s, "
                            "hresult=%s, error=%s",
                            operation_name,
                            hresult_label,
                            operation_error,
                        )
                    else:
                        logger.error(
                            "PowerPoint COM 操作失败且不重试：operation=%s, "
                            "hresult=%s, error=%s",
                            operation_name,
                            hresult_label,
                            operation_error,
                        )
                    raise
                hresult = com_error_hresult(operation_error)
                hresult_label = (
                    f"0x{hresult:08X}" if hresult is not None else "unknown"
                )
                logger.warning(
                    "%s 遭遇瞬时 COM 拒绝，将重试（%d/%d）："
                    "hresult=%s, error=%s",
                    operation_name,
                    attempt,
                    len(delays),
                    hresult_label,
                    operation_error,
                )
        raise RuntimeError(f"{operation_name} 未执行")


__all__ = ["PowerPointOperationRunnerMixin"]
