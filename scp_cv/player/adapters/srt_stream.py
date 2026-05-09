#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
SRT 流适配器：通过 libVLC 直接播放 MediaMTX SRT 流。
路径：OBS → SRT → MediaMTX → SRT read → libVLC → PySide6 QWidget

低延迟策略：
- libVLC 使用 Direct3D11 输出与硬件解码
- network/live caching 降低到现场播放可接受范围
- drop-late-frames / skip-frames 优先追实时画面
- SRT read latency=50: libVLC 读端请求低延迟，MediaMTX 通常收敛到约 120ms

线程模型：
- open() 在 Qt 主线程中调用（由 PlayerController 保证）
- libVLC 内部使用独立解码/渲染线程，通过 HWND 嵌入 Qt 容器
@Project : SCP-cv
@File : srt_stream.py
@Author : Qintsg
@Date : 2026-05-12
'''
from __future__ import annotations

import logging
import os
import time
from pathlib import Path

from scp_cv.player.adapters.base import AdapterState, SourceAdapter
from scp_cv.player.gpu_detector import get_vlc_gpu_options

logger = logging.getLogger(__name__)

_VLC_RUNTIME_DIR = Path(__file__).resolve().parents[3] / "tools" / "third_party" / "vlc"
_VLC_DLL_DIRECTORY_HANDLES: list[object] = []

# libVLC 连接 SRT 读端时可能在首帧前先抛一次错误事件；
# 这段窗口内先保持 loading，避免控制台把正常握手误判为异常。
_TRANSIENT_ERROR_GRACE_SECONDS = 5.0


def _candidate_vlc_runtime_dirs() -> list[Path]:
    """
    枚举 libVLC 运行时目录候选位置。
    :return: 按优先级排列的 VLC runtime 目录列表
    """
    candidate_dirs = [
        _VLC_RUNTIME_DIR / "runtime",
        _VLC_RUNTIME_DIR,
    ]

    for env_name in ("ProgramFiles", "ProgramFiles(x86)"):
        program_files_dir = os.environ.get(env_name)
        if program_files_dir:
            candidate_dirs.append(Path(program_files_dir) / "VideoLAN" / "VLC")

    return candidate_dirs


def _configure_vlc_runtime_paths() -> Path | None:
    """
    将可用 libVLC 目录加入 DLL 搜索路径。
    :return: 命中的 libVLC 目录；未命中时返回 None，由 python-vlc 继续按系统 PATH 查找
    """
    for runtime_dir in _candidate_vlc_runtime_dirs():
        libvlc_path = runtime_dir / "libvlc.dll"
        if not libvlc_path.is_file():
            continue

        runtime_path = str(runtime_dir)
        if os.name == "nt" and hasattr(os, "add_dll_directory"):
            _VLC_DLL_DIRECTORY_HANDLES.append(os.add_dll_directory(runtime_path))
        os.environ["PATH"] = runtime_path + os.pathsep + os.environ.get("PATH", "")

        plugin_dir = runtime_dir / "plugins"
        if plugin_dir.is_dir():
            os.environ.setdefault("VLC_PLUGIN_PATH", str(plugin_dir))

        logger.debug("已配置 libVLC 运行时目录：%s", runtime_dir)
        return runtime_dir

    logger.debug("未发现项目内置 libVLC，继续使用系统 PATH 查找")
    return None


_ACTIVE_VLC_RUNTIME_DIR = _configure_vlc_runtime_paths()

try:
    import vlc  # noqa: E402
except (ImportError, OSError) as vlc_import_error:
    vlc = None
    _VLC_IMPORT_ERROR: BaseException | None = vlc_import_error
else:
    _VLC_IMPORT_ERROR = None


def _build_vlc_instance_args() -> list[str]:
    """
    生成 libVLC 实例级参数。
    :return: 可传给 vlc.Instance() 的参数列表
    """
    instance_args = [
        "--no-video-title-show",
        "--no-snapshot-preview",
        "--network-caching=50",
        "--live-caching=50",
        "--file-caching=0",
        "--clock-jitter=0",
        "--clock-synchro=0",
        "--drop-late-frames",
        "--skip-frames",
    ]

    instance_args.extend(get_vlc_gpu_options())
    return instance_args


def _build_srt_media_options() -> list[str]:
    """
    生成 SRT 直播源媒体级参数。
    :return: 可传给 media.add_option() 的参数列表
    """
    return [
        ":network-caching=50",
        ":live-caching=50",
        ":clock-jitter=0",
        ":clock-synchro=0",
        ":drop-late-frames",
        ":skip-frames",
    ]


class SrtStreamAdapter(SourceAdapter):
    """
    SRT 流播放适配器，使用 libVLC 直接播放 SRT 流。

    通过 MediaMTX 的 SRT 读取端拉取流，利用 VLC 的 SRT、解码和
    Direct3D11 渲染能力嵌入到 PySide6 窗口。延迟目标 < 200ms。

    嵌入方式：
    - Windows 下通过 set_hwnd() 将渲染输出绑定到 Qt 原生 HWND
    - libVLC 自行管理解码/渲染线程，无需手动帧传递
    """

    def __init__(self) -> None:
        super().__init__(adapter_name="srt_stream")
        self._instance: object | None = None
        self._player: object | None = None
        self._media: object | None = None
        self._event_manager: object | None = None
        self._event_callbacks: list[tuple[object, object]] = []
        self._srt_url: str = ""
        self._window_handle: int = 0
        self._is_connected: bool = False
        self._has_error: bool = False
        self._error_message: str = ""
        self._opened_at_monotonic: float = 0.0
        self._last_error_at_monotonic: float = 0.0

    def open(self, uri: str, window_handle: int, autoplay: bool = True) -> None:
        """
        启动 SRT 流播放。libVLC 嵌入到指定 Qt 原生窗口容器中。
        :param uri: SRT 流 URL（如 srt://127.0.0.1:8890?streamid=read:test&latency=50）
        :param window_handle: 渲染目标窗口的原生句柄（由 PlayerWindow 提供）
        :param autoplay: 是否自动开始播放
        """
        if vlc is None:
            raise RuntimeError(
                "libVLC 初始化失败，请安装系统 VLC，或将 VLC 运行时解压到 tools/third_party/vlc/runtime/"
            ) from _VLC_IMPORT_ERROR

        self._srt_url = uri
        self._window_handle = window_handle
        self._release_player()
        self._has_error = False
        self._error_message = ""
        self._opened_at_monotonic = time.monotonic()
        self._last_error_at_monotonic = 0.0

        vlc_args = _build_vlc_instance_args()
        self._instance = vlc.Instance(vlc_args)
        if self._instance is None:
            raise RuntimeError("libVLC 实例创建失败")

        self._player = self._instance.media_player_new()
        if self._player is None:
            raise RuntimeError("libVLC 播放器创建失败")

        # Windows 下将 libVLC 渲染输出嵌入 Qt QWidget 对应的 HWND。
        set_hwnd = getattr(self._player, "set_hwnd", None)
        if callable(set_hwnd):
            set_hwnd(window_handle)
        else:
            self._logger.warning("当前 libVLC 绑定不支持 set_hwnd，无法嵌入窗口")

        self._media = self._instance.media_new(uri)
        for media_option in _build_srt_media_options():
            self._media.add_option(media_option)
        self._player.set_media(self._media)
        self._register_player_events()

        self._mark_open()
        self._logger.info("SRT 流已配置（libVLC hwnd=%d）：%s", window_handle, uri)

        if autoplay:
            self.play()
            self._logger.info("SRT 流正在连接播放")

    def _register_player_events(self) -> None:
        """注册 libVLC 播放状态事件，用于同步连接与错误状态。"""
        if self._player is None or vlc is None:
            return

        self._event_manager = self._player.event_manager()
        event_specs = [
            (vlc.EventType.MediaPlayerPlaying, self._on_vlc_playing),
            (vlc.EventType.MediaPlayerEncounteredError, self._on_vlc_error),
            (vlc.EventType.MediaPlayerStopped, self._on_vlc_stopped),
            (vlc.EventType.MediaPlayerEndReached, self._on_vlc_stopped),
        ]

        for event_type, callback in event_specs:
            try:
                self._event_manager.event_attach(event_type, callback)
                self._event_callbacks.append((event_type, callback))
            except Exception as event_error:
                self._logger.debug("注册 libVLC 事件失败：%s", event_error)

    def _on_vlc_playing(self, _event: object) -> None:
        """
        libVLC 播放开始事件。
        :param _event: libVLC 事件对象（当前仅用于触发状态同步）
        """
        if not self._is_connected:
            self._logger.info("SRT 流已连接（libVLC 已开始渲染）")
        self._is_connected = True
        self._clear_transient_error()

    def _on_vlc_error(self, _event: object) -> None:
        """
        libVLC 播放错误事件。
        :param _event: libVLC 事件对象（当前仅用于触发状态同步）
        """
        self._mark_vlc_error("libVLC 播放 SRT 流失败")

    def _on_vlc_stopped(self, _event: object) -> None:
        """
        libVLC 播放停止事件。
        :param _event: libVLC 事件对象（当前仅用于触发状态同步）
        """
        self._is_connected = False

    def _mark_vlc_error(self, error_message: str) -> None:
        """
        记录 libVLC 错误状态。
        :param error_message: 可上报到播放状态的错误信息
        """
        self._has_error = True
        self._error_message = error_message
        self._last_error_at_monotonic = time.monotonic()
        self._is_connected = False
        self._logger.error(error_message)

    def _clear_transient_error(self) -> None:
        """清理已经被 libVLC 正常播放状态覆盖的瞬时错误。"""
        self._has_error = False
        self._error_message = ""
        self._last_error_at_monotonic = 0.0

    def _is_in_error_grace_period(self) -> bool:
        """
        判断当前错误是否仍处在直播首帧/重连宽限窗口。
        :return: True 表示暂不上报 error，继续让前端显示 loading
        """
        if self._opened_at_monotonic <= 0:
            return False
        return time.monotonic() - self._opened_at_monotonic < _TRANSIENT_ERROR_GRACE_SECONDS

    def _release_player(self) -> None:
        """释放 libVLC 实例及关联资源。"""
        if self._event_manager is not None:
            detach_event = getattr(self._event_manager, "event_detach", None)
            if callable(detach_event):
                for event_type, callback in self._event_callbacks:
                    try:
                        detach_event(event_type)
                    except TypeError:
                        detach_event(event_type, callback)
                    except Exception as detach_error:
                        self._logger.debug("注销 libVLC 事件失败：%s", detach_error)
        self._event_callbacks.clear()
        self._event_manager = None

        if self._player is not None:
            try:
                self._player.stop()
                self._player.set_media(None)
                self._player.release()
            except Exception as release_error:
                self._logger.warning("释放 libVLC 播放器时异常：%s", release_error)
            self._player = None

        if self._media is not None:
            try:
                self._media.release()
            except Exception as release_error:
                self._logger.debug("释放 libVLC 媒体对象时异常：%s", release_error)
            self._media = None

        if self._instance is not None:
            try:
                self._instance.release()
            except Exception as release_error:
                self._logger.debug("释放 libVLC 实例时异常：%s", release_error)
            self._instance = None

        self._is_connected = False

    def close(self) -> None:
        """断开 SRT 流并释放 libVLC 资源。"""
        self._release_player()
        self._mark_closed()
        self._logger.info("SRT 流已断开")

    # ═══════════════════ 播放控制 ═══════════════════

    def play(self) -> None:
        """恢复播放或重新连接流。"""
        if self._player is not None:
            self._has_error = False
            self._error_message = ""
            play_result = self._player.play()
            if isinstance(play_result, int) and play_result < 0:
                self._mark_vlc_error("libVLC play() 返回失败")
        elif self._srt_url and self._window_handle:
            # 播放器已释放，重新创建并立即播放。
            self.open(self._srt_url, self._window_handle, autoplay=True)

    def pause(self) -> None:
        """暂停播放（SRT 直播流暂停后恢复可能重新缓冲）。"""
        if self._player is not None:
            self._player.set_pause(True)

    def stop(self) -> None:
        """停止流接收（不释放 libVLC 实例）。"""
        if self._player is not None:
            self._player.stop()
            self._is_connected = False

    def set_volume(self, volume: int) -> None:
        """
        设置 SRT/libVLC 音量。
        :param volume: 音量等级（0-100）
        """
        if self._player is not None:
            self._player.audio_set_volume(max(0, min(100, int(volume))))

    def set_mute(self, muted: bool) -> None:
        """
        设置 SRT/libVLC 静音状态。
        :param muted: 是否静音
        """
        if self._player is not None:
            self._player.audio_set_mute(muted)

    # ═══════════════════ 状态获取 ═══════════════════

    def get_state(self) -> AdapterState:
        """
        获取 SRT 流状态快照。
        :return: 流连接状态（playing/loading/paused/stopped/error）
        """
        if self._player is None or vlc is None:
            return AdapterState(playback_state="stopped")

        current_state = self._player.get_state()
        if current_state == vlc.State.Playing:
            self._is_connected = True
            self._clear_transient_error()
            playback_state = "playing"
        elif current_state == vlc.State.Paused:
            self._clear_transient_error()
            playback_state = "paused"
        elif current_state in (vlc.State.Opening, vlc.State.Buffering):
            playback_state = "loading"
        elif current_state == vlc.State.Error:
            if self._is_in_error_grace_period():
                playback_state = "loading"
            else:
                return AdapterState(
                    playback_state="error",
                    error_message=self._error_message or "libVLC 播放状态异常",
                )
        elif self._has_error:
            if self._is_in_error_grace_period():
                playback_state = "loading"
            else:
                return AdapterState(
                    playback_state="error",
                    error_message=self._error_message,
                )
        elif current_state in (vlc.State.Stopped, vlc.State.Ended):
            playback_state = "stopped"
        elif self._is_connected:
            playback_state = "playing"
        else:
            playback_state = "loading"

        return AdapterState(
            playback_state=playback_state,
            position_ms=self._read_player_millis("get_time"),
            duration_ms=self._read_player_millis("get_length"),
        )

    def _read_player_millis(self, method_name: str) -> int:
        """
        安全读取 libVLC 毫秒级时间字段。
        :param method_name: libVLC MediaPlayer 方法名
        :return: 非负毫秒数；直播流未知时返回 0
        """
        if self._player is None:
            return 0

        try:
            method = getattr(self._player, method_name)
            raw_value = int(method())
        except Exception:
            return 0
        return max(0, raw_value)

    # ═══════════════════ 窗口适配 ═══════════════════

    def resize_output(self, width: int, height: int) -> None:
        """
        libVLC 嵌入 HWND 后自动跟随容器尺寸，无需手动调整。
        保留此方法以与 RtspStreamAdapter 接口一致。
        :param width: 新宽度（未使用）
        :param height: 新高度（未使用）
        """
        # libVLC 嵌入模式下自动适应容器尺寸，无需操作。
        pass
