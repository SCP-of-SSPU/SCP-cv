#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PPT 文件级预热单元测试。
@Project : SCP-cv
@File : test_ppt_file_preheat.py
@Author : Qintsg
@Date : 2026-05-31
'''
from __future__ import annotations

import sys
import types

from pytest import MonkeyPatch

from scp_cv.player.adapters import ppt
from scp_cv.player.adapters.ppt import PptSourceAdapter
from scp_cv.player.preheat_ppt import PptApplicationPreheater
from scp_cv.player.preheat_types import PreheatedPptApplication
from scp_cv.ppt_com import POWERPOINT_COM_PROG_IDS


class _PresentationStub:
    """记录 Presentation 状态的测试替身。"""

    def __init__(self) -> None:
        """
        初始化演示文稿替身。
        :return: None
        """
        self.Saved = False
        self.close_called = False
        self.close_args: tuple[object, ...] = ()
        self.Slides = type("_SlidesStub", (), {"Count": 6})()

    def Close(self, *args: object) -> None:
        """
        记录关闭参数。
        :param args: COM Close 参数
        :return: None
        """
        self.close_called = True
        self.close_args = args


class _PresentationsStub:
    """记录 Presentations.Open 调用。"""

    def __init__(self, presentation: _PresentationStub) -> None:
        """
        初始化集合替身。
        :param presentation: 打开时返回的演示文稿替身
        :return: None
        """
        self.presentation = presentation
        self.calls: list[tuple[str, tuple[object, ...], dict[str, object]]] = []

    def Open(self, uri: str, *args: object, **kwargs: object) -> _PresentationStub:
        """
        模拟 COM Open。
        :param uri: PPT 文件路径
        :param args: 位置参数
        :param kwargs: 关键字参数
        :return: 演示文稿替身
        """
        self.calls.append((uri, args, kwargs))
        return self.presentation


class _PptAppStub:
    """PowerPoint Application 替身。"""

    def __init__(self, presentation: _PresentationStub) -> None:
        """
        初始化应用替身。
        :param presentation: 打开时返回的演示文稿替身
        :return: None
        """
        self.DisplayAlerts = 2
        self.WindowState = 0
        self.quit_called = False
        self.Presentations = _PresentationsStub(presentation)

    def Quit(self) -> None:
        """
        记录退出调用。
        :return: None
        """
        self.quit_called = True


class _Win32ComClientStub:
    """win32com.client 替身。"""

    def __init__(self, app: _PptAppStub) -> None:
        """
        初始化 DispatchEx 记录。
        :param app: 要返回的应用替身
        :return: None
        """
        self.app = app
        self.calls: list[str] = []

    def DispatchEx(self, prog_id: str) -> _PptAppStub:
        """
        记录 ProgID 并返回应用替身。
        :param prog_id: COM ProgID
        :return: 应用替身
        """
        self.calls.append(prog_id)
        return self.app


class _PythonComStub:
    """pythoncom 替身。"""

    def __init__(self) -> None:
        """
        初始化 COM 生命周期计数。
        :return: None
        """
        self.initialized = 0
        self.uninitialized = 0

    def CoInitialize(self) -> None:
        """
        记录初始化调用。
        :return: None
        """
        self.initialized += 1

    def CoUninitialize(self) -> None:
        """
        记录释放调用。
        :return: None
        """
        self.uninitialized += 1


class _PreheatPoolStub:
    """适配器预热池替身。"""

    def __init__(self, item: PreheatedPptApplication) -> None:
        """
        初始化预热项。
        :param item: 预热应用项
        :return: None
        """
        self.item = item
        self.take_calls: list[tuple[int, str]] = []
        self.returned_items: list[PreheatedPptApplication] = []

    def take_ppt_application(self, source_id: int = 0, uri: str = "") -> PreheatedPptApplication | None:
        """
        记录取用参数并返回预热项。
        :param source_id: 媒体源 ID
        :param uri: PPT 文件路径
        :return: 预热应用项
        """
        self.take_calls.append((source_id, uri))
        item = self.item
        self.item = None  # type: ignore[assignment]
        return item

    def return_ppt_application(self, item: PreheatedPptApplication) -> None:
        """
        记录归还项。
        :param item: 预热应用项
        :return: None
        """
        self.returned_items.append(item)


def _install_com_stubs(monkeypatch: MonkeyPatch, app: _PptAppStub) -> tuple[_PythonComStub, _Win32ComClientStub]:
    """
    安装 pythoncom / win32com.client 测试替身。
    :param monkeypatch: pytest monkeypatch
    :param app: DispatchEx 返回的应用替身
    :return: pythoncom 与 win32com.client 替身
    """
    pythoncom_stub = _PythonComStub()
    win32_client_stub = _Win32ComClientStub(app)
    win32com_module = types.ModuleType("win32com")
    win32com_client_module = types.ModuleType("win32com.client")
    win32com_client_module.DispatchEx = win32_client_stub.DispatchEx  # type: ignore[attr-defined]
    win32com_module.client = win32com_client_module  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "pythoncom", pythoncom_stub)
    monkeypatch.setitem(sys.modules, "win32com", win32com_module)
    monkeypatch.setitem(sys.modules, "win32com.client", win32com_client_module)
    return pythoncom_stub, win32_client_stub


def test_preheat_source_opens_presentation_without_edit_window(
    monkeypatch: MonkeyPatch,
) -> None:
    """PowerPoint 文件级预热应打开无编辑窗口的 Presentation。"""
    presentation = _PresentationStub()
    app = _PptAppStub(presentation)
    pythoncom_stub, win32_client_stub = _install_com_stubs(monkeypatch, app)
    preheater = PptApplicationPreheater()

    preheater.preheat_source(42, "C:/demo/source.pptx")
    item = preheater.take(42, "C:/demo/source.pptx")

    assert pythoncom_stub.initialized == 1
    assert win32_client_stub.calls == [POWERPOINT_COM_PROG_IDS[0]]
    assert item is not None
    assert item.app is app
    assert item.source_id == 42
    assert item.uri == "C:/demo/source.pptx"
    assert item.presentation is presentation
    assert presentation.Saved is True
    # 预热不再最小化编辑窗口；仅对本系统拉起的进程做任务栏隐藏
    assert app.WindowState == 0
    assert app.Presentations.calls == [
        ("C:/demo/source.pptx", (), {"ReadOnly": False, "Untitled": True, "WithWindow": False}),
    ]


def test_return_item_downgrades_file_preheat_to_generic_application() -> None:
    """已消费或归还的文件级预热项应降级为应用级暖实例。"""
    presentation = _PresentationStub()
    app = _PptAppStub(presentation)
    preheater = PptApplicationPreheater()
    item = PreheatedPptApplication(
        "powerpoint",
        app,
        POWERPOINT_COM_PROG_IDS[0],
        source_id=9,
        uri="C:/demo/source.pptx",
        presentation=presentation,
    )

    preheater.return_item(item)
    returned = preheater.take()

    assert presentation.close_called is True
    assert presentation.close_args == (False,)
    assert presentation.Saved is True
    assert returned is item
    assert returned.source_id == 0
    assert returned.uri == ""
    assert returned.presentation is None
    assert app.quit_called is False


def test_ppt_adapter_reuses_preheated_presentation(monkeypatch: MonkeyPatch) -> None:
    """PPT 适配器命中文件级预热时不应再次调用 Presentations.Open。"""
    uri = "C:/demo/source.pptx"
    presentation = _PresentationStub()
    app = _PptAppStub(presentation)
    _install_com_stubs(monkeypatch, app)
    item = PreheatedPptApplication(
        "powerpoint",
        app,
        POWERPOINT_COM_PROG_IDS[0],
        source_id=7,
        uri=uri,
        presentation=presentation,
    )
    preheat_pool = _PreheatPoolStub(item)
    adapter = PptSourceAdapter()
    adapter.set_preheat_context(7, True, preheat_pool)
    adapter._file_path = uri
    monkeypatch.setattr(
        ppt,
        "snapshot_candidate_process_ids_for_prog_ids",
        lambda *_args, **_kwargs: set(),
    )
    monkeypatch.setattr(ppt, "read_ppt_app_process_id", lambda *_args, **_kwargs: 0)
    monkeypatch.setattr(adapter, "_start_slideshow", lambda *_args, **_kwargs: None)

    adapter._init_com_and_open(uri, autoplay=False)
    opened_total_slides = adapter._total_slides
    adapter._close_com_resources()

    assert preheat_pool.take_calls == [(7, uri)]
    assert app.Presentations.calls == []
    assert opened_total_slides == 6
    assert preheat_pool.returned_items == []
    assert item.presentation is None
    assert app.quit_called is False


def test_ppt_adapter_reopens_stale_preheated_presentation(
    monkeypatch: MonkeyPatch,
) -> None:
    """其它放映关闭后文件级 COM Presentation 可能失效，此时应在暖应用中重新打开文件。"""

    class _StaleSlides:
        @property
        def Count(self) -> int:
            raise RuntimeError("Open.Slides")

    uri = "C:/demo/source.pptx"
    stale_presentation = _PresentationStub()
    stale_presentation.Slides = _StaleSlides()
    fresh_presentation = _PresentationStub()
    app = _PptAppStub(fresh_presentation)
    _install_com_stubs(monkeypatch, app)
    item = PreheatedPptApplication(
        "powerpoint",
        app,
        POWERPOINT_COM_PROG_IDS[0],
        source_id=7,
        uri=uri,
        presentation=stale_presentation,
    )
    preheat_pool = _PreheatPoolStub(item)
    adapter = PptSourceAdapter()
    adapter.set_preheat_context(7, True, preheat_pool)
    adapter._file_path = uri
    monkeypatch.setattr(
        ppt,
        "snapshot_candidate_process_ids_for_prog_ids",
        lambda *_args, **_kwargs: set(),
    )
    monkeypatch.setattr(ppt, "read_ppt_app_process_id", lambda *_args, **_kwargs: 0)

    adapter._init_com_and_open(uri, autoplay=False)

    assert adapter._total_slides == 6
    assert len(app.Presentations.calls) == 1


def test_quit_ppt_app_if_idle_skips_when_presentations_open() -> None:
    """PowerPoint 仍有打开的演示文稿时，预热清理不得退出应用。"""
    from scp_cv.player.preheat_ppt import quit_ppt_app_if_idle

    presentation = _PresentationStub()
    app = _PptAppStub(presentation)
    app.Presentations = type("_BusyPresentations", (), {"Count": 3})()

    assert quit_ppt_app_if_idle(app) is False
    assert app.quit_called is False


def test_quit_ppt_app_if_idle_quits_when_no_presentations() -> None:
    """没有打开演示文稿时允许退出 PowerPoint。"""
    from scp_cv.player.preheat_ppt import quit_ppt_app_if_idle

    presentation = _PresentationStub()
    app = _PptAppStub(presentation)
    app.Presentations = type("_IdlePresentations", (), {"Count": 0})()

    assert quit_ppt_app_if_idle(app) is True
    assert app.quit_called is True


def test_preheat_records_and_conceals_spawned_powerpoint(
    monkeypatch: MonkeyPatch,
) -> None:
    """预热拉起新 PowerPoint 进程时应记录进程并隐藏编辑窗口。"""
    from scp_cv.player import preheat_ppt

    presentation = _PresentationStub()
    app = _PptAppStub(presentation)
    _install_com_stubs(monkeypatch, app)
    recorded_pids: list[int] = []
    concealed_apps: list[object] = []
    monkeypatch.setattr(
        preheat_ppt,
        "snapshot_candidate_process_ids_for_prog_ids",
        lambda *_args, **_kwargs: set(),
    )
    monkeypatch.setattr(
        preheat_ppt,
        "read_ppt_app_process_id",
        lambda *_args, **_kwargs: 4242,
    )
    monkeypatch.setattr(preheat_ppt, "record_spawned_ppt_process", recorded_pids.append)
    monkeypatch.setattr(
        preheat_ppt,
        "conceal_ppt_editor_window",
        lambda target_app, _logger=None: concealed_apps.append(target_app),
    )

    preheater = PptApplicationPreheater()
    preheater.preheat()
    item = preheater.take()

    assert recorded_pids == [4242]
    assert concealed_apps == [app]
    assert item is not None
    assert item.process_id == 4242
    assert item.spawned_process is True


def test_preheat_keeps_existing_powerpoint_untouched(
    monkeypatch: MonkeyPatch,
) -> None:
    """连接到既有 PowerPoint 进程时不得隐藏用户窗口或记录清理目标。"""
    from scp_cv.player import preheat_ppt

    presentation = _PresentationStub()
    app = _PptAppStub(presentation)
    _install_com_stubs(monkeypatch, app)
    recorded_pids: list[int] = []
    concealed_apps: list[object] = []
    monkeypatch.setattr(
        preheat_ppt,
        "snapshot_candidate_process_ids_for_prog_ids",
        lambda *_args, **_kwargs: {4242},
    )
    monkeypatch.setattr(
        preheat_ppt,
        "read_ppt_app_process_id",
        lambda *_args, **_kwargs: 4242,
    )
    monkeypatch.setattr(preheat_ppt, "record_spawned_ppt_process", recorded_pids.append)
    monkeypatch.setattr(
        preheat_ppt,
        "conceal_ppt_editor_window",
        lambda target_app, _logger=None: concealed_apps.append(target_app),
    )

    preheater = PptApplicationPreheater()
    preheater.preheat()
    item = preheater.take()

    assert recorded_pids == []
    assert concealed_apps == []
    assert item is not None
    assert item.spawned_process is False
