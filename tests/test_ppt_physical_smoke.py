#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PowerPoint Broker 并发物理冒烟测试。
@Project : SCP-cv
@File : test_ppt_physical_smoke.py
@Author : Qintsg
@Date : 2026-07-11
'''
from __future__ import annotations

import sys
import threading
from pathlib import Path
from types import SimpleNamespace

from pytest import MonkeyPatch

from scp_cv.player.ppt_broker import (
    BrokerHealth,
    PptCommand,
    PptCommandRequest,
    PptOpenRequest,
    PptSessionKey,
    PptState,
)
from scp_cv.services.ppt_physical_smoke import run_ppt_concurrency_smoke_test
from scp_cv.services.ppt_physical_smoke_validation import read_window_exists


class _FakeBroker:
    """可观察并发度和窗口隔离的 Broker 测试替身。"""

    def __init__(self) -> None:
        self._barrier = threading.Barrier(4)
        self._lock = threading.Lock()
        self._states: dict[PptSessionKey, PptState] = {}
        self.active_open_calls = 0
        self.max_concurrent_open_calls = 0
        self.goto_calls: list[int] = []
        self.reopen_calls: list[int] = []

    def health(self) -> BrokerHealth:
        return BrokerHealth(ready=True, generation="fake-generation", pid=4321)

    def open(self, request: PptOpenRequest) -> PptState:
        with self._lock:
            self.active_open_calls += 1
            self.max_concurrent_open_calls = max(
                self.max_concurrent_open_calls,
                self.active_open_calls,
            )
        if "reopen" not in request.request_id:
            self._barrier.wait(timeout=2)
        else:
            self.reopen_calls.append(request.session.window_id)
        state = PptState(
            playback_state="playing",
            current_slide=request.start_slide,
            total_slides=5,
            powerpoint_pid=4321,
            slideshow_hwnd=10_000 + request.session.window_id,
            parent_hwnd=request.parent_hwnd,
            generation="fake-generation",
        )
        with self._lock:
            self._states[request.session] = state
            self.active_open_calls -= 1
        return state

    def command(self, request: PptCommandRequest) -> PptState:
        state = self._states[request.session]
        if request.command is PptCommand.GOTO:
            self.goto_calls.append(request.session.window_id)
            state = PptState(
                playback_state=state.playback_state,
                current_slide=request.slide_index,
                total_slides=state.total_slides,
                powerpoint_pid=state.powerpoint_pid,
                slideshow_hwnd=state.slideshow_hwnd,
                parent_hwnd=state.parent_hwnd,
                generation=state.generation,
            )
            self._states[request.session] = state
        return state

    def get_state(self, session: PptSessionKey) -> PptState:
        return self._states[session]

    def close(self, session: PptSessionKey) -> None:
        self._states.pop(session, None)


def test_cleanup_window_probe_ignores_reused_powerpoint_application_frame(
    monkeypatch: MonkeyPatch,
) -> None:
    """旧数字 HWND 变成普通 PowerPoint frame 后不再算放映窗口泄漏。"""
    title = "PowerPoint"
    fake_win32gui = SimpleNamespace(
        IsWindow=lambda _hwnd: True,
        GetWindowText=lambda _hwnd: title,
    )
    monkeypatch.setitem(sys.modules, "win32gui", fake_win32gui)

    assert read_window_exists(16_192_652) is False

    title = "PowerPoint 幻灯片放映  -  演示文稿4"
    assert read_window_exists(16_192_652) is True


class _BroadcastingFakeBroker(_FakeBroker):
    """模拟错误地把单窗翻页广播到全部会话的 Broker。"""

    def command(self, request: PptCommandRequest) -> PptState:
        if request.command is PptCommand.GOTO:
            for session, state in list(self._states.items()):
                self._states[session] = PptState(
                    playback_state=state.playback_state,
                    current_slide=request.slide_index,
                    total_slides=state.total_slides,
                    powerpoint_pid=state.powerpoint_pid,
                    slideshow_hwnd=state.slideshow_hwnd,
                    parent_hwnd=state.parent_hwnd,
                    generation=state.generation,
                )
        return self._states[request.session]


class _StickySessionFakeBroker(_FakeBroker):
    """模拟 close 返回成功但仍把会话留在 Broker 注册表。"""

    def close(self, session: PptSessionKey) -> None:
        return


class _ExpectedPathsBroker(_FakeBroker):
    """要求每个窗口始终使用指定 PPT 路径和 source id 的 Broker 替身。"""

    def __init__(
        self,
        expected_paths: dict[int, Path],
        expected_source_ids: dict[int, int],
    ) -> None:
        super().__init__()
        self._expected_paths = expected_paths
        self._expected_source_ids = expected_source_ids

    def open(self, request: PptOpenRequest) -> PptState:
        assert Path(request.uri) == self._expected_paths[request.session.window_id]
        assert request.source_id == self._expected_source_ids[request.session.window_id]
        return super().open(request)


def test_ppt_smoke_opens_four_unique_slideshows_in_parallel(
    tmp_path: Path,
) -> None:
    """单轮测试应并发打开四个 PPT，并确认唯一 HWND 与真实父窗口。"""
    ppt_path = tmp_path / "concurrent-smoke.pptx"
    ppt_path.write_bytes(b"fake")
    parent_hwnds = {window_id: 20_000 + window_id for window_id in range(1, 5)}
    actual_parents = {
        10_000 + window_id: parent_hwnd
        for window_id, parent_hwnd in parent_hwnds.items()
    }
    broker = _FakeBroker()

    result = run_ppt_concurrency_smoke_test(
        broker,
        ppt_path,
        parent_hwnds,
        iterations=1,
        parent_hwnd_reader=actual_parents.__getitem__,
    )

    assert result["success"] is True
    assert result["iterations_completed"] == 1
    assert broker.max_concurrent_open_calls == 4
    assert result["rounds"][0]["slideshow_hwnds"] == {
        1: 10_001,
        2: 10_002,
        3: 10_003,
        4: 10_004,
    }
    assert result["rounds"][0]["parent_hwnds"] == parent_hwnds


def test_ppt_smoke_accepts_broker_host_parent_chain(tmp_path: Path) -> None:
    """放映窗口可通过 Broker 原生宿主间接嵌入 Player 容器。"""
    ppt_path = tmp_path / "broker-host-smoke.pptx"
    ppt_path.write_bytes(b"fake")
    parent_hwnds = {window_id: 20_000 + window_id for window_id in range(1, 5)}
    host_hwnds = {window_id: 30_000 + window_id for window_id in range(1, 5)}
    actual_parents = {
        **{
            10_000 + window_id: host_hwnds[window_id]
            for window_id in range(1, 5)
        },
        **{
            host_hwnds[window_id]: parent_hwnds[window_id]
            for window_id in range(1, 5)
        },
    }

    result = run_ppt_concurrency_smoke_test(
        _FakeBroker(),
        ppt_path,
        parent_hwnds,
        iterations=1,
        parent_hwnd_reader=actual_parents.__getitem__,
    )

    assert result["success"] is True
    assert result["rounds"][0]["parent_hwnds"] == parent_hwnds


def test_ppt_smoke_accepts_one_ppt_path_per_window(tmp_path: Path) -> None:
    """调用方可给四个窗口分别指定 PPT，重开时仍使用原窗口源。"""
    ppt_paths = {
        window_id: tmp_path / f"window-{window_id}.pptx"
        for window_id in range(1, 5)
    }
    for ppt_path in ppt_paths.values():
        ppt_path.write_bytes(b"fake")
    parent_hwnds = {window_id: 20_000 + window_id for window_id in range(1, 5)}
    actual_parents = {
        10_000 + window_id: parent_hwnd
        for window_id, parent_hwnd in parent_hwnds.items()
    }
    source_ids = {window_id: 100 + window_id for window_id in range(1, 5)}

    result = run_ppt_concurrency_smoke_test(
        _ExpectedPathsBroker(ppt_paths, source_ids),
        ppt_paths,
        parent_hwnds,
        iterations=1,
        parent_hwnd_reader=actual_parents.__getitem__,
        source_ids=source_ids,
    )

    assert result["success"] is True
    assert result["ppt_paths"] == {
        window_id: str(ppt_path.resolve())
        for window_id, ppt_path in ppt_paths.items()
    }
    assert result["source_ids"] == source_ids


def test_ppt_smoke_proves_navigation_and_close_are_window_isolated(
    tmp_path: Path,
) -> None:
    """不同页码、单窗关闭和重开都不能污染其他窗口。"""
    ppt_path = tmp_path / "isolated-smoke.pptx"
    ppt_path.write_bytes(b"fake")
    parent_hwnds = {window_id: 20_000 + window_id for window_id in range(1, 5)}
    actual_parents = {
        10_000 + window_id: parent_hwnd
        for window_id, parent_hwnd in parent_hwnds.items()
    }
    broker = _FakeBroker()

    result = run_ppt_concurrency_smoke_test(
        broker,
        ppt_path,
        parent_hwnds,
        iterations=1,
        parent_hwnd_reader=actual_parents.__getitem__,
    )

    round_result = result["rounds"][0]
    assert broker.goto_calls == [1, 2, 3, 4]
    assert round_result["navigation_slides"] == {1: 2, 2: 3, 3: 4, 4: 5}
    assert round_result["closed_window_id"] == 1
    assert round_result["surviving_slideshow_hwnds"] == {
        2: 10_002,
        3: 10_003,
        4: 10_004,
    }
    assert broker.reopen_calls == [1]
    assert round_result["reopened_slideshow_hwnd"] == 10_001
    assert round_result["reopened_parent_hwnd"] == 20_001
    assert round_result["final_slides"] == {1: 2, 2: 3, 3: 4, 4: 5}


def test_ppt_smoke_fails_when_final_close_leaves_registered_sessions(
    tmp_path: Path,
) -> None:
    """每轮最终关闭后，任一仍可查询的公开会话都必须使冒烟失败。"""
    ppt_path = tmp_path / "sticky-session.pptx"
    ppt_path.write_bytes(b"fake")
    parent_hwnds = {window_id: 20_000 + window_id for window_id in range(1, 5)}
    actual_parents = {
        10_000 + window_id: parent_hwnd
        for window_id, parent_hwnd in parent_hwnds.items()
    }

    result = run_ppt_concurrency_smoke_test(
        _StickySessionFakeBroker(),
        ppt_path,
        parent_hwnds,
        iterations=1,
        parent_hwnd_reader=actual_parents.__getitem__,
    )

    assert result["success"] is False
    assert "最终关闭后 Broker 会话仍存在" in result["rounds"][0]["error_message"]


def test_ppt_smoke_fails_when_final_close_leaves_slideshow_hwnd(
    tmp_path: Path,
) -> None:
    """会话已注销但任一最终放映 HWND 仍有效时，物理冒烟必须失败。"""
    ppt_path = tmp_path / "leaked-window.pptx"
    ppt_path.write_bytes(b"fake")
    parent_hwnds = {window_id: 20_000 + window_id for window_id in range(1, 5)}
    actual_parents = {
        10_000 + window_id: parent_hwnd
        for window_id, parent_hwnd in parent_hwnds.items()
    }

    result = run_ppt_concurrency_smoke_test(
        _FakeBroker(),
        ppt_path,
        parent_hwnds,
        iterations=1,
        parent_hwnd_reader=actual_parents.__getitem__,
        window_exists_reader=lambda hwnd: hwnd == 10_004,
    )

    assert result["success"] is False
    assert "最终关闭后放映 HWND 仍存在" in result["rounds"][0]["error_message"]
    assert "hwnd=10004" in result["rounds"][0]["error_message"]


def test_ppt_smoke_repeats_three_rounds_by_default(tmp_path: Path) -> None:
    """现场默认值应完整重复三轮，并轮换被单独关闭的窗口。"""
    ppt_path = tmp_path / "three-round-smoke.pptx"
    ppt_path.write_bytes(b"fake")
    parent_hwnds = {window_id: 20_000 + window_id for window_id in range(1, 5)}
    actual_parents = {
        10_000 + window_id: parent_hwnd
        for window_id, parent_hwnd in parent_hwnds.items()
    }

    result = run_ppt_concurrency_smoke_test(
        _FakeBroker(),
        ppt_path,
        parent_hwnds,
        parent_hwnd_reader=actual_parents.__getitem__,
    )

    assert result["success"] is True
    assert result["iterations_requested"] == 3
    assert result["iterations_completed"] == 3
    assert [item["closed_window_id"] for item in result["rounds"]] == [1, 2, 3]


def test_ppt_smoke_reports_cross_window_navigation(tmp_path: Path) -> None:
    """单窗翻页污染其他会话时应返回包含窗口上下文的失败诊断。"""
    ppt_path = tmp_path / "broken-isolation.pptx"
    ppt_path.write_bytes(b"fake")
    parent_hwnds = {window_id: 20_000 + window_id for window_id in range(1, 5)}
    actual_parents = {
        10_000 + window_id: parent_hwnd
        for window_id, parent_hwnd in parent_hwnds.items()
    }

    result = run_ppt_concurrency_smoke_test(
        _BroadcastingFakeBroker(),
        ppt_path,
        parent_hwnds,
        parent_hwnd_reader=actual_parents.__getitem__,
    )

    assert result["success"] is False
    assert result["iterations_completed"] == 0
    assert result["rounds"][0]["status"] == "failed"
    assert "PPT 独立翻页隔离失败" in result["rounds"][0]["error_message"]
    assert "command_window=1" in result["rounds"][0]["error_message"]
