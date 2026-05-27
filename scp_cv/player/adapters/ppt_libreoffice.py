#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
LibreOffice Impress PPT 源适配器，通过 UNO 控制窗口化幻灯片放映。
@Project : SCP-cv
@File : ppt_libreoffice.py
@Author : Qintsg
@Date : 2026-05-26
'''
from __future__ import annotations

import os
import threading
import time
from typing import Optional

from scp_cv import libreoffice as lo_runtime
from scp_cv.player.adapters.ppt_libreoffice_bridge import LibreOfficeBridgeClient
from scp_cv.player.adapters.ppt_libreoffice_media import control_libreoffice_media
from scp_cv.player.adapters import ppt_libreoffice_window as lo_window
from scp_cv.player.adapters.base import AdapterState, SourceAdapter


class LibreOfficePptSourceAdapter(SourceAdapter):
    """
    LibreOffice Impress 放映适配器。

    每个适配器实例启动独立 LibreOffice profile 与 UNO pipe，避免四窗口同时播放时
    共享 LibreOffice 主进程导致窗口、状态或媒体互相串扰。
    """

    def __init__(self) -> None:
        """
        初始化 LibreOffice PPT 适配器。
        :return: None
        """
        super().__init__(adapter_name="ppt-libreoffice")
        self._session: Optional[lo_runtime.LibreOfficeSession] = None
        self._document: Optional[object] = None
        self._presentation: Optional[object] = None
        self._controller: Optional[object] = None
        self._total_slides: int = 0
        self._file_path: str = ""
        self._window_handle: int = 0
        self._lo_hwnd: int = 0
        self._bridge: Optional[LibreOfficeBridgeClient] = None
        self._bridge_process_id: int = 0
        self._is_paused: bool = False
        self._last_slide_index: int = 1
        self._lock = threading.Lock()

    def open(self, uri: str, window_handle: int, autoplay: bool = True) -> None:
        """
        打开 PPT 文件并准备 LibreOffice 放映。
        :param uri: PPT 文件绝对路径
        :param window_handle: PySide 播放器容器 HWND
        :param autoplay: 是否立即开始放映
        :return: None
        """
        if not os.path.isfile(uri):
            raise FileNotFoundError(f"PPT 文件不存在：{uri}")

        with self._lock:
            self._file_path = uri
            self._window_handle = window_handle
            existing_hwnds = lo_window.snapshot_libreoffice_hwnds(self._logger)
            self._bridge = LibreOfficeBridgeClient(self._logger)
            state = self._bridge.open(uri, autoplay)
            self._apply_bridge_state(state)
            if autoplay:
                self._embed_bridge_slideshow(existing_hwnds)

        self._mark_open()
        self._logger.info("LibreOffice PPT 已打开：%s（%d 页）", uri, self._total_slides)

    def close(self) -> None:
        """
        关闭 LibreOffice 放映、文档和隔离进程。
        :return: None
        """
        with self._lock:
            self._close_resources()
        self._mark_closed()
        self._logger.info("LibreOffice PPT 已关闭")

    def play(self) -> None:
        """
        开始或恢复 LibreOffice 放映。
        :return: None
        """
        with self._lock:
            if self._bridge is not None:
                existing_hwnds = lo_window.snapshot_libreoffice_hwnds(
                    self._logger,
                    process_id=self._bridge_process_id or None,
                )
                self._apply_bridge_state(self._bridge.request("play"))
                if self._lo_hwnd == 0:
                    self._embed_bridge_slideshow(existing_hwnds)
                return
            if self._controller is None and self._presentation is not None:
                self._start_slideshow(self._last_slide_index)
                return
            if self._controller is not None and self._is_paused:
                try:
                    self._controller.resume()
                    self._is_paused = False
                except Exception as resume_error:
                    self._logger.warning("LibreOffice PPT 恢复放映失败：%s", resume_error)

    def pause(self) -> None:
        """
        暂停 LibreOffice 放映。
        :return: None
        """
        with self._lock:
            if self._bridge is not None:
                self._apply_bridge_state(self._bridge.request("pause"))
                return
            if self._controller is None or self._is_paused:
                return
            try:
                self._controller.pause()
                self._is_paused = True
            except Exception as pause_error:
                self._logger.warning("LibreOffice PPT 暂停放映失败：%s", pause_error)

    def stop(self) -> None:
        """
        停止放映但保留已打开文档，后续 play 可从最近页恢复。
        :return: None
        """
        with self._lock:
            if self._bridge is not None:
                self._apply_bridge_state(self._bridge.request("stop"))
                self._detach_bridge_hwnd()
                return
            if self._controller is not None:
                self._last_slide_index = self._current_slide_index()
            self._end_presentation()
            self._controller = None
            self._is_paused = False

    def next_item(self) -> None:
        """
        推进到下一动画效果；无效果时由 LibreOffice 推进到下一页。
        :return: None
        """
        with self._lock:
            if self._bridge is not None:
                self._apply_bridge_state(self._bridge.request("next"))
                return
            if self._controller is None or not self._presentation_is_running():
                return
            try:
                self._controller.gotoNextEffect()
                self._last_slide_index = self._current_slide_index()
            except Exception as nav_error:
                self._logger.warning("LibreOffice PPT 下一动画/页失败：%s", nav_error)

    def prev_item(self) -> None:
        """
        回退到上一动画效果；无效果时由 LibreOffice 回退到上一页。
        :return: None
        """
        with self._lock:
            if self._bridge is not None:
                self._apply_bridge_state(self._bridge.request("prev"))
                return
            if self._controller is None or not self._presentation_is_running():
                return
            try:
                self._controller.gotoPreviousEffect()
                self._last_slide_index = self._current_slide_index()
            except Exception as nav_error:
                self._logger.warning("LibreOffice PPT 上一动画/页失败：%s", nav_error)

    def goto_item(self, index: int) -> None:
        """
        跳转到指定页。
        :param index: 目标页码，1-based
        :return: None
        """
        if index < 1 or index > self._total_slides:
            self._logger.warning("无效页码 %d（总计 %d 页）", index, self._total_slides)
            return
        with self._lock:
            if self._bridge is not None:
                self._apply_bridge_state(self._bridge.request("goto", {"index": index}))
                return
            if self._controller is None or not self._presentation_is_running():
                return
            try:
                self._controller.gotoSlideIndex(index - 1)
                self._last_slide_index = index
            except Exception as goto_error:
                self._logger.warning("LibreOffice PPT 跳转到第 %d 页失败：%s", index, goto_error)

    def control_media(self, media_id: str, action: str, media_index: int = 0) -> None:
        """
        控制当前页媒体对象。
        :param media_id: 媒体对象标识；LibreOffice UNO 暂不提供等价 shape 播放器
        :param action: 控制动作（play / pause / stop）
        :param media_index: 当前页媒体序号
        :return: None
        """
        with self._lock:
            if self._bridge is not None:
                self._apply_bridge_state(
                    self._bridge.request(
                        "control_media",
                        {"media_id": media_id, "action": action, "media_index": media_index},
                    )
                )
                return
            if self._controller is None:
                return
            control_libreoffice_media(
                self._controller,
                self._document,
                self._logger,
                media_id,
                action,
                media_index,
                self._current_slide_index(),
            )
            normalized_action = action.lower().strip()
            if normalized_action == "pause":
                self._is_paused = True
            elif normalized_action == "play":
                self._is_paused = False

    def get_state(self) -> AdapterState:
        """
        获取 LibreOffice PPT 放映状态。
        :return: AdapterState 状态快照
        """
        with self._lock:
            if self._bridge is not None:
                try:
                    return self._state_from_bridge_payload(self._bridge.request("state"))
                except Exception as state_error:
                    return AdapterState(playback_state="error", error_message=str(state_error))
            if self._controller is not None and self._presentation_is_running():
                current_slide = self._current_slide_index()
                playback_state = "paused" if self._controller_is_paused() else "playing"
            elif self._document is not None:
                current_slide = self._last_slide_index if self._total_slides else 0
                playback_state = "stopped"
            else:
                current_slide = 0
                playback_state = "idle"
            return AdapterState(
                playback_state=playback_state,
                current_slide=current_slide,
                total_slides=self._total_slides,
            )

    def _configure_presentation(self) -> None:
        """
        配置 Impress 放映为窗口化、支持动画且避免常驻置顶。
        :return: None
        """
        if self._presentation is None:
            return
        for property_name, value in (
            ("AllowAnimations", True),
            ("IsFullScreen", False),
            ("IsAlwaysOnTop", False),
            ("IsEndless", False),
            ("IsMouseVisible", False),
            ("StartWithNavigator", False),
        ):
            try:
                setattr(self._presentation, property_name, value)
            except Exception:
                self._logger.debug("LibreOffice Presentation.%s 不可设置", property_name)

    def _start_slideshow(self, start_slide: int = 1) -> None:
        """
        启动 Impress 放映并嵌入播放器窗口。
        :param start_slide: 起始页码，1-based
        :return: None
        """
        if self._presentation is None:
            return
        existing_hwnds = lo_window.snapshot_libreoffice_hwnds(self._logger)
        self._invoke_presentation_start()
        self._controller = self._wait_for_controller()
        self._is_paused = False
        if start_slide > 1 and self._controller is not None:
            try:
                self._controller.gotoSlideIndex(start_slide - 1)
            except Exception as goto_error:
                self._logger.warning("LibreOffice PPT 起始页跳转失败：%s", goto_error)

        lo_hwnd = lo_window.find_libreoffice_slideshow_hwnd(
            self._logger,
            existing_hwnds=existing_hwnds,
        )
        if lo_hwnd == 0:
            self._logger.warning("未找到 LibreOffice 放映窗口句柄，无法嵌入")
            return
        self._lo_hwnd = lo_hwnd
        lo_window.embed_slideshow_window(lo_hwnd, self._window_handle)
        container_width, container_height = lo_window.resize_slideshow_window(
            lo_hwnd,
            self._window_handle,
        )
        self._logger.debug(
            "LibreOffice PPT 窗口已调整大小：%dx%d",
            container_width,
            container_height,
        )

    def _invoke_presentation_start(self) -> None:
        """
        兼容 XPresentation 与 XPresentation2 的启动方式。
        :return: None
        """
        if self._presentation is None:
            return
        start_with_arguments = getattr(self._presentation, "startWithArguments", None)
        if start_with_arguments is not None:
            start_with_arguments(())
            return
        self._presentation.start()

    def _wait_for_controller(self) -> object:
        """
        等待 Impress 创建 SlideShowController。
        :return: SlideShowController
        :raises lo_runtime.LibreOfficeError: 超时无法获取时
        """
        if self._presentation is None:
            raise lo_runtime.LibreOfficeError("LibreOffice Presentation 未初始化")
        deadline = time.monotonic() + lo_runtime.configured_libreoffice_timeout()
        last_error: Optional[Exception] = None
        while time.monotonic() < deadline:
            try:
                controller = self._presentation.getController()
                if controller is not None:
                    return controller
            except Exception as controller_error:
                last_error = controller_error
            time.sleep(0.1)
        raise lo_runtime.LibreOfficeError(f"获取 LibreOffice 放映控制器超时：{last_error}")

    def _read_slide_count(self) -> int:
        """
        读取文档页数。
        :return: 幻灯片总数
        """
        if self._document is None:
            return 0
        try:
            return int(self._document.getDrawPages().getCount())  # type: ignore[attr-defined]
        except Exception:
            if self._controller is None:
                return 0
            try:
                return int(self._controller.getSlideCount())
            except Exception:
                return 0

    def _current_slide_index(self) -> int:
        """
        读取当前页码，读取失败时返回最近一次页码。
        :return: 当前页码，1-based
        """
        if self._controller is None:
            return self._last_slide_index if self._total_slides else 0
        try:
            current_slide = int(self._controller.getCurrentSlideIndex()) + 1
        except Exception:
            return self._last_slide_index if self._total_slides else 0
        if current_slide > 0:
            self._last_slide_index = current_slide
        return self._last_slide_index

    def _controller_is_paused(self) -> bool:
        """
        读取控制器暂停状态。
        :return: True 表示暂停
        """
        if self._controller is None:
            return self._is_paused
        try:
            self._is_paused = bool(self._controller.isPaused())
        except Exception:
            pass
        return self._is_paused

    def _presentation_is_running(self) -> bool:
        """
        判断放映是否仍在运行。
        :return: True 表示可继续控制
        """
        if self._presentation is None:
            return False
        is_running = getattr(self._presentation, "isRunning", None)
        if is_running is None:
            return self._controller is not None
        try:
            return bool(is_running())
        except Exception:
            return self._controller is not None

    def _end_presentation(self) -> None:
        """
        结束当前 Impress 放映。
        :return: None
        """
        if self._presentation is None:
            return
        try:
            self._presentation.end()
        except Exception:
            pass
        if self._lo_hwnd != 0:
            try:
                lo_window.detach_slideshow_window(self._lo_hwnd)
            except Exception:
                pass
            self._lo_hwnd = 0

    def _close_resources(self) -> None:
        """
        释放 LibreOffice 文档和进程资源。
        :return: None
        """
        if self._bridge is not None:
            self._detach_bridge_hwnd()
            self._bridge.close()
            self._bridge = None
            self._bridge_process_id = 0
        self._end_presentation()
        if self._document is not None:
            lo_runtime.close_document(self._document)
            self._document = None
        if self._session is not None:
            self._session.close()
            self._session = None
        self._presentation = None
        self._controller = None
        self._total_slides = 0
        self._is_paused = False

    def _embed_bridge_slideshow(self, existing_hwnds: set[int]) -> None:
        """
        查找 bridge 启动的 LibreOffice 放映窗口并嵌入播放器。
        :param existing_hwnds: 启动放映前已存在的候选 HWND
        :return: None
        """
        lo_hwnd = lo_window.find_libreoffice_slideshow_hwnd(
            self._logger,
            existing_hwnds=existing_hwnds,
            process_id=self._bridge_process_id or None,
        )
        if lo_hwnd == 0:
            self._logger.warning("未找到 LibreOffice 放映窗口句柄，无法嵌入")
            return
        self._lo_hwnd = lo_hwnd
        lo_window.embed_slideshow_window(lo_hwnd, self._window_handle)
        container_width, container_height = lo_window.resize_slideshow_window(lo_hwnd, self._window_handle)
        self._logger.debug(
            "LibreOffice PPT 窗口已调整大小：%dx%d",
            container_width,
            container_height,
        )

    def _detach_bridge_hwnd(self) -> None:
        """
        解除 bridge 放映窗口嵌入。
        :return: None
        """
        if self._lo_hwnd == 0:
            return
        try:
            lo_window.detach_slideshow_window(self._lo_hwnd)
        except Exception:
            pass
        self._lo_hwnd = 0

    def _apply_bridge_state(self, payload: dict[str, object]) -> None:
        """
        应用 bridge 返回的状态。
        :param payload: bridge 状态数据
        :return: None
        """
        self._total_slides = int(payload.get("total_slides", 0) or 0)
        self._last_slide_index = int(payload.get("current_slide", 0) or 0)
        self._bridge_process_id = int(payload.get("process_id", 0) or 0)
        self._is_paused = payload.get("playback_state") == "paused"

    def _state_from_bridge_payload(self, payload: dict[str, object]) -> AdapterState:
        """
        将 bridge 状态转换为 AdapterState。
        :param payload: bridge 状态数据
        :return: AdapterState 实例
        """
        self._apply_bridge_state(payload)
        return AdapterState(
            playback_state=str(payload.get("playback_state", "idle")),
            current_slide=self._last_slide_index,
            total_slides=self._total_slides,
        )


__all__ = ["LibreOfficePptSourceAdapter"]
