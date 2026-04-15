#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
SRT 流适配器：通过 mpv/libmpv 直接播放 MediaMTX SRT 流。
路径：OBS → SRT → MediaMTX → SRT read → mpv/libmpv → PySide6 QWidget

低延迟策略：
- mpv low-latency profile: 禁用缓冲、启用 untimed 模式
- demuxer_lavf_o='fflags=+nobuffer': FFmpeg 无缓冲读取
- cache='no': 完全禁用缓存
- SRT latency=30000 (30ms): OBS 端最低延迟配置

线程模型：
- open() 在 Qt 主线程中调用（由 PlayerController 保证）
- mpv 内部使用独立渲染线程，通过 wid 参数嵌入 Qt 容器
@Project : SCP-cv
@File : srt_stream.py
@Author : Qintsg
@Date : 2026-05-12
'''
from __future__ import annotations

import locale
import logging
import os
from pathlib import Path
from typing import Optional

from scp_cv.player.adapters.base import AdapterState, SourceAdapter

logger = logging.getLogger(__name__)

# mpv/libmpv 要求 LC_NUMERIC 设为 C，否则浮点参数解析出错
locale.setlocale(locale.LC_NUMERIC, "C")

# 将 libmpv-2.dll 所在目录加入 PATH，确保 python-mpv 可找到动态库
_MPV_LIB_DIR = Path(__file__).resolve().parents[3] / "tools" / "third_party" / "mpv"
if _MPV_LIB_DIR.is_dir():
    os.environ["PATH"] = str(_MPV_LIB_DIR) + os.pathsep + os.environ.get("PATH", "")
    logger.debug("已将 mpv 库目录加入 PATH：%s", _MPV_LIB_DIR)

# 延迟导入 mpv（需要 libmpv-2.dll 在 PATH 中）
import mpv  # noqa: E402


class SrtStreamAdapter(SourceAdapter):
    """
    SRT 流播放适配器，使用 mpv/libmpv 直接播放 SRT 流。

    通过 MediaMTX 的 SRT 读取端拉取流，利用 mpv 内置硬件加速
    解码和 GPU 渲染。延迟目标 < 200ms。

    嵌入方式：
    - 通过 wid 参数将 mpv 渲染输出嵌入 PySide6 QWidget
    - mpv 自行管理渲染线程，无需手动帧传递
    """

    def __init__(self) -> None:
        super().__init__(adapter_name="srt_stream")
        self._player: Optional[mpv.MPV] = None
        self._srt_url: str = ""
        self._window_handle: int = 0
        self._is_connected: bool = False

    def open(self, uri: str, window_handle: int, autoplay: bool = True) -> None:
        """
        启动 SRT 流播放。mpv 嵌入到指定 Qt 原生窗口容器中。
        :param uri: SRT 流 URL（如 srt://127.0.0.1:8890?streamid=read:test&latency=30000）
        :param window_handle: 渲染目标窗口的原生句柄（由 PlayerWindow 提供）
        :param autoplay: 是否自动开始播放
        """
        self._srt_url = uri
        self._window_handle = window_handle
        self._release_player()

        # 创建 mpv 实例，嵌入到 Qt 窗口容器
        self._player = mpv.MPV(
            wid=str(window_handle),
            # 低延迟核心参数
            profile="low-latency",
            cache="no",
            untimed=True,
            # FFmpeg demuxer 级别禁用缓冲
            demuxer_lavf_o="fflags=+nobuffer",
            # GPU 渲染 + 硬件解码
            vo="gpu",
            hwdec="auto",
            # 音频配置
            audio_client_name="SCP-cv",
            # 日志（通过 python-mpv 回调收集）
            log_handler=self._on_mpv_log,
            loglevel="warn",
        )

        # 注册属性观察器：核心播放状态追踪
        self._player.observe_property("core-idle", self._on_core_idle_changed)

        self._mark_open()
        self._logger.info("SRT 流已配置（mpv wid=%d）：%s", window_handle, uri)

        if autoplay:
            self._player.play(uri)
            self._logger.info("SRT 流正在连接播放")

    def _on_mpv_log(self, loglevel: str, component: str, message: str) -> None:
        """
        mpv 日志回调，转发到 Python logging。
        :param loglevel: mpv 日志级别（error/warn/info/debug 等）
        :param component: mpv 组件名
        :param message: 日志消息
        """
        log_message = f"[mpv/{component}] {message.rstrip()}"
        if loglevel in ("error", "fatal"):
            self._logger.error(log_message)
        elif loglevel == "warn":
            self._logger.warning(log_message)
        else:
            self._logger.debug(log_message)

    def _on_core_idle_changed(self, _property_name: str, idle_active: Optional[bool]) -> None:
        """
        mpv core-idle 属性变更回调：检测播放是否活跃。
        core-idle=False 表示正在解码/渲染帧；True 表示空闲。
        :param _property_name: 属性名（固定为 "core-idle"）
        :param idle_active: True=空闲，False=播放中
        """
        if idle_active is False:
            # mpv 开始解码帧 → 流已连接
            if not self._is_connected:
                self._is_connected = True
                self._logger.info("SRT 流已连接（首帧已解码）")
        elif idle_active is True and self._is_connected:
            self._logger.debug("SRT 流进入空闲（可能暂停或断流）")

    def _release_player(self) -> None:
        """释放 mpv 实例及关联资源。"""
        if self._player is not None:
            try:
                self._player.terminate()
            except mpv.ShutdownError:
                # mpv 已经在关闭过程中，忽略
                pass
            except Exception as release_error:
                self._logger.warning("释放 mpv 时异常：%s", release_error)
            self._player = None
        self._is_connected = False

    def close(self) -> None:
        """断开 SRT 流并释放 mpv 资源。"""
        self._release_player()
        self._mark_closed()
        self._logger.info("SRT 流已断开")

    # ═══════════════════ 播放控制 ═══════════════════

    def play(self) -> None:
        """恢复播放或重新连接流。"""
        if self._player is not None:
            # mpv 已暂停 → 恢复
            if self._player.pause:
                self._player.pause = False
            else:
                # 重新播放 URL
                self._player.play(self._srt_url)
        elif self._srt_url and self._window_handle:
            # 播放器已释放，重新创建
            self.open(self._srt_url, self._window_handle, autoplay=True)

    def pause(self) -> None:
        """暂停播放（SRT 直播流暂停后恢复可能重新缓冲）。"""
        if self._player is not None:
            self._player.pause = True

    def stop(self) -> None:
        """停止流接收（不释放 mpv 实例）。"""
        if self._player is not None:
            self._player.command("stop")
            self._is_connected = False

    # ═══════════════════ 状态获取 ═══════════════════

    def get_state(self) -> AdapterState:
        """
        获取 SRT 流状态快照。
        :return: 流连接状态（playing/loading/stopped）
        """
        if self._player is not None and self._is_connected:
            return AdapterState(playback_state="playing")

        if self._player is not None:
            return AdapterState(playback_state="loading")

        return AdapterState(playback_state="stopped")

    # ═══════════════════ 窗口适配 ═══════════════════

    def resize_output(self, width: int, height: int) -> None:
        """
        mpv 通过 wid 嵌入时自动跟随容器尺寸，无需手动调整。
        保留此方法以与 RtspStreamAdapter 接口一致。
        :param width: 新宽度（未使用）
        :param height: 新高度（未使用）
        """
        # mpv 嵌入模式下自动适应容器尺寸，无需操作
        pass
