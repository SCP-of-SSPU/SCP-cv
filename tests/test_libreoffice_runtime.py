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
from scp_cv import libreoffice_worker_runtime


class _BlockingPresentationStub:
    """模拟 startWithArguments 阻塞但 controller 可异步出现的放映对象。"""

    def __init__(self) -> None:
        """
        初始化阻塞放映替身。
        :return: None
        """
        self.start_called = False
        self.unblock_start = threading.Event()
        self.AllowAnimations = False
        self.IsFullScreen = False
        self.IsAlwaysOnTop = True
        self.IsEndless = True
        self.IsMouseVisible = True
        self.StartWithNavigator = True
        self.Display = 0

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
        self.process = _WorkerProcessStub()
        self.closed = False

    def close(self) -> None:
        """
        记录关闭调用。
        :return: None
        """
        self.closed = True


class _WorkerProcessStub:
    """模拟 LibreOffice worker 进程。"""

    pid = 123


class _TerminableProcessStub:
    """模拟可终止的 LibreOffice 进程。"""

    pid = 456

    def __init__(self) -> None:
        """
        初始化调用记录。
        :return: None
        """
        self.terminated = False
        self.killed = False

    def poll(self) -> None:
        """
        模拟进程仍在运行。
        :return: None
        """
        return None

    def terminate(self) -> None:
        """
        记录单进程 terminate 兜底调用。
        :return: None
        """
        self.terminated = True

    def kill(self) -> None:
        """
        记录单进程 kill 兜底调用。
        :return: None
        """
        self.killed = True

    def wait(self, timeout: float) -> None:
        """
        模拟等待结束。
        :param timeout: 等待秒数
        :return: None
        """
        return None


class _UnoStub:
    """模拟 pyuno 模块。"""

    def systemPathToFileUrl(self, path: str) -> str:
        """
        返回伪 file URL。
        :param path: 系统路径
        :return: file URL
        """
        return f"file:///{path}"


class _RuntimeDrawPagesStub:
    """模拟 UNO DrawPages。"""

    def __init__(self, slide_count: int) -> None:
        """
        初始化页数替身。
        :param slide_count: 幻灯片页数
        :return: None
        """
        self.slide_count = slide_count

    def getCount(self) -> int:
        """
        返回幻灯片页数。
        :return: 幻灯片页数
        """
        return self.slide_count


class _RuntimeDocumentStub:
    """模拟 LibreOffice worker 打开的文档。"""

    def __init__(self, slide_count: int) -> None:
        """
        初始化文档替身。
        :param slide_count: 幻灯片页数
        :return: None
        """
        self.presentation = _BlockingPresentationStub()
        self.draw_pages = _RuntimeDrawPagesStub(slide_count)

    def getPresentation(self) -> object:
        """
        返回 Presentation 替身。
        :return: Presentation 替身
        """
        return self.presentation

    def getDrawPages(self) -> object:
        """
        返回 DrawPages 替身。
        :return: DrawPages 替身
        """
        return self.draw_pages


class _RecoverablePresentationDocumentStub(_RuntimeDocumentStub):
    """模拟加载成功后读取 Presentation 时 UNO bridge 断开的文档。"""

    def getPresentation(self) -> object:
        """
        抛出可恢复的 UNO bridge 断开异常。
        :return: 不返回
        :raises RuntimeError: 模拟 LibreOffice bridge disposed
        """
        raise RuntimeError("Binary URP bridge disposed during call")


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


def test_prepare_show_file_copy_uses_isolated_profile_copy(tmp_path: Path) -> None:
    """LibreOffice --show 应打开隔离副本，避免原文件锁提示干扰放映。"""
    source_file = tmp_path / "demo.pptx"
    source_file.write_bytes(b"ppt-data")
    profile_dir = tmp_path / "profile"
    profile_dir.mkdir()

    show_file = libreoffice_worker_runtime._prepare_show_file_copy(source_file, profile_dir)

    assert show_file == profile_dir / "show" / "demo.pptx"
    assert show_file.read_bytes() == b"ppt-data"
    assert source_file.read_bytes() == b"ppt-data"


