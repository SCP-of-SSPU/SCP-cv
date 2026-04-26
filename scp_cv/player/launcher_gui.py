#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
启动器 GUI：Fluent 2 风格的多窗口屏幕选择界面。
四步交互 —— 逐个为窗口 1~4 指定目标显示器，
选择完成后关闭 GUI，由 run_player 命令创建播放窗口。
播放控制统一在 Web 控制台中完成。
@Project : SCP-cv
@File : launcher_gui.py
@Author : Qintsg
@Date : 2026-04-14
'''
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
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

QPushButton#DisplayCard:disabled {
    background: rgba(200, 200, 200, 0.4);
    color: #999999;
    border: 1px solid rgba(15, 23, 42, 0.05);
}

QLabel#SelectedTag {
    font-size: 11px;
    font-weight: 600;
    color: #ffffff;
    background: #0078d4;
    border-radius: 6px;
    padding: 2px 8px;
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

QFrame#SummaryCard {
    background: rgba(255, 255, 255, 0.86);
    border: 1px solid rgba(15, 23, 42, 0.09);
    border-radius: 10px;
    padding: 12px 16px;
}
"""

# 需要选择的窗口总数
TOTAL_WINDOWS = 4


@dataclass
class LauncherResult:
    """
    启动器选择结果：记录每个窗口分配的显示器。
    window_assignments: window_id(1-4) → DisplayTarget
    """

    window_assignments: dict[int, DisplayTarget] = field(default_factory=dict)


class LauncherWindow(QWidget):
    """
    启动器主窗口：逐步为窗口 1~4 分配目标显示器。

    交互流程：
    Step 1 → 选择窗口 1 的屏幕
    Step 2 → 选择窗口 2 的屏幕（正常模式灰显已选屏幕）
    Step 3 → 选择窗口 3 的屏幕
    Step 4 → 选择窗口 4 的屏幕
    确认 → 显示总览，启动播放

    正常模式下显示器数量不足时自动减少可用窗口数。
    DEBUG 模式下始终开放全部 4 个窗口，同一显示器可分配给多个窗口。
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

        # 分配映射：window_id(1-4) → DisplayTarget
        self._assignments: dict[int, DisplayTarget] = {}
        # 当前正在选择的窗口编号（1-4）
        self._current_step = 1
        # 可分配的最大窗口数
        # DEBUG 模式下允许窗口数超过显示器数量（同一屏幕可复用）
        if debug_mode:
            self._max_windows = TOTAL_WINDOWS
        else:
            self._max_windows = min(TOTAL_WINDOWS, len(self._display_targets))

        self.setObjectName("LauncherWindow")
        self.setWindowTitle("SCP-cv 启动器")
        self.setMinimumSize(560, 520)
        self.resize(600, 560)

        if not debug_mode:
            self.setWindowFlags(
                Qt.WindowType.FramelessWindowHint
                | Qt.WindowType.WindowStaysOnTopHint
            )

        self.setStyleSheet(_FLUENT_STYLESHEET)
        self._build_ui()

        if self._max_windows > 0:
            self._show_step_select_display(self._current_step)
        else:
            self._show_no_displays_warning()

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
        # 副标题：DEBUG 模式提示可复用显示器
        reuse_hint = "，同一屏幕可复用" if self._debug_mode else ""
        self._subtitle_label = QLabel(
            f"依次为 {self._max_windows} 个播放窗口选择目标显示器（共检测到 "
            f"{len(self._display_targets)} 台{reuse_hint}）"
        )
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

        self._back_button = QPushButton("返回上一步")
        self._back_button.setObjectName("BackButton")
        self._back_button.clicked.connect(self._on_back)
        self._back_button.hide()

        self._next_button = QPushButton("下一步")
        self._next_button.setObjectName("PrimaryButton")
        self._next_button.setEnabled(False)
        self._next_button.clicked.connect(self._on_next)

        self._button_bar.addWidget(self._back_button)
        self._button_bar.addItem(
            QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        )
        self._button_bar.addWidget(self._next_button)
        self._main_layout.addLayout(self._button_bar)

    def _clear_content(self) -> None:
        """清空内容区域中的所有 widget。"""
        while self._content_layout.count():
            child = self._content_layout.takeAt(0)
            widget = child.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

    # ═══════════════════ 已占用屏幕管理 ═══════════════════

    def _assigned_display_indices(self) -> set[int]:
        """获取已被分配的显示器索引集合。"""
        return {dt.index for dt in self._assignments.values()}

    # ═══════════════════ 步骤渲染 ═══════════════════

    def _show_no_displays_warning(self) -> None:
        """未检测到任何显示器时显示警告。"""
        self._clear_content()
        self._step_label.setText("⚠ 无法启动")
        warning_label = QLabel("未检测到可用的显示器，请检查硬件连接后重试。")
        warning_label.setObjectName("SubtitleLabel")
        warning_label.setWordWrap(True)
        self._content_layout.addWidget(warning_label)
        self._next_button.setEnabled(False)

    def _show_step_select_display(self, window_id: int) -> None:
        """
        渲染屏幕选择步骤：为指定窗口选择一台显示器。
        :param window_id: 当前选择的窗口编号（1-4）
        """
        self._clear_content()
        self._step_label.setText(
            f"第 {window_id} / {self._max_windows} 步 — 选择窗口 {window_id} 的显示器"
        )

        # 显示/隐藏返回按钮
        self._back_button.setVisible(window_id > 1)
        self._next_button.setText("下一步")
        self._next_button.setEnabled(False)

        # 清除该步骤之前可能存在的临时选中状态
        self._pending_selection: int | None = None

        assigned_indices = self._assigned_display_indices()

        for display_target in self._display_targets:
            is_assigned = display_target.index in assigned_indices
            primary_tag = " ⭐ 主显示器" if display_target.is_primary else ""

            # 已分配给其他窗口的屏幕：显示占用标记
            assigned_window_label = ""
            if is_assigned:
                for wid, assigned_dt in self._assignments.items():
                    if assigned_dt.index == display_target.index:
                        assigned_window_label = f"  [已分配给窗口 {wid}]"
                        break

            card_text = (
                f"{display_target.name}{primary_tag}{assigned_window_label}\n"
                f"{display_target.geometry_label}  ·  位置 {display_target.position_label}"
            )

            card_btn = QPushButton(card_text)
            card_btn.setObjectName("DisplayCard")
            card_btn.setCheckable(True)
            # DEBUG 模式下允许复用已分配的显示器
            card_btn.setEnabled(not is_assigned or self._debug_mode)
            card_btn.clicked.connect(
                lambda checked, idx=display_target.index: self._select_display(idx)
            )
            self._content_layout.addWidget(card_btn)

        self._content_layout.addItem(
            QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        )

    def _show_summary(self) -> None:
        """渲染确认总览页面，显示所有窗口分配和 GUI 屏幕。"""
        self._clear_content()
        self._step_label.setText("确认 — 播放窗口分配总览")
        self._back_button.show()
        self._next_button.setText("启动播放")
        self._next_button.setEnabled(True)

        for window_id in sorted(self._assignments.keys()):
            display_target = self._assignments[window_id]
            primary_tag = " ⭐" if display_target.is_primary else ""

            summary_frame = QFrame()
            summary_frame.setObjectName("SummaryCard")
            summary_layout = QHBoxLayout(summary_frame)
            summary_layout.setContentsMargins(12, 8, 12, 8)

            window_label = QLabel(f"窗口 {window_id}")
            window_label.setStyleSheet(
                "font-size: 16px; font-weight: 600; color: #0078d4;"
            )
            display_label = QLabel(
                f"{display_target.name}{primary_tag}  ·  "
                f"{display_target.geometry_label}  ·  "
                f"位置 {display_target.position_label}"
            )
            display_label.setStyleSheet("font-size: 14px; color: #0f172a;")

            summary_layout.addWidget(window_label)
            summary_layout.addSpacing(16)
            summary_layout.addWidget(display_label, stretch=1)
            self._content_layout.addWidget(summary_frame)

        web_hint_label = QLabel("启动后请在浏览器打开 Web 控制台完成播放控制。")
        web_hint_label.setObjectName("SubtitleLabel")
        web_hint_label.setWordWrap(True)
        self._content_layout.addWidget(web_hint_label)

        self._content_layout.addItem(
            QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        )

    # ═══════════════════ 用户交互 ═══════════════════

    def _select_display(self, display_index: int) -> None:
        """
        选中某台显示器供当前窗口使用。
        :param display_index: 显示器索引
        """
        self._pending_selection = display_index
        self._next_button.setEnabled(True)

    def _on_next(self) -> None:
        """点击"下一步"或"启动播放"。"""
        # 总览页面点击"启动播放"
        if self._current_step > self._max_windows:
            self._on_launch()
            return

        # 屏幕选择页面 → 记录分配 → 进入下一步或总览
        if hasattr(self, "_pending_selection") and self._pending_selection is not None:
            selected_display = next(
                (dt for dt in self._display_targets if dt.index == self._pending_selection),
                None,
            )
            if selected_display is not None:
                self._assignments[self._current_step] = selected_display

            self._pending_selection = None
            self._current_step += 1

            if self._current_step <= self._max_windows:
                self._show_step_select_display(self._current_step)
            else:
                self._show_summary()

    def _on_back(self) -> None:
        """返回上一步。"""
        if self._current_step > self._max_windows:
            # 从总览返回到最后一步
            self._current_step = self._max_windows
            # 撤销最后一步的分配
            self._assignments.pop(self._current_step, None)
            self._show_step_select_display(self._current_step)
        elif self._current_step > 1:
            # 撤销当前步骤上一步的分配
            self._current_step -= 1
            self._assignments.pop(self._current_step, None)
            self._show_step_select_display(self._current_step)

    def _on_launch(self) -> None:
        """点击"启动播放"：构建结果并关闭窗口。"""
        launch_result = LauncherResult(
            window_assignments=dict(self._assignments),
        )
        assignment_summary = ", ".join(
            f"窗口{wid}→{dt.name}"
            for wid, dt in sorted(launch_result.window_assignments.items())
        )
        logger.info(
            "启动器选择完成：%s，控制端=Web 控制台",
            assignment_summary,
        )
        self.launch_requested.emit(launch_result)
        self.close()

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
