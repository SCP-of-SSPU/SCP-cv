#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PowerPoint Broker COM 重试与进程所有权测试。
@Project : SCP-cv
@File : test_ppt_broker_powerpoint_process.py
@Author : Qintsg
@Date : 2026-07-12
'''
from __future__ import annotations

import logging

import pytest

from scp_cv.player.ppt_broker import (
    PptBrokerEngine,
    PptOpenRequest,
    PptPreheatRequest,
    PptSessionKey,
)
from scp_cv.player.ppt_broker.powerpoint import PowerPointComBackend
from tests.ppt_broker_powerpoint_test_support import (
    AnimatedPowerPoint as _AnimatedPowerPoint,
    AnimatedPresentation as _AnimatedPresentation,
    AnimatedView as _AnimatedView,
    EmptyPowerPoint as _EmptyPowerPoint,
    TransientComError as _TransientComError,
    WindowPort as _WindowPort,
)


def test_transient_com_rejection_is_retried_until_application_is_ready(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """仅瞬时 RPC 拒绝应按有限次数重试并最终返回成功。"""
    application = _EmptyPowerPoint()
    attempts = 0

    def create_application() -> object:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise _TransientComError("PowerPoint is busy")
        return application

    backend = PowerPointComBackend(
        application_factory=create_application,
        process_id_reader=lambda _app: 4242,
        window_port=object(),  # 应用级预热不会触碰窗口 Adapter
        retry_delays=(0.0, 0.0),
    )
    broker = PptBrokerEngine(backend)
    try:
        with caplog.at_level(
            logging.WARNING,
            logger="scp_cv.player.ppt_broker.powerpoint",
        ):
            broker.preheat(PptPreheatRequest())
        assert attempts == 3
        assert broker.health().ready is True
        retry_messages = [
            record.getMessage()
            for record in caplog.records
            if "瞬时 COM 拒绝" in record.getMessage()
        ]
        assert len(retry_messages) == 2
        assert all("hresult=0x80010001" in message for message in retry_messages)
    finally:
        broker.shutdown()


def test_wrapped_transient_com_rejection_keeps_hresult_retry_semantics() -> None:
    """默认 Dispatch 包装错误后仍应从异常链识别瞬时 HRESULT。"""
    application = _EmptyPowerPoint()
    attempts = 0

    def create_application() -> object:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            try:
                raise _TransientComError("PowerPoint is busy")
            except _TransientComError as transient_error:
                raise RuntimeError("dispatch failed") from transient_error
        return application

    backend = PowerPointComBackend(
        application_factory=create_application,
        process_id_reader=lambda _app: 4242,
        window_port=object(),
        retry_delays=(0.0, 0.0),
    )
    broker = PptBrokerEngine(backend)
    try:
        broker.preheat(PptPreheatRequest())
        assert attempts == 3
    finally:
        broker.shutdown()


def test_deterministic_com_error_is_not_retried() -> None:
    """参数或安装类确定性错误应立即返回，不得被重试掩盖。"""
    attempts = 0

    def create_application() -> object:
        nonlocal attempts
        attempts += 1
        raise ValueError("invalid COM configuration")

    backend = PowerPointComBackend(
        application_factory=create_application,
        process_id_reader=lambda _app: 0,
        window_port=object(),
        retry_delays=(0.0, 0.0, 0.0),
    )
    broker = PptBrokerEngine(backend)
    try:
        with pytest.raises(ValueError, match="invalid COM configuration"):
            broker.preheat(PptPreheatRequest())
        assert attempts == 1
    finally:
        broker.shutdown()


def test_get_state_surfaces_released_view_instead_of_cached_playing_state() -> None:
    """PowerPoint 崩溃或 COM 代理断连后不得继续上报缓存的 playing。"""

    class _ReleasedViewError(RuntimeError):
        hresult = -2_147_417_848

    class _CrashableView(_AnimatedView):
        def __init__(self) -> None:
            super().__init__()
            self._state = 1
            self.crashed = False

        @property
        def State(self) -> int:
            if self.crashed:
                raise _ReleasedViewError("PowerPoint process disconnected")
            return self._state

        @State.setter
        def State(self, value: int) -> None:
            self._state = int(value)

    application = _AnimatedPowerPoint()
    view = _CrashableView()
    presentation = _AnimatedPresentation(view)
    application.Presentations.Open = lambda *_args, **_kwargs: presentation
    backend = PowerPointComBackend(
        application_factory=lambda: application,
        process_id_reader=lambda _app: 4242,
        window_port=_WindowPort(),
        file_exists=lambda _uri: True,
        retry_delays=(0.0, 0.0),
    )
    broker = PptBrokerEngine(backend)
    session = PptSessionKey(1, "crashed-state-player")
    try:
        broker.open(PptOpenRequest(session, "C:/slides/source.pptx", 1001))
        view.crashed = True

        with pytest.raises(_ReleasedViewError, match="disconnected"):
            broker.get_state(session)
    finally:
        view.crashed = False
        broker.shutdown()


def test_preexisting_powerpoint_is_not_owned_and_alerts_are_never_modified() -> None:
    """DispatchEx 命中启动前 PID 时不得修改用户 Application 的全局告警。"""
    application = _EmptyPowerPoint()
    application.DisplayAlerts = 73
    backend = PowerPointComBackend(
        application_factory=lambda: application,
        process_id_reader=lambda _app: 4242,
        process_snapshot=lambda: {4242},
        window_port=object(),
    )
    broker = PptBrokerEngine(backend)

    broker.preheat(PptPreheatRequest())
    assert application.DisplayAlerts == 73
    broker.shutdown()

    assert application.quit_called is False
    assert application.DisplayAlerts == 73


def test_new_powerpoint_pid_is_owned_and_quit_only_when_idle() -> None:
    """启动后新增且无外部文档的 PID 才可由 Broker 退出。"""
    application = _EmptyPowerPoint()
    application.DisplayAlerts = 91
    backend = PowerPointComBackend(
        application_factory=lambda: application,
        process_id_reader=lambda _app: 4242,
        process_snapshot=lambda: {1111},
        window_port=object(),
    )
    broker = PptBrokerEngine(backend)

    broker.preheat(PptPreheatRequest())
    broker.shutdown()

    assert application.quit_called is True
    assert application.DisplayAlerts == 91


def test_failed_quit_forces_only_verified_windowless_owned_process() -> None:
    """Quit 失败后仅可按 PID+创建时间终止无外部窗口的 Broker 自有进程。"""

    class _QuitFailurePowerPoint(_EmptyPowerPoint):
        def Quit(self) -> None:
            raise RuntimeError("PowerPoint refused to quit")

    application = _QuitFailurePowerPoint()
    snapshots = iter(
        [
            {1111: 10.0},
            {1111: 10.0, 4242: 20.0},
            {1111: 10.0, 4242: 20.0},
        ]
    )
    terminated: list[tuple[int, float]] = []
    backend = PowerPointComBackend(
        application_factory=lambda: application,
        process_id_reader=lambda _app: 4242,
        process_snapshot=lambda: next(snapshots),
        process_window_probe=lambda _pid: False,
        process_terminator=lambda pid, created_at: terminated.append(
            (pid, created_at)
        )
        or True,
        window_port=object(),
    )
    broker = PptBrokerEngine(backend)

    broker.preheat(PptPreheatRequest())
    broker.shutdown()

    assert terminated == [(4242, 20.0)]


@pytest.mark.parametrize(
    ("shutdown_snapshot", "has_windows"),
    [
        ({1111: 10.0, 4242: 21.0}, False),
        ({1111: 10.0, 4242: 20.0}, True),
    ],
)
def test_failed_quit_preserves_process_when_identity_or_windows_are_unsafe(
    shutdown_snapshot: dict[int, float],
    has_windows: bool,
) -> None:
    """PID 被复用或仍存在外部窗口时必须保留 PowerPoint 进程。"""

    class _QuitFailurePowerPoint(_EmptyPowerPoint):
        def Quit(self) -> None:
            raise RuntimeError("PowerPoint refused to quit")

    snapshots = iter(
        [
            {1111: 10.0},
            {1111: 10.0, 4242: 20.0},
            shutdown_snapshot,
        ]
    )
    terminated: list[tuple[int, float]] = []
    backend = PowerPointComBackend(
        application_factory=_QuitFailurePowerPoint,
        process_id_reader=lambda _app: 4242,
        process_snapshot=lambda: next(snapshots),
        process_window_probe=lambda _pid: has_windows,
        process_terminator=lambda pid, created_at: terminated.append(
            (pid, created_at)
        )
        or True,
        window_port=object(),
    )
    broker = PptBrokerEngine(backend)

    broker.preheat(PptPreheatRequest())
    broker.shutdown()

    assert terminated == []


def test_process_terminator_rechecks_pid_creation_time(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """真正 kill 前必须再次核对 POWERPNT.EXE 创建时间，防止 PID 复用。"""
    import sys
    from types import SimpleNamespace

    from scp_cv.player.ppt_broker.com_support import terminate_powerpoint_process

    killed: list[bool] = []

    class _ReusedProcess:
        @staticmethod
        def name() -> str:
            return "POWERPNT.EXE"

        @staticmethod
        def create_time() -> float:
            return 21.0

        @staticmethod
        def kill() -> None:
            killed.append(True)

    monkeypatch.setitem(
        sys.modules,
        "psutil",
        SimpleNamespace(Process=lambda _pid: _ReusedProcess()),
    )

    assert terminate_powerpoint_process(4242, 20.0) is False
    assert killed == []


def test_application_without_hwnd_uses_unique_process_delta() -> None:
    """DispatchEx 尚无编辑器 HWND 时应以启动前后唯一 PID 差集确认归属。"""
    application = _EmptyPowerPoint()
    snapshots = iter(
        [
            {1111: 10.0},
            {1111: 10.0, 4242: 20.0},
        ]
    )
    backend = PowerPointComBackend(
        application_factory=lambda: application,
        process_id_reader=lambda _app: 0,
        process_snapshot=lambda: next(snapshots),
        window_port=object(),
    )
    broker = PptBrokerEngine(backend)

    broker.preheat(PptPreheatRequest())

    assert backend.powerpoint_pid == 4242
    broker.shutdown()
    assert application.quit_called is True


def test_application_without_hwnd_rejects_ambiguous_process_delta() -> None:
    """启动后出现多个 POWERPNT.EXE 时不得猜测 PID。"""
    snapshots = iter(
        [
            {1111: 10.0},
            {1111: 10.0, 4242: 20.0, 4343: 20.1},
        ]
    )
    backend = PowerPointComBackend(
        application_factory=_EmptyPowerPoint,
        process_id_reader=lambda _app: 0,
        process_snapshot=lambda: next(snapshots),
        window_port=object(),
    )
    broker = PptBrokerEngine(backend)

    try:
        with pytest.raises(RuntimeError, match="多个新增 PowerPoint 进程"):
            broker.preheat(PptPreheatRequest())
    finally:
        broker.shutdown()


def test_owned_powerpoint_is_not_quit_when_external_document_remains() -> None:
    """即使 PID 由 Broker 创建，只要出现外部文档也不得退出 Application。"""
    application = _EmptyPowerPoint()
    backend = PowerPointComBackend(
        application_factory=lambda: application,
        process_id_reader=lambda _app: 4242,
        process_snapshot=lambda: set(),
        window_port=object(),
    )
    broker = PptBrokerEngine(backend)

    broker.preheat(PptPreheatRequest())
    application.Presentations.Count = 1
    broker.shutdown()

    assert application.quit_called is False
