#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
网页源适配器，通过 QWebEngineView 在 PlayerWindow 中嵌入可交互的网页。
支持加载任意 URL，全屏渲染到播放器窗口，并允许鼠标点击、滚动等操作。
@Project : SCP-cv
@File : web.py
@Author : Qintsg
@Date : 2026-04-15
'''
from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import Qt, QUrl, Slot
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QVBoxLayout, QWidget

from scp_cv.player.adapters.base import AdapterState, SourceAdapter
from scp_cv.services.media import normalize_web_url

logger = logging.getLogger(__name__)


class WebSourceAdapter(SourceAdapter):
    """
    网页显示适配器。

    使用 QWebEngineView（Chromium 内核）渲染网页，
    嵌入 PlayerWindow 的网页容器中全屏显示。
    与视频容器不同，网页容器不使用 WA_NativeWindow 属性，
    因此 QWebEngineView 能正常接收鼠标和键盘事件，
    支持页面内点击链接、滚动、表单输入等交互操作。

    适用场景：大屏展示数据仪表盘、实时看板、公告网页等。
    """

    def __init__(self) -> None:
        super().__init__(adapter_name="web")
        self._web_view: Optional[QWebEngineView] = None
        self._url: str = ""
        # 由 PlayerController 在 open() 前通过 set_parent_container() 注入
        self._parent_widget: Optional[QWidget] = None
        self._has_error: bool = False
        self._error_message: str = ""
        # 标记容器是否由外部显式注入（而非通过句柄查找）
        self._container_injected: bool = False

    def set_parent_container(self, container: QWidget) -> None:
        """
        注入渲染容器 widget。
        由 PlayerController 在调用 open() 前设置，将 QWebEngineView
        创建为此容器的子组件，避免使用原生窗口句柄查找。
        :param container: PlayerWindow.web_container 引用
        """
        self._parent_widget = container
        self._container_injected = True

    def open(self, uri: str, window_handle: int, autoplay: bool = True) -> None:
        """
        加载并显示网页。
        :param uri: 网页 URL（需包含 http:// 或 https:// 协议前缀）
        :param window_handle: 渲染目标窗口的原生句柄（备用，优先使用注入的容器）
        :param autoplay: 忽略（网页无播放概念）
        """
        # 补全 URL 协议前缀
        normalized_url = self._normalize_url(uri)
        self._url = normalized_url
        self._has_error = False
        self._error_message = ""

        # 如果未通过 set_parent_container() 注入，则回退到句柄查找
        if not self._container_injected:
            self._parent_widget = self._find_widget_by_handle(window_handle)

        if self._parent_widget is None:
            self._has_error = True
            self._error_message = "无法获取渲染容器"
            self._logger.error(self._error_message)
            return

        # 为容器设置布局（如果尚未设置），使 QWebEngineView 自动填满
        if self._parent_widget.layout() is None:
            container_layout = QVBoxLayout(self._parent_widget)
            container_layout.setContentsMargins(0, 0, 0, 0)
            container_layout.setSpacing(0)

        # 创建 QWebEngineView 并配置交互属性
        self._web_view = QWebEngineView(self._parent_widget)
        self._configure_web_view_interaction(self._web_view)

        # 将 web view 添加到容器的布局中（自动随窗口缩放）
        self._parent_widget.layout().addWidget(self._web_view)

        # 监听加载完成事件
        self._web_view.loadFinished.connect(self._on_load_finished)

        # 加载并显示网页
        self._web_view.setUrl(QUrl(normalized_url))
        self._web_view.show()
        # 将焦点设置到 web view 以接收键盘事件
        self._web_view.setFocus()

        self._mark_open()
        self._logger.info("网页已打开：%s", normalized_url)

    @staticmethod
    def _configure_web_view_interaction(web_view: QWebEngineView) -> None:
        """
        配置 QWebEngineView 的交互属性，确保鼠标和键盘事件正常传递。
        :param web_view: 待配置的 QWebEngineView 实例
        """
        # 允许 Tab 键和鼠标点击获取焦点
        web_view.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        # 启用鼠标追踪（hover 事件）
        web_view.setMouseTracking(True)
        # 允许右键上下文菜单（浏览器默认行为）
        web_view.setContextMenuPolicy(Qt.ContextMenuPolicy.DefaultContextMenu)

        # 配置 WebEngine 页面设置
        page_settings = web_view.page().settings()
        # 启用 JavaScript（默认已启用，显式声明确保不被意外关闭）
        from PySide6.QtWebEngineCore import QWebEngineSettings
        page_settings.setAttribute(
            QWebEngineSettings.WebAttribute.JavascriptEnabled, True,
        )
        # 允许 JavaScript 打开窗口（弹窗）
        page_settings.setAttribute(
            QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows, False,
        )
        # 启用本地存储（LocalStorage / IndexedDB）
        page_settings.setAttribute(
            QWebEngineSettings.WebAttribute.LocalStorageEnabled, True,
        )
        # 允许剪贴板读写（便于大屏复制数据）
        page_settings.setAttribute(
            QWebEngineSettings.WebAttribute.JavascriptCanAccessClipboard, True,
        )
        # 启用滚动动画（平滑滚动）
        page_settings.setAttribute(
            QWebEngineSettings.WebAttribute.ScrollAnimatorEnabled, True,
        )

    @staticmethod
    def _normalize_url(url_string: str) -> str:
        """
        补全 URL 协议前缀。无协议的 URL 默认添加 http://，优先兼容局域网网页源。
        :param url_string: 原始 URL 字符串
        :return: 规范化的 URL
        """
        normalized_url = normalize_web_url(url_string)
        if not normalized_url:
            return "about:blank"
        return normalized_url

    @staticmethod
    def _find_widget_by_handle(window_handle: int) -> Optional[QWidget]:
        """
        通过原生窗口句柄查找对应的 QWidget（备用方案）。
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
            self._error_message = f"网页加载失败：{self._url}，请确认地址、协议和局域网可达性"
            self._logger.error(self._error_message)

    def close(self) -> None:
        """关闭网页并释放资源。"""
        if self._web_view is not None:
            # 先导航到空白页停止所有网络活动
            self._web_view.setUrl(QUrl("about:blank"))
            self._web_view.hide()

            # 从容器布局中移除（避免残留引用）
            if self._parent_widget is not None and self._parent_widget.layout() is not None:
                self._parent_widget.layout().removeWidget(self._web_view)

            self._web_view.deleteLater()
            self._web_view = None

        self._parent_widget = None
        self._container_injected = False
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
