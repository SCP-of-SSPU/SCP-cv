#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
网页源适配器，通过 QWebEngineView 在 PlayerWindow 中嵌入网页。
支持加载任意 URL，全屏渲染到播放器窗口。
@Project : SCP-cv
@File : web.py
@Author : Qintsg
@Date : 2026-04-15
'''
from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import QUrl, Slot
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QWidget

from scp_cv.player.adapters.base import AdapterState, SourceAdapter

logger = logging.getLogger(__name__)


class WebSourceAdapter(SourceAdapter):
    """
    网页显示适配器。

    使用 QWebEngineView（Chromium 内核）渲染网页，
    嵌入 PlayerWindow 的视频容器中全屏显示。

    适用场景：大屏展示数据仪表盘、实时看板、公告网页等。
    """

    def __init__(self) -> None:
        super().__init__(adapter_name="web")
        self._web_view: Optional[QWebEngineView] = None
        self._url: str = ""
        self._parent_widget: Optional[QWidget] = None
        self._has_error: bool = False
        self._error_message: str = ""

    def open(self, uri: str, window_handle: int, autoplay: bool = True) -> None:
        """
        加载并显示网页。
        :param uri: 网页 URL（需包含 http:// 或 https:// 协议前缀）
        :param window_handle: 渲染目标窗口的原生句柄
        :param autoplay: 忽略（网页无播放概念）
        """
        self._url = uri
        self._has_error = False
        self._error_message = ""

        # 补全 URL 协议前缀
        normalized_url = self._normalize_url(uri)

        # 查找目标窗口的视频容器
        self._parent_widget = self._find_widget_by_handle(window_handle)

        # 创建 WebEngine 视图
        self._web_view = QWebEngineView(self._parent_widget)
        if self._parent_widget is not None:
            self._web_view.setGeometry(self._parent_widget.rect())

        # 加载完成回调
        self._web_view.loadFinished.connect(self._on_load_finished)

        # 加载网页
        self._web_view.setUrl(QUrl(normalized_url))
        self._web_view.show()

        self._mark_open()
        self._logger.info("网页已打开：%s", normalized_url)

    @staticmethod
    def _normalize_url(url_string: str) -> str:
        """
        补全 URL 协议前缀。无协议的 URL 默认添加 https://。
        :param url_string: 原始 URL 字符串
        :return: 规范化的 URL
        """
        stripped_url = url_string.strip()
        if not stripped_url:
            return "about:blank"

        # 已有协议前缀则直接返回
        if stripped_url.startswith(("http://", "https://", "file://")):
            return stripped_url

        # 本地文件路径（Windows 驱动器号开头）
        if len(stripped_url) > 2 and stripped_url[1] == ":":
            return f"file:///{stripped_url}"

        # 默认使用 https
        return f"https://{stripped_url}"

    @staticmethod
    def _find_widget_by_handle(window_handle: int) -> Optional[QWidget]:
        """
        通过原生窗口句柄查找对应的 QWidget。
        :param window_handle: 原生窗口句柄
        :return: 对应的 QWidget，找不到返回 None
        """
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            return None

        for widget in app.allWidgets():
            if int(widget.winId()) == window_handle:
                return widget
        return None

    @Slot(bool)
    def _on_load_finished(self, load_success: bool) -> None:
        """
        网页加载完成回调。
        :param load_success: 加载是否成功
        """
        if load_success:
            self._logger.info("网页加载完成：%s", self._url)
        else:
            self._has_error = True
            self._error_message = f"网页加载失败：{self._url}"
            self._logger.error(self._error_message)

    def close(self) -> None:
        """关闭网页并释放资源。"""
        if self._web_view is not None:
            self._web_view.setUrl(QUrl("about:blank"))
            self._web_view.hide()
            self._web_view.deleteLater()
            self._web_view = None

        self._parent_widget = None
        self._url = ""
        self._has_error = False
        self._error_message = ""
        self._mark_closed()
        self._logger.info("网页已关闭")

    # ═══════════════════ 播放控制（网页无时间线） ═══════════════════

    def play(self) -> None:
        """刷新网页（恢复播放语义映射为刷新）。"""
        if self._web_view is not None:
            self._web_view.reload()
            self._logger.debug("网页已刷新")

    def pause(self) -> None:
        """网页无暂停概念，忽略。"""
        self._logger.debug("网页不支持 pause 操作")

    def stop(self) -> None:
        """停止加载网页。"""
        if self._web_view is not None:
            self._web_view.stop()
            self._logger.debug("网页加载已停止")

    # ═══════════════════ 状态获取 ═══════════════════

    def get_state(self) -> AdapterState:
        """
        获取网页显示状态。
        :return: 网页加载中返回 loading，加载完成返回 playing
        """
        if self._has_error:
            return AdapterState(
                playback_state="error",
                error_message=self._error_message,
            )

        if self._web_view is not None:
            return AdapterState(playback_state="playing")

        return AdapterState(playback_state="idle")