def test_worker_start_session_terminates_process_when_uno_connect_fails(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    """UNO pipe 连接失败时应结束刚启动的 soffice 并清理隔离 profile。"""
    process = _WorkerProcessStub()
    profile_dir = tmp_path / "profile"
    profile_dir.mkdir()
    terminated: list[object] = []
    removed_profiles: list[Path] = []

    def popen_stub(_args: object, stdout: object, stderr: object) -> _WorkerProcessStub:
        """
        返回伪 LibreOffice 进程。
        :param _args: 启动参数
        :param stdout: stdout 参数
        :param stderr: stderr 参数
        :return: 伪进程
        """
        return process

    monkeypatch.setattr(libreoffice_worker_runtime, "_import_uno", lambda: _UnoStub())
    monkeypatch.setattr(libreoffice_worker_runtime, "_resolve_soffice_executable", lambda: Path("soffice.exe"))
    monkeypatch.setattr(libreoffice_worker_runtime.tempfile, "mkdtemp", lambda prefix: str(profile_dir))
    monkeypatch.setattr(libreoffice_worker_runtime.subprocess, "Popen", popen_stub)
    monkeypatch.setattr(
        libreoffice_worker_runtime,
        "_connect_uno_pipe",
        lambda *_args: (_ for _ in ()).throw(libreoffice_worker.WorkerError("connect failed")),
    )
    monkeypatch.setattr(libreoffice_worker_runtime, "_terminate_process", lambda target_process: terminated.append(target_process))
    monkeypatch.setattr(
        libreoffice_worker_runtime.shutil,
        "rmtree",
        lambda path, ignore_errors=False: removed_profiles.append(Path(path)),
    )

    try:
        libreoffice_worker_runtime._start_session(headless=False)
    except libreoffice_worker.WorkerError as start_error:
        assert "connect failed" in str(start_error)
    else:
        raise AssertionError("expected WorkerError")

    assert terminated == [process]
    assert removed_profiles == [profile_dir]


def test_worker_terminate_process_uses_process_tree_before_single_process_fallback(
    monkeypatch: MonkeyPatch,
) -> None:
    """结束 LibreOffice 时应优先终止进程树，避免残留 soffice.bin。"""
    process = _TerminableProcessStub()
    tree_calls: list[int] = []

    def terminate_tree(process_id: int) -> bool:
        """
        记录进程树终止请求。
        :param process_id: 进程 ID
        :return: True 表示已处理
        """
        tree_calls.append(process_id)
        return True

    monkeypatch.setattr(libreoffice_worker_runtime, "_terminate_process_tree", terminate_tree)

    libreoffice_worker_runtime._terminate_process(process)  # type: ignore[arg-type]

    assert tree_calls == [456]
    assert process.terminated is False
    assert process.killed is False


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


def test_worker_open_preloads_document_hidden_when_not_autoplay(monkeypatch: MonkeyPatch) -> None:
    """bridge 预加载 PPT 时应隐藏编辑窗口，避免未放映前暴露 Impress。"""
    bridge = libreoffice_worker.LibreOfficeBridge()
    session = _WorkerSessionStub("open")
    document = _RuntimeDocumentStub(slide_count=3)
    load_calls: list[tuple[object, Path, bool, bool]] = []

    def fake_load_document(
        loaded_session: object,
        file_path: Path,
        hidden: bool,
        readonly: bool,
    ) -> object:
        """
        记录 LibreOffice 加载参数。
        :param loaded_session: session 替身
        :param file_path: PPT 路径
        :param hidden: 是否隐藏编辑窗口
        :param readonly: 是否只读打开
        :return: 文档替身
        """
        load_calls.append((loaded_session, file_path, hidden, readonly))
        return document

    monkeypatch.setattr(libreoffice_worker, "_start_session", lambda headless: session)
    monkeypatch.setattr(libreoffice_worker, "_load_document", fake_load_document)

    payload = bridge.open(Path("demo.pptx"), autoplay=False, display_index=2)

    assert load_calls == [(session, Path("demo.pptx"), True, True)]
    assert payload["playback_state"] == "stopped"
    assert payload["total_slides"] == 3
    assert document.presentation.AllowAnimations is True
    assert document.presentation.IsFullScreen is True
    assert document.presentation.IsAlwaysOnTop is False
    assert document.presentation.IsEndless is False
    assert document.presentation.IsMouseVisible is False
    assert document.presentation.StartWithNavigator is False
    assert document.presentation.Display == 2


def test_worker_open_autoplay_uses_show_session(monkeypatch: MonkeyPatch) -> None:
    """bridge 自动播放应走 LibreOffice 原生 --show 会话，避免 UNO 手动 start 超时。"""
    bridge = libreoffice_worker.LibreOfficeBridge()
    session = _WorkerSessionStub("show")
    document = _RuntimeDocumentStub(slide_count=3)
    show_calls: list[Path] = []
    load_calls: list[object] = []

    def fake_start_show_session(file_path: Path) -> tuple[_WorkerSessionStub, _RuntimeDocumentStub]:
        show_calls.append(file_path)
        document.presentation.start_called = True
        return session, document

    monkeypatch.setattr(libreoffice_worker, "_start_show_session", fake_start_show_session)
    monkeypatch.setattr(libreoffice_worker, "_load_document", lambda *args: load_calls.append(args))

    payload = bridge.open(Path("demo.pptx"), autoplay=True, display_index=2)

    assert show_calls == [Path("demo.pptx")]
    assert load_calls == []
    assert payload["playback_state"] == "playing"
    assert payload["total_slides"] == 3
    assert bridge.session is session
    assert bridge.document is document


def test_worker_open_retries_recoverable_bridge_dispose_after_load(monkeypatch: MonkeyPatch) -> None:
    """加载后 UNO bridge 断开时应重建会话并重试完整打开流程。"""
    bridge = libreoffice_worker.LibreOfficeBridge()
    first_session = _WorkerSessionStub("first")
    second_session = _WorkerSessionStub("second")
    documents: list[object] = [
        _RecoverablePresentationDocumentStub(slide_count=1),
        _RuntimeDocumentStub(slide_count=4),
    ]
    sessions = [first_session, second_session]
    load_calls: list[tuple[str, Path, bool, bool]] = []

    def fake_start_session(headless: bool) -> _WorkerSessionStub:
        """
        按顺序返回会话替身。
        :param headless: 是否 headless 启动
        :return: session 替身
        """
        assert headless is False
        return sessions.pop(0)

    def fake_load_document(
        loaded_session: _WorkerSessionStub,
        file_path: Path,
        hidden: bool,
        readonly: bool,
    ) -> object:
        """
        第一次返回读取 Presentation 失败的文档，第二次返回正常文档。
        :param loaded_session: 当前 session
        :param file_path: PPT 路径
        :param hidden: 是否隐藏加载
        :param readonly: 是否只读加载
        :return: 文档替身
        """
        load_calls.append((loaded_session.label, file_path, hidden, readonly))
        return documents.pop(0)

    monkeypatch.setattr(libreoffice_worker, "_start_session", fake_start_session)
    monkeypatch.setattr(libreoffice_worker, "_load_document", fake_load_document)

    payload = bridge.open(Path("demo.pptx"), autoplay=False)

    assert payload["playback_state"] == "stopped"
    assert payload["total_slides"] == 4
    assert bridge.session is second_session
    assert first_session.closed is True
    assert load_calls == [
        ("first", Path("demo.pptx"), True, True),
        ("second", Path("demo.pptx"), True, True),
    ]


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

    loaded_document = bridge._load_document_with_retry(Path("demo.pptx"), hidden=True, readonly=True)

    assert loaded_document is document
    assert first_session.closed is True
    assert bridge.session is second_session
    assert calls == ["first", "second"]
