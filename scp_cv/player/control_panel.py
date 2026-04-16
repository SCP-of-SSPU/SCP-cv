#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
GUI 控制面板（窗口 0）：Fluent 2 风格的多窗口播放控制界面。
提供与 Web 前端对等的功能——窗口状态监控、源管理、播放控制、
拼接模式切换、窗口 ID 显示。
通过定时器轮询 DB 状态更新 UI，通过 pending_command 下发指令。
@Project : SCP-cv
@File : control_panel.py
@Author : Qintsg
@Date : 2026-04-18
'''
from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)

# 状态轮询间隔（毫秒）
_STATUS_POLL_MS = 1000

# ═══════════════════ Fluent 2 样式表 ═══════════════════

_PANEL_STYLESHEET = """
QWidget#ControlPanel {
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:1,
        stop:0 #f8fbff, stop:1 #eff4fb
    );
}

QLabel#PanelTitle {
    font-size: 20px;
    font-weight: 600;
    color: #0f172a;
}

QLabel#SectionTitle {
    font-size: 14px;
    font-weight: 600;
    color: #0078d4;
    padding: 4px 0px;
}

QLabel#StatusLabel {
    font-size: 12px;
    color: #526076;
}

QFrame#WindowCard {
    background: rgba(255, 255, 255, 0.86);
    border: 1px solid rgba(15, 23, 42, 0.09);
    border-radius: 10px;
    padding: 12px;
}

QFrame#WindowCard[active="true"] {
    border: 2px solid #0078d4;
    background: rgba(0, 120, 212, 0.04);
}

QPushButton#ActionButton {
    background: #0078d4;
    border: none;
    border-radius: 8px;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 600;
    color: #ffffff;
    min-width: 60px;
}
QPushButton#ActionButton:hover {
    background: #005a9e;
}
QPushButton#ActionButton:pressed {
    background: #004578;
}
QPushButton#ActionButton:disabled {
    background: rgba(0, 120, 212, 0.3);
    color: rgba(255, 255, 255, 0.6);
}

QPushButton#DangerButton {
    background: #d13438;
    border: none;
    border-radius: 8px;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 600;
    color: #ffffff;
    min-width: 60px;
}
QPushButton#DangerButton:hover {
    background: #a52e31;
}
QPushButton#DangerButton:disabled {
    background: rgba(209, 52, 56, 0.3);
    color: rgba(255, 255, 255, 0.6);
}

QPushButton#SecondaryButton {
    background: transparent;
    border: 1px solid rgba(15, 23, 42, 0.12);
    border-radius: 8px;
    padding: 8px 16px;
    font-size: 13px;
    color: #0f172a;
}
QPushButton#SecondaryButton:hover {
    background: rgba(15, 23, 42, 0.04);
}
QPushButton#SecondaryButton:checked {
    background: rgba(0, 120, 212, 0.10);
    border: 2px solid #0078d4;
    color: #0078d4;
    font-weight: 600;
}

QComboBox#SourceCombo {
    background: rgba(255, 255, 255, 0.86);
    border: 1px solid rgba(15, 23, 42, 0.12);
    border-radius: 8px;
    padding: 6px 12px;
    font-size: 13px;
    color: #0f172a;
    min-width: 200px;
}
QComboBox#SourceCombo:hover {
    border-color: rgba(0, 120, 212, 0.35);
}
QComboBox#SourceCombo QAbstractItemView {
    background: #ffffff;
    border: 1px solid rgba(15, 23, 42, 0.12);
    border-radius: 8px;
    selection-background-color: rgba(0, 120, 212, 0.10);
}

QFrame#Divider {
    background: rgba(15, 23, 42, 0.09);
    max-height: 1px;
}

QScrollArea {
    border: none;
    background: transparent;
}
"""

# 播放状态 → 中文标签 & 颜色
_STATE_DISPLAY: dict[str, tuple[str, str]] = {
    "IDLE": ("空闲", "#526076"),
    "PLAYING": ("播放中", "#107c10"),
    "PAUSED": ("已暂停", "#ca5010"),
    "STOPPED": ("已停止", "#d13438"),
}


class ControlPanel(QWidget):
    """
    GUI 控制面板（窗口 0），Fluent 2 风格。
    功能对等 Web 前端：窗口状态卡片、源选择、播放控制、拼接模式、ID 显示。
    通过 QTimer 定期轮询 DB 刷新 UI。
    """

    def __init__(
        self,
        controller: object,
        debug_mode: bool = False,
    ) -> None:
        """
        初始化控制面板。
        :param controller: PlayerController 实例，用于获取窗口引用
        :param debug_mode: 调试模式（显示标题栏）
        """
        super().__init__()
        self._controller = controller
        self._debug_mode = debug_mode
        # 当前选中的窗口编号
        self._selected_window: int = 1
        # 窗口卡片引用：window_id → 卡片组件字典
        self._window_cards: dict[int, dict[str, QLabel]] = {}
        # 源列表缓存：list of (source_id, display_name)
        self._cached_sources: list[tuple[int, str]] = []

        self.setObjectName("ControlPanel")
        self.setWindowTitle("SCP-cv 控制面板")
        self.setMinimumSize(480, 640)
        self.resize(520, 720)

        if not debug_mode:
            self.setWindowFlags(
                Qt.WindowType.WindowStaysOnTopHint
                | Qt.WindowType.Tool
            )

        self.setStyleSheet(_PANEL_STYLESHEET)
        self._build_ui()
        self._refresh_source_list()

        # 状态轮询定时器
        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._poll_status)
        self._poll_timer.start(_STATUS_POLL_MS)

    # ═══════════════════ UI 构建 ═══════════════════

    def _build_ui(self) -> None:
        """构建完整的控制面板 UI。"""
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(20, 16, 20, 16)
        root_layout.setSpacing(12)

        # 标题
        title_label = QLabel("SCP-cv 控制面板")
        title_label.setObjectName("PanelTitle")
        root_layout.addWidget(title_label)

        # 分割线
        divider = QFrame()
        divider.setObjectName("Divider")
        divider.setFrameShape(QFrame.Shape.HLine)
        root_layout.addWidget(divider)

        # 滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(16)

        # ── 窗口状态区域 ──
        status_section_label = QLabel("窗口状态")
        status_section_label.setObjectName("SectionTitle")
        scroll_layout.addWidget(status_section_label)

        status_grid = QGridLayout()
        status_grid.setSpacing(8)
        for window_id in range(1, 5):
            card = self._create_window_card(window_id)
            row = (window_id - 1) // 2
            col = (window_id - 1) % 2
            status_grid.addWidget(card, row, col)
        scroll_layout.addLayout(status_grid)

        # ── 全局操作区域 ──
        global_section_label = QLabel("全局操作")
        global_section_label.setObjectName("SectionTitle")
        scroll_layout.addWidget(global_section_label)

        global_bar = QHBoxLayout()
        global_bar.setSpacing(8)

        # 拼接模式切换
        self._splice_button = QPushButton("拼接 1+2")
        self._splice_button.setObjectName("SecondaryButton")
        self._splice_button.setCheckable(True)
        self._splice_button.clicked.connect(self._on_toggle_splice)
        global_bar.addWidget(self._splice_button)

        # 显示窗口 ID
        show_ids_button = QPushButton("显示窗口 ID")
        show_ids_button.setObjectName("ActionButton")
        show_ids_button.clicked.connect(self._on_show_ids)
        global_bar.addWidget(show_ids_button)

        global_bar.addItem(
            QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        )
        scroll_layout.addLayout(global_bar)

        # ── 分割线 ──
        divider2 = QFrame()
        divider2.setObjectName("Divider")
        divider2.setFrameShape(QFrame.Shape.HLine)
        scroll_layout.addWidget(divider2)

        # ── 播放控制区域（针对选中窗口） ──
        control_section_label = QLabel("播放控制")
        control_section_label.setObjectName("SectionTitle")
        scroll_layout.addWidget(control_section_label)

        # 窗口选择器
        window_select_bar = QHBoxLayout()
        window_select_bar.setSpacing(4)
        self._window_buttons: dict[int, QPushButton] = {}
        for window_id in range(1, 5):
            window_button = QPushButton(f"窗口 {window_id}")
            window_button.setObjectName("SecondaryButton")
            window_button.setCheckable(True)
            window_button.setChecked(window_id == 1)
            window_button.clicked.connect(
                lambda checked, wid=window_id: self._select_window(wid)
            )
            self._window_buttons[window_id] = window_button
            window_select_bar.addWidget(window_button)
        scroll_layout.addLayout(window_select_bar)

        # 源选择 + 打开
        source_bar = QHBoxLayout()
        source_bar.setSpacing(8)
        self._source_combo = QComboBox()
        self._source_combo.setObjectName("SourceCombo")
        self._source_combo.setPlaceholderText("选择媒体源…")
        source_bar.addWidget(self._source_combo, stretch=1)

        refresh_sources_button = QPushButton("刷新")
        refresh_sources_button.setObjectName("SecondaryButton")
        refresh_sources_button.clicked.connect(self._refresh_source_list)
        source_bar.addWidget(refresh_sources_button)

        open_button = QPushButton("打开")
        open_button.setObjectName("ActionButton")
        open_button.clicked.connect(self._on_open_source)
        source_bar.addWidget(open_button)
        scroll_layout.addLayout(source_bar)

        # 播放/暂停/停止/关闭
        playback_bar = QHBoxLayout()
        playback_bar.setSpacing(8)

        play_button = QPushButton("▶ 播放")
        play_button.setObjectName("ActionButton")
        play_button.clicked.connect(lambda: self._on_control("play"))
        playback_bar.addWidget(play_button)

        pause_button = QPushButton("⏸ 暂停")
        pause_button.setObjectName("SecondaryButton")
        pause_button.clicked.connect(lambda: self._on_control("pause"))
        playback_bar.addWidget(pause_button)

        stop_button = QPushButton("⏹ 停止")
        stop_button.setObjectName("SecondaryButton")
        stop_button.clicked.connect(lambda: self._on_control("stop"))
        playback_bar.addWidget(stop_button)

        close_button = QPushButton("关闭")
        close_button.setObjectName("DangerButton")
        close_button.clicked.connect(self._on_close_source)
        playback_bar.addWidget(close_button)

        scroll_layout.addLayout(playback_bar)

        # 导航控制（上一页/下一页）
        nav_bar = QHBoxLayout()
        nav_bar.setSpacing(8)

        prev_button = QPushButton("← 上一页")
        prev_button.setObjectName("SecondaryButton")
        prev_button.clicked.connect(lambda: self._on_navigate("prev"))
        nav_bar.addWidget(prev_button)

        next_button = QPushButton("下一页 →")
        next_button.setObjectName("SecondaryButton")
        next_button.clicked.connect(lambda: self._on_navigate("next"))
        nav_bar.addWidget(next_button)

        # 循环切换
        self._loop_button = QPushButton("循环")
        self._loop_button.setObjectName("SecondaryButton")
        self._loop_button.setCheckable(True)
        self._loop_button.clicked.connect(self._on_toggle_loop)
        nav_bar.addWidget(self._loop_button)

        nav_bar.addItem(
            QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        )
        scroll_layout.addLayout(nav_bar)

        # 弹性空间
        scroll_layout.addItem(
            QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        )

        scroll_area.setWidget(scroll_content)
        root_layout.addWidget(scroll_area, stretch=1)

    def _create_window_card(self, window_id: int) -> QFrame:
        """
        创建单个窗口状态卡片。
        :param window_id: 窗口编号（1-4）
        :return: 窗口卡片 QFrame
        """
        card_frame = QFrame()
        card_frame.setObjectName("WindowCard")
        card_layout = QVBoxLayout(card_frame)
        card_layout.setContentsMargins(10, 8, 10, 8)
        card_layout.setSpacing(4)

        # 窗口标题行
        window_title = QLabel(f"窗口 {window_id}")
        window_title_font = QFont("Microsoft YaHei", 13, QFont.Weight.Bold)
        window_title.setFont(window_title_font)
        window_title.setStyleSheet("color: #0078d4;")
        card_layout.addWidget(window_title)

        # 状态标签
        state_label = QLabel("空闲")
        state_label.setObjectName("StatusLabel")
        card_layout.addWidget(state_label)

        # 源名称标签
        source_label = QLabel("无内容")
        source_label.setObjectName("StatusLabel")
        source_label.setWordWrap(True)
        card_layout.addWidget(source_label)

        # 进度标签（PPT 页码 / 视频时间）
        progress_label = QLabel("")
        progress_label.setObjectName("StatusLabel")
        card_layout.addWidget(progress_label)

        # 保存引用
        self._window_cards[window_id] = {
            "frame": card_frame,
            "state": state_label,
            "source": source_label,
            "progress": progress_label,
        }
        return card_frame

    # ═══════════════════ 窗口选择 ═══════════════════

    def _select_window(self, window_id: int) -> None:
        """
        切换当前选中的目标窗口。
        :param window_id: 窗口编号（1-4）
        """
        self._selected_window = window_id
        for wid, button in self._window_buttons.items():
            button.setChecked(wid == window_id)
        logger.debug("控制面板选中窗口 %d", window_id)

    # ═══════════════════ 源管理 ═══════════════════

    def _refresh_source_list(self) -> None:
        """从 DB 刷新媒体源列表到下拉框。"""
        from scp_cv.services.media import list_media_sources

        sources = list_media_sources()
        self._cached_sources = [
            (source_item["id"], f'{source_item["name"]} ({source_item["source_type"]})')
            for source_item in sources
        ]

        self._source_combo.clear()
        for source_id, display_name in self._cached_sources:
            self._source_combo.addItem(display_name, userData=source_id)

    # ═══════════════════ 播放指令 ═══════════════════

    def _on_open_source(self) -> None:
        """打开选中的媒体源到当前窗口。"""
        source_id = self._source_combo.currentData()
        if source_id is None:
            logger.warning("未选择媒体源")
            return

        from scp_cv.services.playback import open_source
        from scp_cv.services.sse import publish_event
        from scp_cv.services.playback import get_session_snapshot

        try:
            open_source(self._selected_window, source_id, autoplay=True)
            snapshot = get_session_snapshot(self._selected_window)
            publish_event("playback_state", {
                "window_id": self._selected_window,
                **snapshot,
            })
            logger.info(
                "控制面板：窗口 %d 打开源 #%d",
                self._selected_window, source_id,
            )
        except Exception as open_err:
            logger.error("打开源失败：%s", open_err)

    def _on_control(self, action: str) -> None:
        """
        发送播放控制指令（play/pause/stop）。
        :param action: 动作名
        """
        from scp_cv.services.playback import control_playback
        from scp_cv.services.sse import publish_event
        from scp_cv.services.playback import get_session_snapshot

        try:
            control_playback(self._selected_window, action)
            snapshot = get_session_snapshot(self._selected_window)
            publish_event("playback_state", {
                "window_id": self._selected_window,
                **snapshot,
            })
        except Exception as ctrl_err:
            logger.error("播放控制失败：%s", ctrl_err)

    def _on_close_source(self) -> None:
        """关闭当前窗口的播放源。"""
        from scp_cv.services.playback import close_source
        from scp_cv.services.sse import publish_event
        from scp_cv.services.playback import get_session_snapshot

        try:
            close_source(self._selected_window)
            snapshot = get_session_snapshot(self._selected_window)
            publish_event("playback_state", {
                "window_id": self._selected_window,
                **snapshot,
            })
        except Exception as close_err:
            logger.error("关闭源失败：%s", close_err)

    def _on_navigate(self, action: str) -> None:
        """
        发送导航指令（next/prev）。
        :param action: 导航动作名
        """
        from scp_cv.services.playback import navigate_content

        try:
            navigate_content(self._selected_window, action)
        except Exception as nav_err:
            logger.error("导航失败：%s", nav_err)

    def _on_toggle_loop(self) -> None:
        """切换当前窗口的循环播放状态。"""
        from scp_cv.services.playback import toggle_loop_playback

        loop_enabled = self._loop_button.isChecked()
        try:
            toggle_loop_playback(self._selected_window, loop_enabled)
        except Exception as loop_err:
            logger.error("切换循环失败：%s", loop_err)

    # ═══════════════════ 全局操作 ═══════════════════

    @Slot()
    def _on_toggle_splice(self) -> None:
        """切换窗口 1+2 拼接模式。"""
        from scp_cv.services.playback import set_splice_mode
        from scp_cv.services.sse import publish_event
        from scp_cv.services.playback import get_all_sessions_snapshot

        splice_enabled = self._splice_button.isChecked()
        try:
            set_splice_mode(splice_enabled)
            all_snapshots = get_all_sessions_snapshot()
            publish_event("playback_state", {"sessions": all_snapshots})
        except Exception as splice_err:
            logger.error("切换拼接模式失败：%s", splice_err)
            # 恢复按钮状态
            self._splice_button.setChecked(not splice_enabled)

    @Slot()
    def _on_show_ids(self) -> None:
        """触发所有窗口显示 ID 覆盖层。"""
        from scp_cv.apps.playback.models import PlaybackCommand
        from scp_cv.services.playback import get_or_create_session, VALID_WINDOW_IDS

        for wid in VALID_WINDOW_IDS:
            session = get_or_create_session(wid)
            session.pending_command = PlaybackCommand.SHOW_ID
            session.save(update_fields=["pending_command"])
        logger.info("控制面板：已触发所有窗口显示 ID")

    # ═══════════════════ 状态轮询 ═══════════════════

    @Slot()
    def _poll_status(self) -> None:
        """定期从 DB 读取所有窗口状态并更新卡片 UI。"""
        from scp_cv.services.playback import get_all_sessions_snapshot, is_splice_mode_active

        try:
            snapshots = get_all_sessions_snapshot()
        except Exception as poll_err:
            logger.debug("状态轮询异常：%s", poll_err)
            return

        for snapshot in snapshots:
            window_id = snapshot.get("window_id")
            if window_id not in self._window_cards:
                continue

            card_refs = self._window_cards[window_id]
            playback_state = str(snapshot.get("playback_state", "IDLE"))
            state_display, state_color = _STATE_DISPLAY.get(
                playback_state, ("未知", "#526076")
            )

            card_refs["state"].setText(state_display)
            card_refs["state"].setStyleSheet(
                f"font-size: 12px; color: {state_color}; font-weight: 600;"
            )

            source_name = snapshot.get("source_name", "")
            card_refs["source"].setText(source_name if source_name else "无内容")

            # 进度信息
            progress_text = self._format_progress(snapshot)
            card_refs["progress"].setText(progress_text)

        # 更新拼接按钮状态
        try:
            splice_active = is_splice_mode_active()
            self._splice_button.setChecked(splice_active)
        except Exception:
            pass

    @staticmethod
    def _format_progress(snapshot: dict[str, object]) -> str:
        """
        根据快照格式化进度文本。
        :param snapshot: 会话快照
        :return: 进度描述字符串
        """
        total_slides = int(snapshot.get("total_slides", 0))
        if total_slides > 0:
            current = int(snapshot.get("current_slide", 0))
            return f"第 {current} / {total_slides} 页"

        duration_ms = int(snapshot.get("duration_ms", 0))
        if duration_ms > 0:
            position_ms = int(snapshot.get("position_ms", 0))
            pos_sec = position_ms // 1000
            dur_sec = duration_ms // 1000
            return (
                f"{pos_sec // 60:02d}:{pos_sec % 60:02d} / "
                f"{dur_sec // 60:02d}:{dur_sec % 60:02d}"
            )

        return ""

    # ═══════════════════ 生命周期 ═══════════════════

    def closeEvent(self, event: object) -> None:
        """面板关闭时停止轮询。"""
        self._poll_timer.stop()
        super().closeEvent(event)
