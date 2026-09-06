#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PPT 适配器导航与状态读取 mixin。
包含放映控制（play/pause/stop）、翻页/动画导航、页内媒体控制
以及放映状态采集；公开方法经 _submit_com_command 路由到 COM 工作线程。
@Project : SCP-cv
@File : ppt_navigation.py
@Author : Qintsg
@Date : 2026-06-10
'''
from __future__ import annotations

from typing import Optional

from scp_cv.player.adapters.base import AdapterState
from scp_cv.player.adapters.ppt_constants import (
    PP_SLIDE_SHOW_DONE as _PP_SLIDE_SHOW_DONE,
    PP_SLIDE_SHOW_PAUSED as _PP_SLIDE_SHOW_PAUSED,
    PP_SLIDE_SHOW_RUNNING as _PP_SLIDE_SHOW_RUNNING,
)
from scp_cv.player.adapters.ppt_media import control_slide_media
from scp_cv.player.adapters.ppt_window import close_embedded_slideshow_window


class PptNavigationMixin:
    """PPT 适配器的放映控制、导航和状态读取逻辑。"""

    # ═══════════════════ 播放控制 ═══════════════════

    def play(self) -> None:
        """恢复放映（从暂停状态）。"""
        self._submit_com_command("恢复放映", self._play_on_com_thread)

    def _play_on_com_thread(self) -> None:
        """
        在 COM 线程执行恢复放映。
        :return: None
        """
        with self._com_lock:
            if self._slideshow_view is None and self._presentation is not None:
                self._start_slideshow(self._last_slide_index)
                return
            if self._slideshow_view is None:
                raise RuntimeError("PowerPoint 放映未运行，无法恢复播放")
            if self._slideshow_view is not None and self._is_paused:
                try:
                    self._slideshow_view.State = _PP_SLIDE_SHOW_RUNNING
                    self._is_paused = False
                except Exception as resume_error:
                    self._logger.warning("恢复放映失败：%s", resume_error)
                    raise RuntimeError(f"恢复 PowerPoint 放映失败：{resume_error}") from resume_error

    def pause(self) -> None:
        """暂停放映。"""
        self._submit_com_command("暂停放映", self._pause_on_com_thread)

    def _pause_on_com_thread(self) -> None:
        """
        在 COM 线程执行暂停放映。
        :return: None
        """
        with self._com_lock:
            if self._slideshow_view is None:
                raise RuntimeError("PowerPoint 放映未运行，无法暂停")
            if self._slideshow_view is not None and not self._is_paused:
                try:
                    self._slideshow_view.State = _PP_SLIDE_SHOW_PAUSED
                    self._is_paused = True
                except Exception as pause_error:
                    self._logger.warning("暂停放映失败：%s", pause_error)
                    raise RuntimeError(f"暂停 PowerPoint 放映失败：{pause_error}") from pause_error

    def stop(self) -> None:
        """停止放映（退出放映模式，但不关闭文件）。"""
        self._submit_com_command("停止放映", self._stop_on_com_thread)

    def _stop_on_com_thread(self) -> None:
        """
        在 COM 线程执行停止放映并关闭嵌入子窗口。
        :return: None
        """
        with self._com_lock:
            if self._slideshow_view is not None:
                try:
                    self._last_slide_index = int(
                        self._slideshow_view.CurrentShowPosition
                        or self._last_slide_index
                    )
                    self._mark_presentation_clean()
                    self._slideshow_view.Exit()
                except Exception as stop_error:
                    self._logger.warning("停止 PowerPoint 放映失败：%s", stop_error)
                    raise RuntimeError(f"停止 PowerPoint 放映失败：{stop_error}") from stop_error
                if self._ppt_hwnd != 0:
                    try:
                        close_embedded_slideshow_window(
                            self._ppt_hwnd, self._embed_owner_token
                        )
                    except Exception:
                        pass
                    self._ppt_hwnd = 0
                self._slideshow_view = None
                self._slideshow_window = None
                self._is_paused = False

    # ═══════════════════ 幻灯片导航 ═══════════════════

    def next_item(self) -> None:
        """下一动画或下一页。"""
        self._submit_com_command("下一动画/页", self._next_item_on_com_thread)

    def _next_item_on_com_thread(self) -> None:
        """
        在 COM 线程执行下一动画/页。
        :return: None
        """
        with self._com_lock:
            if self._slideshow_view is None or self._slideshow_is_finished():
                raise RuntimeError("PowerPoint 放映未运行或已结束")
            try:
                self._goto_next_click()
                self._last_slide_index = self._current_show_position()
            except Exception as nav_error:
                self._logger.warning("PPT 下一动画/页失败：%s", nav_error)
                raise RuntimeError(f"PPT 下一动画/页失败：{nav_error}") from nav_error

    def prev_item(self) -> None:
        """上一动画或上一页。"""
        self._submit_com_command("上一动画/页", self._prev_item_on_com_thread)

    def _prev_item_on_com_thread(self) -> None:
        """
        在 COM 线程执行上一动画/页。
        :return: None
        """
        with self._com_lock:
            if self._slideshow_view is None or self._slideshow_is_finished():
                raise RuntimeError("PowerPoint 放映未运行或已结束")
            try:
                self._goto_previous_click()
                self._last_slide_index = self._current_show_position()
            except Exception as nav_error:
                self._logger.warning("PPT 上一动画/页失败：%s", nav_error)
                raise RuntimeError(f"PPT 上一动画/页失败：{nav_error}") from nav_error

    def _goto_next_click(self) -> None:
        """
        优先推进到下一动画点击，接口不可用时回退到下一页。
        :return: None
        """
        if self._slideshow_view is None:
            return
        current_position = self._current_show_position()
        goto_next_click = getattr(self._slideshow_view, "GotoNextClick", None)
        if callable(goto_next_click):
            has_next_click = self._has_remaining_next_click()
            if has_next_click is not False:
                try:
                    goto_next_click()
                    return
                except Exception as click_error:
                    self._logger.debug("PPT 下一动画接口不可用，回退到下一页：%s", click_error)
        if self._total_slides > 0 and current_position >= self._total_slides:
            self._last_slide_index = self._total_slides
            self._logger.info("PPT 已在最后一页，忽略继续下一页指令")
            return
        self._slideshow_view.Next()

    def _goto_previous_click(self) -> None:
        """
        优先回退到上一动画点击，接口不可用时回退到上一页。
        :return: None
        """
        if self._slideshow_view is None:
            return
        current_position = self._current_show_position()
        goto_previous_click = getattr(self._slideshow_view, "GotoPreClick", None)
        if callable(goto_previous_click):
            has_previous_click = self._has_previous_click()
            if has_previous_click is not False:
                try:
                    goto_previous_click()
                    return
                except Exception as click_error:
                    self._logger.debug("PPT 上一动画接口不可用，回退到上一页：%s", click_error)
        if current_position <= 1:
            self._last_slide_index = 1
            return
        self._slideshow_view.Previous()

    def _has_remaining_next_click(self) -> Optional[bool]:
        """
        判断当前页是否仍有可推进的动画点击。
        :return: True/False 表示已确认；None 表示后端不支持读取
        """
        click_count = self._read_slideshow_click_value("GetClickCount")
        click_index = self._read_slideshow_click_value("GetClickIndex")
        if click_count is None or click_index is None:
            return None
        return click_index < click_count

    def _has_previous_click(self) -> Optional[bool]:
        """
        判断当前页是否有可回退的动画点击。
        :return: True/False 表示已确认；None 表示后端不支持读取
        """
        click_index = self._read_slideshow_click_value("GetClickIndex")
        if click_index is None:
            return None
        return click_index > 0

    def _read_slideshow_click_value(self, method_name: str) -> Optional[int]:
        """
        读取 SlideShowView 的动画点击计数。
        :param method_name: COM 方法名
        :return: 计数值；不可读取时返回 None
        """
        if self._slideshow_view is None:
            return None
        method = getattr(self._slideshow_view, method_name, None)
        if not callable(method):
            return None
        try:
            return int(method())
        except Exception:
            return None

    def goto_item(self, index: int) -> None:
        """
        跳转到指定页。
        :param index: 页码（1-based）
        """
        if index < 1 or index > self._total_slides:
            raise ValueError(f"无效页码 {index}（总计 {self._total_slides} 页）")
        self._submit_com_command(
            f"跳转第 {index} 页",
            lambda: self._goto_item_on_com_thread(index),
        )

    def _goto_item_on_com_thread(self, index: int) -> None:
        """
        在 COM 线程执行跳页。
        :param index: 目标页码（1-based）
        :return: None
        """
        with self._com_lock:
            if self._slideshow_view is None or self._slideshow_is_finished():
                raise RuntimeError("PowerPoint 放映未运行或已结束")
            try:
                self._goto_slide(index)
                self._last_slide_index = index
            except Exception as goto_error:
                self._logger.warning("PPT 跳转到第 %d 页失败：%s", index, goto_error)
                raise RuntimeError(f"PPT 跳转到第 {index} 页失败：{goto_error}") from goto_error

    def _goto_slide(self, index: int) -> None:
        """
        跳转到指定页，兼容 PowerPoint 不同版本的 COM 参数签名。
        :param index: 目标页码，1-based
        :return: None
        """
        if self._slideshow_view is None:
            return
        try:
            self._slideshow_view.GotoSlide(index)
        except TypeError:
            self._slideshow_view.GotoSlide(index, False)

    def _slideshow_is_finished(self) -> bool:
        """
        判断当前放映是否已经结束或 COM 视图已失效。
        :return: True 表示不应再向 PowerPoint 下发翻页指令
        """
        if self._slideshow_view is None:
            return True
        try:
            return int(self._slideshow_view.State) == _PP_SLIDE_SHOW_DONE
        except Exception:
            return self._read_current_show_position() is None

    def _current_show_position(self) -> int:
        """
        安全读取当前页码，失败时使用最近一次成功读取的页码。
        :return: 当前页码（从 1 开始）
        """
        current_position = self._read_current_show_position()
        if current_position is None:
            return self._last_slide_index
        self._last_slide_index = current_position
        return current_position

    def _read_current_show_position(self) -> Optional[int]:
        """
        读取当前页码，读取失败时返回 None 而不修改内部状态。
        :return: 当前页码；COM 视图不可读时返回 None
        """
        if self._slideshow_view is None:
            return None
        try:
            current_position = int(self._slideshow_view.CurrentShowPosition or 0)
        except Exception:
            return None
        return current_position if current_position > 0 else None

    def control_media(self, media_id: str, action: str, media_index: int = 0) -> None:
        """
        控制当前页中的音视频媒体对象。
        :param media_id: 媒体对象标识，可为 PowerPoint shape id
        :param action: 控制动作（play / pause / stop）
        :param media_index: 当前页媒体序号（从 1 开始）
        :return: None
        """
        self._submit_com_command(
            f"页内媒体 {action}",
            lambda: self._control_media_on_com_thread(media_id, action, media_index),
        )

    def _control_media_on_com_thread(
        self, media_id: str, action: str, media_index: int
    ) -> None:
        """
        在 COM 线程执行页内媒体控制。
        :param media_id: 媒体对象标识
        :param action: 控制动作
        :param media_index: 当前页媒体序号
        :return: None
        """
        with self._com_lock:
            control_slide_media(
                self._slideshow_view,
                self._presentation,
                self._logger,
                media_id,
                action,
                media_index,
            )

    # ═══════════════════ 状态采集 ═══════════════════

    def _collect_state_via_com(self) -> AdapterState:
        """
        通过 COM 读取 PPT 放映状态快照（必须在 COM 线程调用）。
        :return: 包含当前页码和总页数的状态快照
        """
        current_slide = 0
        playback_state = "idle"

        with self._com_lock:
            if self._slideshow_view is not None:
                try:
                    slideshow_state = int(self._slideshow_view.State)
                    if slideshow_state == _PP_SLIDE_SHOW_DONE:
                        current_slide = self._last_slide_index or self._total_slides
                        playback_state = "stopped"
                    else:
                        current_slide = self._current_show_position()

                        if slideshow_state == _PP_SLIDE_SHOW_RUNNING:
                            playback_state = "playing"
                        elif slideshow_state == _PP_SLIDE_SHOW_PAUSED:
                            playback_state = "paused"
                        else:
                            playback_state = "playing"
                except Exception as state_error:
                    self._logger.debug("读取 PPT 放映状态失败：%s", state_error)
                    current_position = self._read_current_show_position()
                    if current_position is not None:
                        current_slide = current_position
                        self._last_slide_index = current_position
                        playback_state = "playing" if not self._is_paused else "paused"
                    else:
                        self._slideshow_view = None
                        self._slideshow_window = None
                        current_slide = (
                            self._last_slide_index if self._total_slides else 0
                        )
                        playback_state = (
                            "stopped" if self._presentation is not None else "idle"
                        )
            elif self._presentation is not None:
                # 文件已打开但未在放映
                playback_state = "stopped"
                current_slide = self._last_slide_index if self._total_slides else 0

        return AdapterState(
            playback_state=playback_state,
            current_slide=current_slide,
            total_slides=self._total_slides,
        )


__all__ = ["PptNavigationMixin"]
