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
from PySide6.QtGui import QGuiApplication
from PySide6.QtTest import QTest
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


def test_debug_player_window_uses_resizable_16_by_9_preview(
    qt_app: QApplication,
) -> None:
    """
    开发模式应在目标屏幕内显示可缩放的 16:9 预览窗口。
    :param qt_app: QApplication fixture
    :return: None
    """
    target_screen = QGuiApplication.primaryScreen()
    assert target_screen is not None
    target_geometry = target_screen.geometry()
    window = PlayerWindow(window_id=1, debug_mode=True)

    try:
        window.position_on_display(target_geometry)
        qt_app.processEvents()

        assert window.width() * 9 == window.height() * 16
        assert window.width() <= int(target_geometry.width() * 0.8)
        assert window.height() <= int(target_geometry.height() * 0.8)
        assert target_geometry.contains(window.geometry())

        resized_width = max(160, window.width() // 2)
        resized_height = max(90, window.height() // 2)
        window.resize(resized_width, resized_height)
        qt_app.processEvents()
        assert window.size().width() == resized_width
        assert window.size().height() == resized_height
    finally:
        window.close()
        qt_app.processEvents()


def test_player_window_emits_debounced_render_viewport_size(
    qt_app: QApplication,
) -> None:
    """窗口拖动缩放后应发出稳定的原生渲染容器尺寸。"""
    window = PlayerWindow(window_id=3, debug_mode=True)
    emitted: list[tuple[int, int, int]] = []
    window.render_viewport_resized.connect(
        lambda window_id, width, height: emitted.append(
            (window_id, width, height)
        )
    )

    try:
        window.show()
        window.resize(640, 360)
        QTest.qWait(80)
        qt_app.processEvents()

        assert emitted[-1] == (3, 640, 360)
    finally:
        window.close()
        qt_app.processEvents()


def test_debug_player_windows_are_cascaded_by_window_id(
    qt_app: QApplication,
) -> None:
    """
    同一显示器上的开发窗口应按窗口编号错位，且都留在目标屏幕内。
    :param qt_app: QApplication fixture
    :return: None
    """
    target_screen = QGuiApplication.primaryScreen()
    assert target_screen is not None
    target_geometry = target_screen.geometry()
    first_window = PlayerWindow(window_id=1, debug_mode=True)
    second_window = PlayerWindow(window_id=2, debug_mode=True)

    try:
        first_window.position_on_display(target_geometry)
        second_window.position_on_display(target_geometry)
        qt_app.processEvents()

        assert first_window.pos() != second_window.pos()
        assert second_window.x() > first_window.x()
        assert second_window.y() > first_window.y()
        assert target_geometry.contains(first_window.geometry())
        assert target_geometry.contains(second_window.geometry())
    finally:
        first_window.close()
        second_window.close()
        qt_app.processEvents()


def test_production_player_window_remains_fixed_to_target_display(
    qt_app: QApplication,
) -> None:
    """
    生产模式仍应锁定为目标屏幕的完整尺寸和位置。
    :param qt_app: QApplication fixture
    :return: None
    """
    target_screen = QGuiApplication.primaryScreen()
    assert target_screen is not None
    target_geometry = target_screen.geometry()
    window = PlayerWindow(window_id=1, debug_mode=False)

    try:
        window.position_on_display(target_geometry)
        qt_app.processEvents()

        assert window.geometry() == target_geometry
        assert window.minimumSize() == target_geometry.size()
        assert window.maximumSize() == target_geometry.size()
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


def test_player_window_prepares_ppt_container(qt_app: QApplication) -> None:
    """
    PPT 首次打开前应激活视频容器并同步为播放器窗口尺寸。
    :param qt_app: QApplication fixture
    :return: None
    """
    window = PlayerWindow(window_id=4, debug_mode=True)

    try:
        window.resize(800, 450)
        window.show_black_screen()

        window.prepare_ppt_container()

        assert window.is_showing_video is True
        assert window._video_viewport.isVisible()
        assert window._video_container.isVisible()
        assert window._video_container.geometry().width() == 800
        assert window._video_container.geometry().height() == 450
    finally:
        window.close()
        qt_app.processEvents()
