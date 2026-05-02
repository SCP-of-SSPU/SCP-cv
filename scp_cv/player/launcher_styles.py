#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
启动器 GUI 样式表。
集中维护选择界面的 Qt 样式，避免交互逻辑文件继续堆叠样式内容。
@Project : SCP-cv
@File : launcher_styles.py
@Author : Qintsg
@Date : 2026-05-02
'''

from __future__ import annotations


# 启动器使用浅色 Fluent 风格；样式集中放置，便于后续替换品牌色。
FLUENT_STYLESHEET = """
QWidget#LauncherWindow {
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:1,
        stop:0 #f8fbff, stop:1 #eff4fb
    );
}

QLabel#TitleLabel {
    font-size: 24px;
    font-weight: 600;
    color: #0f172a;
    padding: 4px 0px;
}

QLabel#SubtitleLabel {
    font-size: 14px;
    color: #526076;
    padding: 2px 0px;
}

QLabel#StepLabel {
    font-size: 13px;
    font-weight: 600;
    color: #0078d4;
    padding: 6px 0px;
}

QLabel#AssignmentHint {
    font-size: 12px;
    color: #526076;
    padding: 2px 0px 8px 0px;
}

QScrollArea#ContentScroll {
    background: transparent;
    border: none;
}

QScrollArea#ContentScroll QWidget {
    background: transparent;
}

QScrollBar:vertical {
    width: 8px;
    background: transparent;
}

QScrollBar::handle:vertical {
    background: rgba(15, 23, 42, 0.18);
    border-radius: 4px;
    min-height: 28px;
}

QPushButton#DisplayCard {
    background: rgba(255, 255, 255, 0.90);
    border: 1px solid rgba(15, 23, 42, 0.09);
    border-radius: 10px;
    padding: 14px 16px;
    font-size: 14px;
    color: #0f172a;
    text-align: left;
    min-height: 58px;
}
QPushButton#DisplayCard:hover {
    background: rgba(0, 120, 212, 0.06);
    border-color: rgba(0, 120, 212, 0.25);
}
QPushButton#DisplayCard:pressed {
    background: rgba(0, 120, 212, 0.12);
}
QPushButton#DisplayCard:checked {
    background: rgba(0, 120, 212, 0.12);
    border: 2px solid #0078d4;
    font-weight: 600;
}
QPushButton#DisplayCard:disabled {
    background: rgba(200, 200, 200, 0.4);
    color: #999999;
    border: 1px solid rgba(15, 23, 42, 0.05);
}

QPushButton#PrimaryButton {
    background: #0078d4;
    border: none;
    border-radius: 10px;
    padding: 12px 32px;
    font-size: 15px;
    font-weight: 600;
    color: #ffffff;
    min-width: 140px;
}
QPushButton#PrimaryButton:hover {
    background: #005a9e;
}
QPushButton#PrimaryButton:pressed {
    background: #004578;
}
QPushButton#PrimaryButton:disabled {
    background: rgba(0, 120, 212, 0.3);
    color: rgba(255, 255, 255, 0.6);
}

QPushButton#BackButton,
QPushButton#CancelButton {
    background: transparent;
    border: 1px solid rgba(15, 23, 42, 0.12);
    border-radius: 10px;
    padding: 10px 24px;
    font-size: 14px;
    color: #526076;
    min-width: 80px;
}
QPushButton#BackButton:hover,
QPushButton#CancelButton:hover {
    background: rgba(15, 23, 42, 0.04);
}

QFrame#Divider {
    background: rgba(15, 23, 42, 0.09);
    max-height: 1px;
}

QFrame#SummaryCard {
    background: rgba(255, 255, 255, 0.86);
    border: 1px solid rgba(15, 23, 42, 0.09);
    border-radius: 10px;
    padding: 12px 16px;
}

QComboBox#GpuCombo {
    background: rgba(255, 255, 255, 0.86);
    border: 1px solid rgba(15, 23, 42, 0.09);
    border-radius: 10px;
    padding: 10px 16px;
    font-size: 14px;
    color: #0f172a;
    min-height: 40px;
    min-width: 280px;
}
QComboBox#GpuCombo:hover {
    background: rgba(0, 120, 212, 0.06);
    border-color: rgba(0, 120, 212, 0.25);
}
QComboBox#GpuCombo::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 32px;
    border-left: none;
    border-top-right-radius: 10px;
    border-bottom-right-radius: 10px;
}
QComboBox#GpuCombo::down-arrow {
    width: 12px;
    height: 12px;
}
QComboBox#GpuCombo QAbstractItemView {
    background: rgba(255, 255, 255, 0.96);
    border: 1px solid rgba(15, 23, 42, 0.09);
    border-radius: 8px;
    padding: 6px;
    font-size: 13px;
    color: #0f172a;
    selection-background-color: rgba(0, 120, 212, 0.10);
    selection-color: #0f172a;
    outline: none;
}

QLabel#GpuLabel {
    font-size: 13px;
    font-weight: 600;
    color: #526076;
    padding: 2px 0px;
}
"""
