#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
启动器 GUI：Fluent 2 风格的屏幕选择界面。
两步交互 —— ① 选择显示模式（单屏/双屏拼接）→ ② 指定目标显示器。
选择完成后关闭 GUI，由 run_player 命令创建播放窗口。
@Project : SCP-cv
@File : launcher_gui.py
@Author : Qintsg
@Date : 2026-04-14
'''
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)

from scp_cv.services.display import DisplayTarget, list_display_targets

logger = logging.getLogger(__name__)

# ═══════════════════ Fluent 2 样式表 ═══════════════════

_FLUENT_STYLESHEET = """
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

QPushButton#ModeCard {
    background: rgba(255, 255, 255, 0.86);
    border: 1px solid rgba(15, 23, 42, 0.09);
    border-radius: 14px;
    padding: 24px 20px;
    font-size: 16px;
    font-weight: 600;
    color: #0f172a;
    text-align: left;
    min-height: 80px;
}
QPushButton#ModeCard:hover {
    background: rgba(0, 120, 212, 0.08);
    border-color: rgba(0, 120, 212, 0.3);
}
QPushButton#ModeCard:pressed {
    background: rgba(0, 120, 212, 0.14);
}
QPushButton#ModeCard:checked {
    background: rgba(0, 120, 212, 0.12);
    border: 2px solid #0078d4;
}

QPushButton#DisplayCard {
    background: rgba(255, 255, 255, 0.86);
    border: 1px solid rgba(15, 23, 42, 0.09);
    border-radius: 10px;
    padding: 14px 16px;
    font-size: 14px;
    color: #0f172a;
    text-align: left;
    min-height: 50px;
}
QPushButton#DisplayCard:hover {
    background: rgba(0, 120, 212, 0.06);
    border-color: rgba(0, 120, 212, 0.25);
}
QPushButton#DisplayCard:pressed {
    background: rgba(0, 120, 212, 0.12);
}
QPushButton#DisplayCard:checked {
    background: rgba(0, 120, 212, 0.10);
    border: 2px solid #0078d4;
}

QRadioButton#RoleRadio {
    font-size: 13px;
    color: #0f172a;
    spacing: 6px;
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

QPushButton#BackButton {
    background: transparent;
    border: 1px solid rgba(15, 23, 42, 0.12);
    border-radius: 10px;
    padding: 10px 24px;
    font-size: 14px;
    color: #526076;
    min-width: 80px;
}
QPushButton#BackButton:hover {
    background: rgba(15, 23, 42, 0.04);
}

QFrame#Divider {
    background: rgba(15, 23, 42, 0.09);
    max-height: 1px;
}
"""


@dataclass
class LauncherResult:
    """启动器选择结果。"""

    display_mode: str                      # "single" 或 "left_right_splice"
    single_target: Optional[DisplayTarget] = None  # 单屏模式下的目标
    left_target: Optional[DisplayTarget] = None    # 拼接模式左屏
    right_target: Optional[DisplayTarget] = None   # 拼接模式右屏


class LauncherWindow(QWidget):
    """
    启动器主窗口：两步完成显示模式与屏幕选择。

    Step 1 — 选择显示模式（单屏 / 双屏拼接）
    Step 2 — 指定具体屏幕
      · 单屏：选一个目标屏幕
      · 双屏拼接：为每个屏幕指定左/右角色

    选择完成后发射 launch_requested 信号并关闭。
    """

    # 选择完成信号，携带 LauncherResult
    launch_requested = Signal(object)

    def __init__(self, debug_mode: bool = False) -> None:
        """
        初始化启动器窗口。
        :param debug_mode: True 时显示标题栏，False 时无边框
        """
        super().__init__()
        self._debug_mode = debug_mode
        self._display_targets = list_display_targets()
        self._selected_mode: str = ""

        # 双屏拼接选择状态
        self._role_assignments: dict[int, str] = {}  # display index → "left"/"right"

        self.setObjectName("LauncherWindow")
        self.setWindowTitle("SCP-cv 启动器")
        self.setMinimumSize(520, 480)
        self.resize(560, 520)

        if not debug_mode:
            self.setWindowFlags(
                Qt.WindowType.FramelessWindowHint
                | Qt.WindowType.WindowStaysOnTopHint
            )

        self.setStyleSheet(_FLUENT_STYLESHEET)
        self._build_ui()
        self._show_step_mode()

        # 居中显示
        self._center_on_primary()

    # ═══════════════════ UI 构建 ═══════════════════

    def _build_ui(self) -> None:
        """构建主 layout 和各步骤容器。"""
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(32, 28, 32, 24)
        self._main_layout.setSpacing(0)

        # 标题区域
        self._title_label = QLabel("SCP-cv 播放器")
        self._title_label.setObjectName("TitleLabel")
        self._subtitle_label = QLabel("选择显示模式和目标屏幕以启动播放窗口")
        self._subtitle_label.setObjectName("SubtitleLabel")
        self._main_layout.addWidget(self._title_label)
        self._main_layout.addWidget(self._subtitle_label)
        self._main_layout.addSpacing(16)

        # 分割线
        divider = QFrame()
        divider.setObjectName("Divider")
        divider.setFrameShape(QFrame.Shape.HLine)
        self._main_layout.addWidget(divider)
        self._main_layout.addSpacing(16)

        # 步骤标签
        self._step_label = QLabel()
        self._step_label.setObjectName("StepLabel")
        self._main_layout.addWidget(self._step_label)

        # 内容区域（动态替换）
        self._content_container = QWidget()
        self._content_layout = QVBoxLayout(self._content_container)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(10)
        self._main_layout.addWidget(self._content_container, stretch=1)

        # 底部按钮区域
        self._main_layout.addSpacing(16)
        self._button_bar = QHBoxLayout()
        self._button_bar.setSpacing(12)

        self._back_button = QPushButton("返回")
        self._back_button.setObjectName("BackButton")
        self._back_button.clicked.connect(self._on_back)
        self._back_button.hide()

        self._launch_button = QPushButton("启动播放")
        self._launch_button.setObjectName("PrimaryButton")
        self._launch_button.setEnabled(False)
        self._launch_button.clicked.connect(self._on_launch)

        self._button_bar.addWidget(self._back_button)
        self._button_bar.addItem(
            QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        )
        self._button_bar.addWidget(self._launch_button)
        self._main_layout.addLayout(self._button_bar)

    def _clear_content(self) -> None:
        """清空内容区域中的所有 widget。"""
        while self._content_layout.count():
            child = self._content_layout.takeAt(0)
            widget = child.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

    # ═══════════════════ Step 1: 模式选择 ═══════════════════

    def _show_step_mode(self) -> None:
        """渲染第 1 步：让用户选择单屏或双屏拼接。"""
        self._clear_content()
        self._step_label.setText("第 1 步 — 选择显示模式")
        self._back_button.hide()
        self._launch_button.setEnabled(False)
        self._launch_button.setText("下一步")

        # 断开旧连接、重连为"下一步"逻辑
        try:
            self._launch_button.clicked.disconnect()
        except RuntimeError:
            pass
        self._launch_button.clicked.connect(self._on_next_to_display)

        # 单屏卡片
        self._mode_single_btn = QPushButton("🖥  单屏模式\n在一台显示器上全屏播放")
        self._mode_single_btn.setObjectName("ModeCard")
        self._mode_single_btn.setCheckable(True)
        self._mode_single_btn.clicked.connect(
            lambda: self._select_mode("single")
        )
        self._content_layout.addWidget(self._mode_single_btn)

        # 双屏拼接卡片
        has_multiple = len(self._display_targets) >= 2
        splice_desc = "🖥🖥  双屏拼接模式\n左右两台显示器拼接为一个播放区域"
        if not has_multiple:
            splice_desc += "\n⚠ 当前仅检测到 1 台显示器，无法使用"
        self._mode_splice_btn = QPushButton(splice_desc)
        self._mode_splice_btn.setObjectName("ModeCard")
        self._mode_splice_btn.setCheckable(True)
        self._mode_splice_btn.setEnabled(has_multiple)
        self._mode_splice_btn.clicked.connect(
            lambda: self._select_mode("left_right_splice")
        )
        self._content_layout.addWidget(self._mode_splice_btn)

        # 弹性填充
        self._content_layout.addItem(
            QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        )

        # 显示器数量提示
        count_label = QLabel(
            f"已检测到 {len(self._display_targets)} 台显示器"
        )
        count_label.setObjectName("SubtitleLabel")
        count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._content_layout.addWidget(count_label)

    def _select_mode(self, mode: str) -> None:
        """
        模式按钮点击处理：互斥选中。
        :param mode: "single" 或 "left_right_splice"
        """
        self._selected_mode = mode
        self._mode_single_btn.setChecked(mode == "single")
        self._mode_splice_btn.setChecked(mode == "left_right_splice")
        self._launch_button.setEnabled(True)

    def _on_next_to_display(self) -> None:
        """点击"下一步"进入第 2 步屏幕选择。"""
        if not self._selected_mode:
            return
        if self._selected_mode == "single":
            self._show_step_single_display()
        else:
            self._show_step_splice_displays()

    # ═══════════════════ Step 2a: 单屏选择 ═══════════════════

    def _show_step_single_display(self) -> None:
        """渲染第 2 步（单屏）：选择一台目标显示器。"""
        self._clear_content()
        self._step_label.setText("第 2 步 — 选择目标显示器")
        self._back_button.show()
        self._launch_button.setText("启动播放")
        self._launch_button.setEnabled(False)

        # 重连为启动逻辑
        try:
            self._launch_button.clicked.disconnect()
        except RuntimeError:
            pass
        self._launch_button.clicked.connect(self._on_launch)

        self._single_display_group = QButtonGroup(self)
        self._single_display_group.setExclusive(True)
        self._single_display_buttons: dict[int, QPushButton] = {}

        for display_target in self._display_targets:
            primary_tag = " ⭐ 主显示器" if display_target.is_primary else ""
            card_text = (
                f"{display_target.name}{primary_tag}\n"
                f"{display_target.geometry_label}  ·  "
                f"位置 {display_target.position_label}"
            )
            card_btn = QPushButton(card_text)
            card_btn.setObjectName("DisplayCard")
            card_btn.setCheckable(True)
            card_btn.clicked.connect(
                lambda checked, idx=display_target.index: self._select_single_display(idx)
            )

            self._single_display_group.addButton(card_btn, display_target.index)
            self._single_display_buttons[display_target.index] = card_btn
            self._content_layout.addWidget(card_btn)

        self._content_layout.addItem(
            QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        )

        self._selected_single_index: Optional[int] = None

    def _select_single_display(self, display_index: int) -> None:
        """
        单屏模式下选中某台显示器。
        :param display_index: 显示器索引
        """
        self._selected_single_index = display_index
        self._launch_button.setEnabled(True)

    # ═══════════════════ Step 2b: 双屏拼接选择 ═══════════════════

    def _show_step_splice_displays(self) -> None:
        """渲染第 2 步（双屏拼接）：为每台显示器指定左/右角色。"""
        self._clear_content()
        self._step_label.setText("第 2 步 — 为显示器指定左/右角色")
        self._back_button.show()
        self._launch_button.setText("启动播放")
        self._launch_button.setEnabled(False)

        # 重连为启动逻辑
        try:
            self._launch_button.clicked.disconnect()
        except RuntimeError:
            pass
        self._launch_button.clicked.connect(self._on_launch)

        self._role_assignments.clear()
        self._role_radio_groups: dict[int, QButtonGroup] = {}

        for display_target in self._display_targets:
            primary_tag = " ⭐ 主显示器" if display_target.is_primary else ""
            # 显示器信息框
            card_frame = QFrame()
            card_frame.setStyleSheet(
                "QFrame { background: rgba(255,255,255,0.86); "
                "border: 1px solid rgba(15,23,42,0.09); "
                "border-radius: 10px; padding: 12px 16px; }"
            )
            card_layout = QVBoxLayout(card_frame)
            card_layout.setSpacing(6)

            info_label = QLabel(
                f"<b>{display_target.name}{primary_tag}</b>"
                f"<br/>{display_target.geometry_label}  ·  "
                f"位置 {display_target.position_label}"
            )
            info_label.setStyleSheet("color: #0f172a; font-size: 14px;")
            card_layout.addWidget(info_label)

            # 角色选择：左 / 右 / 不使用
            role_layout = QHBoxLayout()
            role_layout.setSpacing(16)
            role_group = QButtonGroup(card_frame)

            radio_left = QRadioButton("左屏")
            radio_left.setObjectName("RoleRadio")
            radio_right = QRadioButton("右屏")
            radio_right.setObjectName("RoleRadio")
            radio_none = QRadioButton("不使用")
            radio_none.setObjectName("RoleRadio")
            radio_none.setChecked(True)

            role_group.addButton(radio_left, 1)   # id=1 → left
            role_group.addButton(radio_right, 2)  # id=2 → right
            role_group.addButton(radio_none, 0)   # id=0 → none

            role_group.idClicked.connect(
                lambda role_id, idx=display_target.index: self._assign_role(idx, role_id)
            )

            role_layout.addWidget(radio_left)
            role_layout.addWidget(radio_right)
            role_layout.addWidget(radio_none)
            role_layout.addItem(
                QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
            )
            card_layout.addLayout(role_layout)

            self._role_radio_groups[display_target.index] = role_group
            self._content_layout.addWidget(card_frame)

        self._content_layout.addItem(
            QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        )

    def _assign_role(self, display_index: int, role_id: int) -> None:
        """
        双屏拼接模式下分配角色。互斥逻辑：同一角色只能分配给一个屏幕。
        :param display_index: 显示器索引
        :param role_id: 0=不使用, 1=左屏, 2=右屏
        """
        role_name = {0: "", 1: "left", 2: "right"}.get(role_id, "")

        # 若新角色已被其他屏幕占用，清除旧分配
        if role_name:
            for other_index, other_role in list(self._role_assignments.items()):
                if other_role == role_name and other_index != display_index:
                    self._role_assignments.pop(other_index)
                    # 重置该屏幕的 radio 为"不使用"
                    other_group = self._role_radio_groups.get(other_index)
                    if other_group is not None:
                        none_btn = other_group.button(0)
                        if none_btn is not None:
                            none_btn.setChecked(True)

        # 更新当前分配
        if role_name:
            self._role_assignments[display_index] = role_name
        else:
            self._role_assignments.pop(display_index, None)

        # 检查是否左右都已分配
        assigned_roles = set(self._role_assignments.values())
        both_assigned = "left" in assigned_roles and "right" in assigned_roles
        self._launch_button.setEnabled(both_assigned)

    # ═══════════════════ 导航按钮 ═══════════════════

    def _on_back(self) -> None:
        """返回到第 1 步。"""
        self._show_step_mode()

    def _on_launch(self) -> None:
        """点击"启动播放"：构建结果并关闭窗口。"""
        result = self._build_result()
        if result is None:
            return
        logger.info(
            "启动器选择完成：mode=%s, single=%s, left=%s, right=%s",
            result.display_mode,
            getattr(result.single_target, "name", None),
            getattr(result.left_target, "name", None),
            getattr(result.right_target, "name", None),
        )
        self.launch_requested.emit(result)
        self.close()

    def _build_result(self) -> Optional[LauncherResult]:
        """
        根据当前选择状态构建 LauncherResult。
        :return: 结果对象，若状态不完整返回 None
        """
        if self._selected_mode == "single":
            if not hasattr(self, "_selected_single_index") or self._selected_single_index is None:
                return None
            target = next(
                (dt for dt in self._display_targets if dt.index == self._selected_single_index),
                None,
            )
            if target is None:
                return None
            return LauncherResult(display_mode="single", single_target=target)

        elif self._selected_mode == "left_right_splice":
            left_index = None
            right_index = None
            for idx, role in self._role_assignments.items():
                if role == "left":
                    left_index = idx
                elif role == "right":
                    right_index = idx

            if left_index is None or right_index is None:
                return None

            left_target = next(
                (dt for dt in self._display_targets if dt.index == left_index),
                None,
            )
            right_target = next(
                (dt for dt in self._display_targets if dt.index == right_index),
                None,
            )
            if left_target is None or right_target is None:
                return None

            return LauncherResult(
                display_mode="left_right_splice",
                left_target=left_target,
                right_target=right_target,
            )

        return None

    # ═══════════════════ 辅助方法 ═══════════════════

    def _center_on_primary(self) -> None:
        """将窗口居中到主显示器。"""
        screen = QApplication.primaryScreen()
        if screen is not None:
            screen_geometry = screen.availableGeometry()
            window_geometry = self.frameGeometry()
            center_point = screen_geometry.center()
            window_geometry.moveCenter(center_point)
            self.move(window_geometry.topLeft())

    def keyPressEvent(self, event: object) -> None:
        """Escape 关闭窗口。"""
        from PySide6.QtCore import Qt as QtKey
        if hasattr(event, "key") and event.key() == QtKey.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)
