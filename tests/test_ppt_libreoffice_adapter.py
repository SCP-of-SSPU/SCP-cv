#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
LibreOffice PPT 适配器单元测试，覆盖动画推进、跳页和状态读取语义。
@Project : SCP-cv
@File : test_ppt_libreoffice_adapter.py
@Author : Qintsg
@Date : 2026-05-26
'''
from __future__ import annotations

import threading
from pathlib import Path

from pytest import MonkeyPatch

from scp_cv.player.adapters import ppt_libreoffice
from scp_cv.player.adapters.ppt_libreoffice import LibreOfficePptSourceAdapter


class _PresentationStub:
    """LibreOffice Presentation 替身。"""

    def __init__(self, running: bool = True) -> None:
        """
        初始化 Presentation 替身。
        :param running: 是否模拟正在放映
        :return: None
        """
        self.running = running
        self.AllowAnimations = False
        self.IsFullScreen = False
        self.IsAlwaysOnTop = True
        self.IsEndless = True
        self.IsMouseVisible = True
        self.StartWithNavigator = True
        self.Display = 0

    def isRunning(self) -> bool:
        """
        返回放映运行状态。
        :return: True 表示正在放映
        """
        return self.running


class _BlockingPresentationStub:
    """模拟 LibreOffice startWithArguments 同步阻塞的 Presentation。"""

    def __init__(self) -> None:
        """
        初始化阻塞 Presentation 替身。
        :return: None
        """
        self.start_called = False
        self.unblock_start = threading.Event()

    def startWithArguments(self, _args: tuple[object, ...]) -> None:
        """
        模拟阻塞的放映启动调用。
        :param _args: 启动参数
        :return: None
        """
        self.start_called = True
        self.unblock_start.wait(timeout=1.0)

    def getController(self) -> object | None:
        """
        启动调用进入后返回 controller。
        :return: controller 替身或 None
        """
        return _ControllerStub() if self.start_called else None


class _FailingPresentationStub:
    """模拟 LibreOffice 放映启动失败的 Presentation。"""

    def startWithArguments(self, _args: tuple[object, ...]) -> None:
        """
        抛出放映启动失败异常。
        :param _args: 启动参数
        :return: None
        """
        raise RuntimeError("start failed")

    def getController(self) -> object | None:
        """
        启动失败时不返回 controller。
        :return: None
        """
        return None


class _ControllerStub:
    """LibreOffice SlideShowController 替身。"""

    def __init__(self) -> None:
        """
        初始化控制器替身。
        :return: None
        """
        self.slide_index = 1
        self.paused = False
        self.next_effect_called = False
        self.previous_effect_called = False
        self.goto_indices: list[int] = []
        self.stop_sound_called = False
        self.slide_show = _SlideShowStub()
        self.current_slide = _ShapeContainerStub([])

    def gotoNextEffect(self) -> None:
        """
        记录下一动画调用。
        :return: None
        """
        self.next_effect_called = True
        self.slide_index += 1

    def gotoPreviousEffect(self) -> None:
        """
        记录上一动画调用。
        :return: None
        """
        self.previous_effect_called = True
        self.slide_index -= 1

    def gotoSlideIndex(self, index: int) -> None:
        """
        记录 0-based 跳页调用。
        :param index: 0-based 页码
        :return: None
        """
        self.goto_indices.append(index)
        self.slide_index = index

    def getCurrentSlideIndex(self) -> int:
        """
        返回当前 0-based 页码。
        :return: 当前页码
        """
        return self.slide_index

    def isPaused(self) -> bool:
        """
        返回暂停状态。
        :return: True 表示暂停
        """
        return self.paused

    def pause(self) -> None:
        """
        暂停放映。
        :return: None
        """
        self.paused = True

    def resume(self) -> None:
        """
        恢复放映。
        :return: None
        """
        self.paused = False

    def stopSound(self) -> None:
        """
        停止当前声音。
        :return: None
        """
        self.stop_sound_called = True

    def getSlideShow(self) -> object:
        """
        返回 SlideShow 替身。
        :return: SlideShow 替身
        """
        return self.slide_show

    def getCurrentSlide(self) -> object:
        """
        返回当前页替身。
        :return: 当前页 shape 容器
        """
        return self.current_slide


class _SlideShowStub:
    """LibreOffice XSlideShow 替身。"""

    def __init__(self) -> None:
        """
        初始化 SlideShow 替身。
        :return: None
        """
        self.started_shapes: list[object] = []
        self.stopped_shapes: list[object] = []
        self.pause_values: list[bool] = []

    def startShapeActivity(self, shape: object) -> bool:
        """
        记录媒体 shape 启动。
        :param shape: 媒体 shape
        :return: True 表示启动成功
        """
        self.started_shapes.append(shape)
        return True

    def stopShapeActivity(self, shape: object) -> bool:
        """
        记录媒体 shape 停止。
        :param shape: 媒体 shape
        :return: True 表示停止成功
        """
        self.stopped_shapes.append(shape)
        return True

    def pause(self, paused: bool) -> bool:
        """
        记录 slideshow 暂停/恢复。
        :param paused: True 表示暂停
        :return: True 表示操作成功
        """
        self.pause_values.append(paused)
        return True


class _MediaShapeStub:
    """LibreOffice 媒体 shape 替身。"""

    def __init__(self, media_url: str = "file:///demo.mp4", name: str = "media") -> None:
        """
        初始化媒体 shape。
        :param media_url: 媒体 URL
        :param name: shape 名称
        :return: None
        """
        self.MediaURL = media_url
        self.Name = name

    def getShapeType(self) -> str:
        """
        返回媒体 shape 类型。
        :return: LibreOffice shape type
        """
        return "com.sun.star.presentation.MediaShape"


class _BridgeStub:
    """LibreOffice bridge 客户端替身。"""

    instances: list["_BridgeStub"] = []

    def __init__(self, _logger: object) -> None:
        """
        初始化 bridge 替身。
        :param _logger: 日志器
        :return: None
        """
        self.open_calls: list[tuple[str, bool, int]] = []
        self.requests: list[tuple[str, dict[str, object] | None]] = []
        self.closed = False
        _BridgeStub.instances.append(self)

    def open(self, file_path: str, autoplay: bool, display_index: int = 0) -> dict[str, object]:
        """
        模拟打开 PPT。
        :param file_path: PPT 文件路径
        :param autoplay: 是否自动播放
        :param display_index: LibreOffice Display 序号
        :return: 状态数据
        """
        self.open_calls.append((file_path, autoplay, display_index))
        return {"playback_state": "playing", "current_slide": 1, "total_slides": 4, "process_id": 123}

    def request(self, command: str, payload: dict[str, object] | None = None) -> dict[str, object]:
        """
        模拟 bridge 命令。
        :param command: 命令名称
        :param payload: 命令参数
        :return: 状态数据
        """
        self.requests.append((command, payload))
        return {"playback_state": "playing", "current_slide": 2, "total_slides": 4, "process_id": 123}

    def close(self) -> None:
        """
        模拟关闭 bridge。
        :return: None
        """
        self.closed = True

    def close_document(self) -> dict[str, object]:
        """
        模拟关闭当前文档。
        :return: 状态数据
        """
        self.requests.append(("close_document", None))
        return {"playback_state": "idle", "current_slide": 0, "total_slides": 0, "process_id": 123}


class _ShapeContainerStub:
    """XShapes 容器替身。"""

    def __init__(self, shapes: list[object]) -> None:
        """
        初始化 shape 容器。
        :param shapes: shape 列表
        :return: None
        """
        self._shapes = shapes

    def getCount(self) -> int:
        """
        返回 shape 数量。
        :return: shape 数量
        """
        return len(self._shapes)

    def getByIndex(self, index: int) -> object:
        """
        返回指定 0-based shape。
        :param index: shape 序号
        :return: shape 对象
        """
        return self._shapes[index]


def test_next_item_uses_next_effect_to_preserve_animations() -> None:
    """下一项应调用 gotoNextEffect，而不是直接跳过动画到下一页。"""
    adapter = LibreOfficePptSourceAdapter()
    controller = _ControllerStub()
    adapter._presentation = _PresentationStub()
    adapter._controller = controller
    adapter._total_slides = 5

    adapter.next_item()

    assert controller.next_effect_called is True
    assert adapter._last_slide_index == 3


def test_open_uses_bridge_client_and_presents_external_window(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    """LibreOffice 打开路径应走 bridge，并将放映窗口铺满目标区域。"""
    ppt_file = tmp_path / "demo.pptx"
    ppt_file.write_text("placeholder", encoding="utf-8")
    calls: list[object] = []
    _BridgeStub.instances.clear()

    def fail_start_session(**_kwargs: object) -> object:
        """
        确认不会调用项目 Python 内的 pyuno 启动路径。
        :param _kwargs: 启动参数
        :return: 不返回
        """
        raise AssertionError("should use LibreOffice bridge")

    monkeypatch.setattr(ppt_libreoffice, "LibreOfficeBridgeClient", _BridgeStub)
    monkeypatch.setattr(ppt_libreoffice, "libreoffice_display_index_from_anchor_window", lambda _hwnd: 2)
    monkeypatch.setattr(ppt_libreoffice.lo_runtime, "start_libreoffice_session", fail_start_session)
    monkeypatch.setattr(ppt_libreoffice.lo_window, "snapshot_libreoffice_hwnds", lambda *_args, **_kwargs: {1})
    monkeypatch.setattr(ppt_libreoffice.lo_window, "find_libreoffice_slideshow_hwnd", lambda *_args, **_kwargs: 99)
    monkeypatch.setattr(ppt_libreoffice, "present_external_slideshow_window", lambda *args: calls.append(args) or (800, 600))

    adapter = LibreOfficePptSourceAdapter()
    adapter.open(str(ppt_file), window_handle=1001, autoplay=True)

    assert adapter.get_state().total_slides == 4
    assert _BridgeStub.instances[0].open_calls == [(str(ppt_file), True, 2)]
    assert calls == [(99, 1001)]


def test_open_falls_back_to_new_window_search_when_process_filter_misses(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    """按 bridge 进程过滤找不到窗口时，应回退到本次新增窗口查找。"""
    ppt_file = tmp_path / "demo.pptx"
    ppt_file.write_text("placeholder", encoding="utf-8")
    calls: list[object] = []
    find_calls: list[tuple[object, object]] = []
    _BridgeStub.instances.clear()

    def find_hwnd_stub(*_args: object, **kwargs: object) -> int:
        """
        首次按进程过滤失败，回退到新增窗口查找成功。
        :param _args: 位置参数
        :param kwargs: 关键字参数
        :return: HWND
        """
        find_calls.append((kwargs.get("process_id"), kwargs.get("timeout_seconds")))
        return 0 if kwargs.get("process_id") else 99

    monkeypatch.setattr(ppt_libreoffice, "LibreOfficeBridgeClient", _BridgeStub)
    monkeypatch.setattr(ppt_libreoffice, "libreoffice_display_index_from_anchor_window", lambda _hwnd: 2)
    monkeypatch.setattr(ppt_libreoffice.lo_window, "snapshot_libreoffice_hwnds", lambda *_args, **_kwargs: {1})
    monkeypatch.setattr(ppt_libreoffice.lo_window, "find_libreoffice_slideshow_hwnd", find_hwnd_stub)
    monkeypatch.setattr(ppt_libreoffice, "present_external_slideshow_window", lambda *args: calls.append(args) or (800, 600))

    adapter = LibreOfficePptSourceAdapter()
    adapter.open(str(ppt_file), window_handle=1001, autoplay=True)

    assert find_calls == [(123, 1.5), (None, 12.0)]
    assert calls == [(99, 1001)]


def test_start_slideshow_does_not_block_on_libreoffice_start(monkeypatch: MonkeyPatch) -> None:
    """播放器内 LibreOffice 放映启动不应被 startWithArguments 同步阻塞。"""
    calls: list[object] = []
    presentation = _BlockingPresentationStub()
    adapter = LibreOfficePptSourceAdapter()
    adapter._presentation = presentation
    adapter._window_handle = 1001
    adapter._total_slides = 3
    monkeypatch.setattr(ppt_libreoffice.lo_window, "snapshot_libreoffice_hwnds", lambda *_args, **_kwargs: {1})
    monkeypatch.setattr(ppt_libreoffice.lo_window, "find_libreoffice_slideshow_hwnd", lambda *_args, **_kwargs: 99)
    monkeypatch.setattr(ppt_libreoffice, "present_external_slideshow_window", lambda *args: calls.append(args) or (800, 600))

    adapter._start_slideshow(1)
    presentation.unblock_start.set()

    assert adapter._controller is not None
    assert presentation.start_called is True
    assert calls == [(99, 1001)]


def test_configure_presentation_uses_fullscreen_slideshow_window(monkeypatch: MonkeyPatch) -> None:
    """LibreOffice 应使用全屏放映路径创建真实外部窗口。"""
    presentation = _PresentationStub()
    adapter = LibreOfficePptSourceAdapter()
    adapter._presentation = presentation
    adapter._window_handle = 1001
    monkeypatch.setattr(ppt_libreoffice, "libreoffice_display_index_from_anchor_window", lambda _hwnd: 2)

    adapter._configure_presentation()

    assert presentation.AllowAnimations is True
    assert presentation.IsFullScreen is True
    assert presentation.IsAlwaysOnTop is False
    assert presentation.IsEndless is False
    assert presentation.IsMouseVisible is False
    assert presentation.StartWithNavigator is False
    assert presentation.Display == 2


def test_start_slideshow_reports_async_start_error(monkeypatch: MonkeyPatch) -> None:
    """播放器内 LibreOffice 异步启动失败时应快速抛出明确错误。"""
    adapter = LibreOfficePptSourceAdapter()
    adapter._presentation = _FailingPresentationStub()
    adapter._window_handle = 1001
    adapter._total_slides = 3
    monkeypatch.setattr(ppt_libreoffice.lo_window, "snapshot_libreoffice_hwnds", lambda *_args, **_kwargs: {1})

    try:
        adapter._start_slideshow(1)
    except ppt_libreoffice.lo_runtime.LibreOfficeError as start_error:
        assert "LibreOffice 放映启动失败" in str(start_error)
        assert "start failed" in str(start_error)
    else:
        raise AssertionError("expected LibreOfficeError")


def test_close_drops_preheated_bridge_when_close_document_fails() -> None:
    """预热 bridge 关闭文档失败时不应把坏实例放回池。"""

    class FailingBridge(_BridgeStub):
        """关闭文档失败的 bridge 替身。"""

        def close_document(self) -> dict[str, object]:
            """
            模拟 LibreOffice 全屏关闭文档超时失败。
            :return: 不返回
            :raises RuntimeError: 模拟关闭失败
            """
            raise RuntimeError("close timeout")

    class PoolStub:
        """预热池替身。"""

        def __init__(self) -> None:
            """初始化返回记录。"""
            self.returned: list[object] = []

        def return_libreoffice_bridge(self, bridge: object) -> None:
            """
            记录被放回的 bridge。
            :param bridge: bridge 实例
            :return: None
            """
            self.returned.append(bridge)

    bridge = FailingBridge(None)
    pool = PoolStub()
    adapter = LibreOfficePptSourceAdapter()
    adapter._bridge = bridge
    adapter._using_preheated_bridge = True
    adapter._preheat_pool = pool

    adapter.close()

    assert bridge.closed is True
    assert pool.returned == []


def test_prev_item_uses_previous_effect_to_preserve_animations() -> None:
    """上一项应调用 gotoPreviousEffect，保持动画级回退能力。"""
    adapter = LibreOfficePptSourceAdapter()
    controller = _ControllerStub()
    adapter._presentation = _PresentationStub()
    adapter._controller = controller
    adapter._total_slides = 5

    adapter.prev_item()

    assert controller.previous_effect_called is True
    assert adapter._last_slide_index == 1


def test_goto_item_uses_zero_based_libreoffice_index() -> None:
    """跳页应把前端 1-based 页码转换为 LibreOffice 0-based 页码。"""
    adapter = LibreOfficePptSourceAdapter()
    controller = _ControllerStub()
    adapter._presentation = _PresentationStub()
    adapter._controller = controller
    adapter._total_slides = 5

    adapter.goto_item(4)

    assert controller.goto_indices == [3]
    assert adapter._last_slide_index == 4


def test_get_state_reports_one_based_slide_and_pause_state() -> None:
    """状态上报应把 LibreOffice 0-based 当前页转换为 1-based。"""
    adapter = LibreOfficePptSourceAdapter()
    controller = _ControllerStub()
    controller.slide_index = 2
    controller.paused = True
    adapter._presentation = _PresentationStub()
    adapter._controller = controller
    adapter._total_slides = 5

    state = adapter.get_state()

    assert state.playback_state == "paused"
    assert state.current_slide == 3
    assert state.total_slides == 5


def test_control_media_starts_selected_media_shape_activity() -> None:
    """LibreOffice 媒体播放应启动指定媒体 shape 的内在活动。"""
    adapter = LibreOfficePptSourceAdapter()
    controller = _ControllerStub()
    media_shape_1 = _MediaShapeStub(media_url="file:///a.mp4", name="a")
    media_shape_2 = _MediaShapeStub(media_url="file:///b.mp4", name="b")
    controller.current_slide = _ShapeContainerStub([media_shape_1, media_shape_2])
    adapter._presentation = _PresentationStub()
    adapter._controller = controller
    adapter._total_slides = 5

    adapter.control_media("page-1-media-2", "play", media_index=2)

    assert controller.next_effect_called is False
    assert controller.slide_show.pause_values == [False]
    assert controller.slide_show.started_shapes == [media_shape_2]


def test_control_media_pauses_and_stops_selected_media_shape() -> None:
    """LibreOffice 媒体暂停和停止应走 XSlideShow shape activity。"""
    adapter = LibreOfficePptSourceAdapter()
    controller = _ControllerStub()
    media_shape = _MediaShapeStub(media_url="file:///a.mp4", name="a")
    controller.current_slide = _ShapeContainerStub([media_shape])
    adapter._presentation = _PresentationStub()
    adapter._controller = controller
    adapter._total_slides = 5

    adapter.control_media("page-1-media-1", "pause", media_index=1)
    adapter.control_media("page-1-media-1", "stop", media_index=1)

    assert controller.slide_show.pause_values == [True]
    assert controller.slide_show.stopped_shapes == [media_shape]
