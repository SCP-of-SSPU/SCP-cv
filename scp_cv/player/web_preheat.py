#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
网页源预热池：在播放器进程中提前加载并复用 QWebEngineView。
@Project : SCP-cv
@File : web_preheat.py
@Author : Qintsg
@Date : 2026-05-09
'''
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from PySide6.QtCore import QUrl, Slot
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QVBoxLayout, QWidget

from scp_cv.services.media_web import normalize_web_url

logger = logging.getLogger(__name__)


@dataclass
class PreheatedWebView:
    """
    已预热网页视图记录。
    """

    source_id: int
    url: str
    view: QWebEngineView


class WebPreheatPool:
    """
    QWebEngineView 预热池。
    """

    def __init__(self) -> None:
        """
        初始化隐藏宿主容器。
        :return: None
        """
        self._host = QWidget()
        self._host.setObjectName("WebPreheatHost")
        self._host.hide()
        host_layout = QVBoxLayout(self._host)
        host_layout.setContentsMargins(0, 0, 0, 0)
        host_layout.setSpacing(0)
        self._items: dict[int, PreheatedWebView] = {}

    def preheat_source(self, source_id: int, url: str) -> None:
        """
        预热指定网页源。
        :param source_id: 媒体源 ID
        :param url: 网页 URL
        :return: None
        """
        normalized_url = normalize_web_url(url)
        if source_id <= 0 or not normalized_url:
            return
        existing = self._items.get(source_id)
        if existing is not None and existing.url == normalized_url:
            return
        if existing is not None:
            self._dispose_view(existing.view)

        view = QWebEngineView(self._host)
        view.hide()
        self._host.layout().addWidget(view)
        view.loadFinished.connect(self._on_load_finished)
        view.setUrl(QUrl(normalized_url))
        self._items[source_id] = PreheatedWebView(source_id=source_id, url=normalized_url, view=view)
        logger.info("网页源已开始预热：source_id=%d, url=%s", source_id, normalized_url)

    def take_preheated_view(
        self,
        source_id: int,
        url: str,
        parent_widget: QWidget,
    ) -> Optional[QWebEngineView]:
        """
        认领已预热的 WebView，并挂载到播放窗口容器。
        :param source_id: 媒体源 ID
        :param url: 待打开 URL
        :param parent_widget: 播放窗口网页容器
        :return: 匹配的 QWebEngineView；没有命中时返回 None
        """
        normalized_url = normalize_web_url(url)
        item = self._items.pop(source_id, None)
        if item is None:
            return None
        if item.url != normalized_url:
            self._dispose_view(item.view)
            return None
        self._detach_from_current_parent(item.view)
        item.view.setParent(parent_widget)
        if parent_widget.layout() is not None:
            parent_widget.layout().addWidget(item.view)
        logger.info("已复用网页预热视图：source_id=%d, url=%s", source_id, normalized_url)
        return item.view

    def release_preheated_view(self, source_id: int, url: str, view: QWebEngineView) -> None:
        """
        将当前播放窗口里的 WebView 放回预热池。
        :param source_id: 媒体源 ID
        :param url: 当前 URL
        :param view: 待回收的 QWebEngineView
        :return: None
        """
        normalized_url = normalize_web_url(url)
        if source_id <= 0 or not normalized_url:
            self._dispose_view(view)
            return
        self._detach_from_current_parent(view)
        view.setParent(self._host)
        self._host.layout().addWidget(view)
        view.hide()
        self._items[source_id] = PreheatedWebView(source_id=source_id, url=normalized_url, view=view)
        logger.info("网页预热视图已回收：source_id=%d, url=%s", source_id, normalized_url)

    def close_all(self) -> None:
        """
        释放所有预热视图。
        :return: None
        """
        for item in list(self._items.values()):
            self._dispose_view(item.view)
        self._items.clear()
        self._host.deleteLater()

    @Slot(bool)
    def _on_load_finished(self, load_success: bool) -> None:
        """
        记录预热视图加载结果。
        :param load_success: 加载是否成功
        :return: None
        """
        logger.info("网页预热加载完成：success=%s", load_success)

    @staticmethod
    def _detach_from_current_parent(view: QWebEngineView) -> None:
        """
        从当前父容器布局中移除 WebView。
        :param view: 待移除视图
        :return: None
        """
        parent = view.parentWidget()
        if parent is not None and parent.layout() is not None:
            parent.layout().removeWidget(view)

    @staticmethod
    def _dispose_view(view: QWebEngineView) -> None:
        """
        停止并释放 WebView。
        :param view: 待释放视图
        :return: None
        """
        WebPreheatPool._detach_from_current_parent(view)
        view.setUrl(QUrl("about:blank"))
        view.hide()
        view.deleteLater()
