#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PowerPoint/WPS 文件级预热复用 mixin。
@Project : SCP-cv
@File : ppt_preheat.py
@Author : Qintsg
@Date : 2026-05-31
'''
from __future__ import annotations

import os

from scp_cv.player.preheat_types import PreheatedPptApplication


class PptPreheatMixin:
    """为 PowerPoint/WPS 适配器提供预热应用和预打开 Presentation 复用能力。"""

    def _take_preheated_application(self) -> PreheatedPptApplication | None:
        """
        从统一预热池取出已启动的 PowerPoint/WPS 应用。
        :return: 预热应用或 None
        """
        if not self._preheat_enabled or self._preheat_pool is None:
            return None
        take_application = getattr(self._preheat_pool, "take_ppt_application", None)
        if not callable(take_application):
            return None
        backend = "wps" if self._adapter_name == "ppt-wps" else "powerpoint"
        return take_application(backend, self._source_id, self._file_path)

    def _take_preheated_presentation(self, file_path: str) -> object | None:
        """
        取出文件级预热时已打开的 Presentation。
        :param file_path: 当前 PPT 文件路径
        :return: Presentation COM 对象或 None
        """
        item = self._preheated_app
        if item is None or not item.presentation:
            return None
        if item.uri and os.path.normcase(os.path.abspath(item.uri)) != os.path.normcase(os.path.abspath(file_path)):
            return None
        presentation = item.presentation
        item.presentation = None
        self._logger.info("已复用文件级预热 %s Presentation：source_id=%d", self._app_label, item.source_id)
        return presentation

    def _return_preheated_application(self) -> bool:
        """
        将借出的 PowerPoint/WPS 应用归还预热池。
        :return: True 表示已归还
        """
        if self._preheated_app is None or self._preheat_pool is None:
            return False
        return_application = getattr(self._preheat_pool, "return_ppt_application", None)
        if not callable(return_application):
            return False
        return_application(self._preheated_app)
        return True


__all__ = ["PptPreheatMixin"]
