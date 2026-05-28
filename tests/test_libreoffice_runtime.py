#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
LibreOffice 运行时路径解析测试，覆盖自带 Python 定位。
@Project : SCP-cv
@File : test_libreoffice_runtime.py
@Author : Qintsg
@Date : 2026-05-27
'''
from __future__ import annotations

import threading
from pathlib import Path

from pytest import MonkeyPatch

from scp_cv import libreoffice
from scp_cv import libreoffice_worker


class _BlockingPresentationStub:
    """模拟 startWithArguments 阻塞但 controller 可异步出现的放映对象。"""

    def __init__(self) -> None:
        """
        初始化阻塞放映替身。
        :return: None
        """
        self.start_called = False
        self.unblock_start = threading.Event()

    def startWithArguments(self, _args: tuple[object, ...]) -> None:
        """
        模拟 LibreOffice 放映启动调用阻塞。
        :param _args: 启动参数
        :return: None
        """
        self.start_called = True
        self.unblock_start.wait(timeout=1.0)

    def getController(self) -> object | None:
        """
        返回已创建的 controller。
        :return: controller 替身
        """
        return object() if self.start_called else None


class _FailingPresentationStub:
    """模拟 LibreOffice 放映启动直接失败的 Presentation。"""

    def startWithArguments(self, _args: tuple[object, ...]) -> None:
        """
        抛出启动失败异常。
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


class _WorkerSessionStub:
    """模拟 LibreOffice worker session。"""

    def __init__(self, label: str) -> None:
        """
        初始化 session 替身。
        :param label: session 标识
        :return: None
        """
        self.label = label
        self.closed = False

    def close(self) -> None:
        """
        记录关闭调用。
        :return: None
        """
        self.closed = True


def test_resolve_libreoffice_python_executable_uses_program_dir(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    """LibreOffice Python 应从 soffice 所在 program 目录解析。"""
    program_dir = tmp_path / "program"
    program_dir.mkdir()
    soffice = program_dir / "soffice.exe"
    lo_python = program_dir / "python.exe"
    soffice.write_text("", encoding="utf-8")
    lo_python.write_text("", encoding="utf-8")

    monkeypatch.setattr(libreoffice, "resolve_libreoffice_executable", lambda _bin_path=None: soffice)

    assert libreoffice.resolve_libreoffice_python_executable() == lo_python


def test_configured_bridge_command_timeout_is_separate_from_connect_timeout(
    monkeypatch: MonkeyPatch,
) -> None:
    """bridge 命令超时应独立于 UNO 连接超时。"""
    monkeypatch.setenv("LIBREOFFICE_CONNECT_TIMEOUT_SECONDS", "2")
    monkeypatch.delenv("LIBREOFFICE_BRIDGE_COMMAND_TIMEOUT_SECONDS", raising=False)

    assert libreoffice.configured_libreoffice_timeout() == 2.0
    assert libreoffice.configured_libreoffice_bridge_command_timeout() == 120.0

    monkeypatch.setenv("LIBREOFFICE_BRIDGE_COMMAND_TIMEOUT_SECONDS", "45")

    assert libreoffice.configured_libreoffice_bridge_command_timeout() == 45.0


def test_worker_bridge_command_timeout_is_separate_from_connect_timeout(
    monkeypatch: MonkeyPatch,
) -> None:
    """worker 内部 bridge 命令超时也应独立于 UNO 连接超时。"""
    monkeypatch.setenv("LIBREOFFICE_CONNECT_TIMEOUT_SECONDS", "2")
    monkeypatch.delenv("LIBREOFFICE_BRIDGE_COMMAND_TIMEOUT_SECONDS", raising=False)

    assert libreoffice_worker._timeout_seconds() == 2.0
    assert libreoffice_worker._bridge_command_timeout_seconds() == 120.0

    monkeypatch.setenv("LIBREOFFICE_BRIDGE_COMMAND_TIMEOUT_SECONDS", "45")

    assert libreoffice_worker._bridge_command_timeout_seconds() == 45.0


def test_worker_slideshow_start_does_not_block_on_libreoffice_start() -> None:
    """worker 启动放映不应被 LibreOffice startWithArguments 同步阻塞。"""
    bridge = libreoffice_worker.LibreOfficeBridge()
    presentation = _BlockingPresentationStub()
    bridge.presentation = presentation

    bridge._start_slideshow(1)
    presentation.unblock_start.set()

    assert bridge.controller is not None
    assert bridge.is_paused is False
    assert presentation.start_called is True


def test_worker_slideshow_start_reports_async_start_error() -> None:
    """worker 异步启动放映失败时应快速返回明确错误。"""
    bridge = libreoffice_worker.LibreOfficeBridge()
    bridge.presentation = _FailingPresentationStub()

    try:
        bridge._start_slideshow(1)
    except libreoffice_worker.WorkerError as start_error:
        assert "LibreOffice 放映启动失败" in str(start_error)
        assert "start failed" in str(start_error)
    else:
        raise AssertionError("expected WorkerError")


def test_worker_load_document_retries_recoverable_bridge_dispose(
    monkeypatch: MonkeyPatch,
) -> None:
    """LibreOffice 冷启动 loadComponentFromURL 断开时应重建 session 后重试一次。"""
    bridge = libreoffice_worker.LibreOfficeBridge()
    first_session = _WorkerSessionStub("first")
    second_session = _WorkerSessionStub("second")
    bridge.session = first_session
    calls: list[str] = []
    document = object()

    def fake_load_document(session: _WorkerSessionStub, *_args: object, **_kwargs: object) -> object:
        """
        第一次模拟 UNO bridge disposed，第二次成功。
        :param session: session 替身
        :param _args: 位置参数
        :param _kwargs: 关键字参数
        :return: 文档对象
        """
        calls.append(session.label)
        if session is first_session:
            raise RuntimeError("Binary URP bridge disposed during call")
        return document

    monkeypatch.setattr(libreoffice_worker, "_load_document", fake_load_document)
    monkeypatch.setattr(libreoffice_worker, "_start_session", lambda headless: second_session)

    loaded_document = bridge._load_document_with_retry(Path("demo.pptx"), hidden=False, readonly=True)

    assert loaded_document is document
    assert first_session.closed is True
    assert bridge.session is second_session
    assert calls == ["first", "second"]
