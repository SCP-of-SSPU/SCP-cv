#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PPT 适配器 PowerPoint COM 会话辅助 mixin。
负责 COM 应用创建、演示文稿打开/关闭、提示级别与重试等底层操作。
@Project : SCP-cv
@File : ppt_com_session.py
@Author : Qintsg
@Date : 2026-06-10
'''
from __future__ import annotations

import time
from collections.abc import Callable
from typing import Optional

_POWERPOINT_OPERATION_RETRIES = 3
_POWERPOINT_RETRY_DELAY_SECONDS = 0.3


class PptComSessionMixin:
    """封装 PowerPoint COM 应用与演示文稿会话的底层辅助逻辑。"""

    def _dispatch_ppt_application(self, win32com_client: object) -> object:
        """
        按候选 ProgID 创建 PPT COM 应用实例。
        :param win32com_client: win32com.client 模块对象
        :return: PPT 应用 COM 对象
        :raises RuntimeError: 所有 ProgID 均不可用时
        """
        last_error: Optional[Exception] = None
        for prog_id in self._com_prog_ids:
            try:
                app = self._run_powerpoint_operation(
                    f"创建 COM 应用 {prog_id}",
                    lambda prog_id=prog_id: win32com_client.DispatchEx(prog_id),
                )
                self._active_com_prog_id = prog_id
                self._logger.info("已创建 %s COM 应用：%s", self._app_label, prog_id)
                return app
            except Exception as dispatch_error:
                last_error = dispatch_error
                self._logger.debug(
                    "%s COM ProgID 不可用：%s，原因：%s",
                    self._app_label,
                    prog_id,
                    dispatch_error,
                )
        supported_prog_ids = ", ".join(self._com_prog_ids)
        raise RuntimeError(
            f"未找到 {self._app_label} COM 自动化对象：{supported_prog_ids}"
        ) from last_error

    def _open_presentation_for_slideshow(self, file_path: str) -> object:
        """
        以只读、不显示编辑窗口的方式打开演示文稿，避免文件锁冲突。
        :param file_path: PPT 文件路径
        :return: Presentation COM 对象
        """
        if self._ppt_app is None:
            raise RuntimeError(f"{self._app_label} COM 应用尚未初始化")
        presentations = self._ppt_app.Presentations

        def open_once() -> object:
            try:
                return presentations.Open(
                    file_path,
                    ReadOnly=True,
                    Untitled=False,
                    WithWindow=False,
                )
            except Exception as keyword_error:
                try:
                    return presentations.Open(file_path, True, False, False)
                except Exception as positional_error:
                    raise RuntimeError(
                        f"{self._app_label} 打开演示文稿失败："
                        f"keyword={keyword_error}; positional={positional_error}"
                    ) from positional_error

        return self._run_powerpoint_operation("打开演示文稿", open_once)

    def _quit_ppt_application_if_idle(self) -> None:
        """
        仅在 PowerPoint 没有其它打开的演示文稿时退出应用。
        PowerPoint 是单实例进程，其它播放窗口或用户文档可能仍在使用。
        :return: None
        """
        if self._ppt_app is None:
            return
        if not self._ppt_application_is_idle():
            self._logger.info(
                "%s 仍有其它演示文稿打开，跳过退出应用", self._app_label
            )
            return
        try:
            self._ppt_app.Quit()
        except Exception:
            pass

    def _ppt_application_is_idle(self) -> bool:
        """
        判断 PowerPoint 应用是否已无打开的演示文稿。
        :return: True 表示可以安全退出；读取失败时按可退出处理
        """
        try:
            return int(self._ppt_app.Presentations.Count) <= 0
        except Exception:
            return True

    def _set_powerpoint_alerts(self, alert_level: int) -> None:
        """
        设置 PPT 应用提示级别，避免关闭只读文件时弹出保存对话框。
        :param alert_level: PowerPoint 的 PpAlertLevel 常量值
        :return: None
        """
        if self._ppt_app is None:
            return
        try:
            self._ppt_app.DisplayAlerts = alert_level
        except Exception:
            pass

    def _mark_presentation_clean(self) -> None:
        """
        将演示文稿标记为已保存，关闭只读文件时不再触发保存提示。
        :return: None
        """
        if self._presentation is None:
            return
        try:
            self._presentation.Saved = True
        except Exception:
            pass

    def _close_presentation_without_save(self) -> None:
        """
        关闭演示文稿时显式选择不保存，避免 PowerPoint 弹出保存对话框。
        :return: None
        """
        if self._presentation is None:
            return
        self._mark_presentation_clean()
        close_method = getattr(self._presentation, "Close", None)
        if close_method is None:
            return
        try:
            close_method(False)
            return
        except TypeError:
            close_method()

    def _run_powerpoint_operation(
        self,
        operation_name: str,
        operation: Callable[[], object],
    ) -> object:
        """
        按固定次数重试 PowerPoint COM 操作，缓解冷启动阶段的临时失败。
        :param operation_name: 日志中的操作名
        :param operation: 待执行的 COM 调用
        :return: COM 调用结果
        :raises RuntimeError: 多次重试后仍失败
        """
        last_error: Exception | None = None
        for attempt in range(1, _POWERPOINT_OPERATION_RETRIES + 1):
            try:
                return operation()
            except Exception as operation_error:
                last_error = operation_error
                if attempt >= _POWERPOINT_OPERATION_RETRIES:
                    break
                self._logger.warning(
                    "%s %s 失败，将重试（%d/%d）：%s",
                    self._app_label,
                    operation_name,
                    attempt,
                    _POWERPOINT_OPERATION_RETRIES,
                    operation_error,
                )
                time.sleep(_POWERPOINT_RETRY_DELAY_SECONDS)
        raise RuntimeError(
            f"{self._app_label} {operation_name} 失败，"
            f"已重试 {_POWERPOINT_OPERATION_RETRIES} 次"
        ) from last_error


__all__ = ["PptComSessionMixin"]
