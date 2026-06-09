#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
播放器窗口行为测试。
@Project : SCP-cv
@File : test_player_window.py
@Author : Qintsg
@Date : 2026-06-09
'''
from __future__ import annotations

import os
from typing import Iterator

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import QApplication, QWidget

from scp_cv.player.window import CURSOR_IDLE_HIDE_DELAY_MS, PlayerWindow


@pytest.fixture(scope="module")
def qt_app() -> Iterator[QApplication]:
    """
    提供无界面的 QApplication 实例。
    :return: QApplication 迭代器
    """
    app = QApplication.instance() or QApplication([])
    yield app


def test_player_window_hides_cursor_after_idle_timeout(qt_app: QApplication) -> None:
    """
    播放窗口初始化后应在鼠标静止超过阈值时隐藏光标。
    :param qt_app: QApplication fixture
    :return: None
    """
    window = PlayerWindow(window_id=1, debug_mode=True)

    try:
        assert window._cursor_idle_timer.isActive()
        assert window._cursor_idle_timer.interval() == CURSOR_IDLE_HIDE_DELAY_MS

        window._hide_idle_cursor()

        assert window._cursor_hidden is True
        assert window.cursor().shape() == Qt.CursorShape.BlankCursor
        assert window.web_container.cursor().shape() == Qt.CursorShape.BlankCursor
    finally:
        window.close()
        qt_app.processEvents()


def test_player_window_restores_cursor_on_mouse_move(qt_app: QApplication) -> None:
    """
    鼠标移动应恢复光标并重新开始静止计时。
    :param qt_app: QApplication fixture
    :return: None
    """
    window = PlayerWindow(window_id=2, debug_mode=True)

    try:
        window._hide_idle_cursor()

        window.eventFilter(window, QEvent(QEvent.Type.MouseMove))

        assert window._cursor_hidden is False
        assert window.cursor().shape() == Qt.CursorShape.ArrowCursor
        assert window._cursor_idle_timer.isActive()
        assert window._cursor_idle_timer.interval() == CURSOR_IDLE_HIDE_DELAY_MS
    finally:
        window.close()
        qt_app.processEvents()


def test_player_window_tracks_new_child_widgets_while_cursor_hidden(qt_app: QApplication) -> None:
    """
    光标隐藏后新增的渲染子组件也应继承隐藏光标。
    :param qt_app: QApplication fixture
    :return: None
    """
    window = PlayerWindow(window_id=3, debug_mode=True)

    try:
        window._hide_idle_cursor()
        child = QWidget(window)
        qt_app.processEvents()

        assert child.hasMouseTracking()
        assert child.cursor().shape() == Qt.CursorShape.BlankCursor
    finally:
        window.close()
        qt_app.processEvents()
