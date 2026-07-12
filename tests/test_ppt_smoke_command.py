#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
ppt_smoke 管理命令测试。
@Project : SCP-cv
@File : test_ppt_smoke_command.py
@Author : Qintsg
@Date : 2026-07-11
'''
from __future__ import annotations

from io import StringIO
from pathlib import Path

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from pytest import MonkeyPatch

from scp_cv.apps.playback.models import MediaSource, SourceType


@pytest.mark.django_db
def test_ppt_smoke_maps_four_source_ids_to_requested_windows(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """公开命令应按 windows 顺序解析四个 PPT source id。"""
    sources: list[MediaSource] = []
    for window_id in range(1, 5):
        ppt_path = tmp_path / f"source-{window_id}.pptx"
        ppt_path.write_bytes(b"fake")
        sources.append(
            MediaSource.objects.create(
                source_type=SourceType.PPT,
                name=f"PPT {window_id}",
                uri=str(ppt_path),
                is_available=True,
            )
        )
    fake_broker = object()
    parent_hwnds = {window_id: 30_000 + window_id for window_id in range(1, 5)}
    captured: dict[str, object] = {}
    monkeypatch.setattr(
        "scp_cv.apps.dashboard.management.ppt_smoke_runtime.connect_ppt_broker",
        lambda timeout_seconds: (
            captured.update({"timeout": timeout_seconds}) or fake_broker
        ),
    )
    monkeypatch.setattr(
        "scp_cv.apps.dashboard.management.ppt_smoke_runtime.run_with_temporary_ppt_hosts",
        lambda runner: runner(parent_hwnds),
    )

    def fake_runner(
        broker: object,
        ppt_paths: dict[int, Path],
        selected_parents: dict[int, int],
        *,
        iterations: int,
        source_ids: dict[int, int],
    ) -> dict[str, object]:
        captured.update(
            {
                "broker": broker,
                "ppt_paths": ppt_paths,
                "parents": selected_parents,
                "iterations": iterations,
                "source_ids": source_ids,
            }
        )
        return {
            "success": True,
            "iterations_requested": iterations,
            "iterations_completed": iterations,
            "rounds": [],
        }

    monkeypatch.setattr(
        "scp_cv.apps.dashboard.management.commands.ppt_smoke.run_ppt_concurrency_smoke_test",
        fake_runner,
    )
    output = StringIO()

    call_command(
        "ppt_smoke",
        windows="1,2,3,4",
        source_ids=",".join(str(source.pk) for source in sources),
        iterations=2,
        timeout=45.0,
        stdout=output,
    )

    assert captured == {
        "timeout": 45.0,
        "broker": fake_broker,
        "ppt_paths": {
            window_id: Path(sources[window_id - 1].uri).resolve()
            for window_id in range(1, 5)
        },
        "parents": parent_hwnds,
        "iterations": 2,
        "source_ids": {
            window_id: sources[window_id - 1].pk
            for window_id in range(1, 5)
        },
    }
    assert "并发 PPT 物理冒烟通过：2/2 轮" in output.getvalue()


@pytest.mark.django_db
def test_ppt_smoke_rejects_empty_source_id_items(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """source id 列表含空项时应给格式错误，且不得触碰 Broker。"""
    sources: list[MediaSource] = []
    for window_id in range(1, 5):
        ppt_path = tmp_path / f"invalid-list-{window_id}.pptx"
        ppt_path.write_bytes(b"fake")
        sources.append(
            MediaSource.objects.create(
                source_type=SourceType.PPT,
                name=f"PPT {window_id}",
                uri=str(ppt_path),
                is_available=True,
            )
        )
    monkeypatch.setattr(
        "scp_cv.apps.dashboard.management.ppt_smoke_runtime.connect_ppt_broker",
        lambda _timeout_seconds: pytest.fail("格式错误时不应连接 Broker"),
    )
    malformed = ",".join(
        [str(sources[0].pk), "", *(str(source.pk) for source in sources[1:])]
    )

    with pytest.raises(CommandError, match="空项"):
        call_command(
            "ppt_smoke",
            windows="1,2,3,4",
            source_ids=malformed,
            iterations=1,
            timeout=10.0,
            stdout=StringIO(),
        )


@pytest.mark.django_db
def test_ppt_smoke_rejects_registered_source_with_missing_file(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """媒体源记录存在但文件丢失时，应在连接 Broker 前报告 source id。"""
    missing_path = tmp_path / "missing.pptx"
    source = MediaSource.objects.create(
        source_type=SourceType.PPT,
        name="Missing PPT",
        uri=str(missing_path),
        is_available=True,
    )
    monkeypatch.setattr(
        "scp_cv.apps.dashboard.management.ppt_smoke_runtime.connect_ppt_broker",
        lambda _timeout_seconds: pytest.fail("文件缺失时不应连接 Broker"),
    )

    with pytest.raises(CommandError, match=rf"媒体源 {source.pk}.*文件不存在"):
        call_command(
            "ppt_smoke",
            windows="1,2,3,4",
            source_ids=str(source.pk),
            iterations=1,
            timeout=10.0,
            stdout=StringIO(),
        )


@pytest.mark.django_db
def test_ppt_smoke_reuses_one_source_id_for_all_windows(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """单个 source id 应映射到四个窗口并保留三轮默认值。"""
    ppt_path = tmp_path / "shared.pptx"
    ppt_path.write_bytes(b"fake")
    source = MediaSource.objects.create(
        source_type=SourceType.PPT,
        name="Shared PPT",
        uri=str(ppt_path),
        is_available=True,
    )
    parent_hwnds = {window_id: 40_000 + window_id for window_id in range(1, 5)}
    captured: dict[str, object] = {}
    monkeypatch.setattr(
        "scp_cv.apps.dashboard.management.ppt_smoke_runtime.connect_ppt_broker",
        lambda _timeout_seconds: object(),
    )
    monkeypatch.setattr(
        "scp_cv.apps.dashboard.management.ppt_smoke_runtime.run_with_temporary_ppt_hosts",
        lambda runner: runner(parent_hwnds),
    )

    def fake_runner(
        _broker: object,
        ppt_paths: dict[int, Path],
        _parents: dict[int, int],
        *,
        iterations: int,
        source_ids: dict[int, int],
    ) -> dict[str, object]:
        captured.update(
            {
                "ppt_paths": ppt_paths,
                "iterations": iterations,
                "source_ids": source_ids,
            }
        )
        return {
            "success": True,
            "iterations_requested": iterations,
            "iterations_completed": iterations,
            "rounds": [],
        }

    monkeypatch.setattr(
        "scp_cv.apps.dashboard.management.commands.ppt_smoke.run_ppt_concurrency_smoke_test",
        fake_runner,
    )

    call_command(
        "ppt_smoke",
        windows="1,2,3,4",
        source_ids=str(source.pk),
        stdout=StringIO(),
    )

    assert captured == {
        "ppt_paths": {window_id: ppt_path.resolve() for window_id in range(1, 5)},
        "iterations": 3,
        "source_ids": {window_id: source.pk for window_id in range(1, 5)},
    }


@pytest.mark.django_db
def test_ppt_smoke_returns_nonzero_after_invariant_failure(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """任一现场不变量失败时应保留 JSON 并以 CommandError 返回非零。"""
    ppt_path = tmp_path / "failed.pptx"
    ppt_path.write_bytes(b"fake")
    source = MediaSource.objects.create(
        source_type=SourceType.PPT,
        name="Failed PPT",
        uri=str(ppt_path),
        is_available=True,
    )
    monkeypatch.setattr(
        "scp_cv.apps.dashboard.management.ppt_smoke_runtime.connect_ppt_broker",
        lambda _timeout_seconds: object(),
    )
    monkeypatch.setattr(
        "scp_cv.apps.dashboard.management.ppt_smoke_runtime.run_with_temporary_ppt_hosts",
        lambda runner: runner({window_id: 50_000 + window_id for window_id in range(1, 5)}),
    )
    monkeypatch.setattr(
        "scp_cv.apps.dashboard.management.commands.ppt_smoke.run_ppt_concurrency_smoke_test",
        lambda *_args, **_kwargs: {
            "success": False,
            "iterations_requested": 3,
            "iterations_completed": 0,
            "rounds": [
                {
                    "iteration": 1,
                    "status": "failed",
                    "error_message": "重开后 HWND 与窗口 2 重复",
                }
            ],
        },
    )
    output = StringIO()

    with pytest.raises(CommandError, match="重开后 HWND 与窗口 2 重复"):
        call_command(
            "ppt_smoke",
            windows="1,2,3,4",
            source_ids=str(source.pk),
            stdout=output,
        )

    assert '"success": false' in output.getvalue()


@pytest.mark.django_db
def test_ppt_smoke_rejects_iteration_range_before_connecting_broker(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """轮数越界应在连接 Broker 或创建桌面窗口前直接拒绝。"""
    ppt_path = tmp_path / "iterations.pptx"
    ppt_path.write_bytes(b"fake")
    source = MediaSource.objects.create(
        source_type=SourceType.PPT,
        name="Iterations PPT",
        uri=str(ppt_path),
        is_available=True,
    )
    monkeypatch.setattr(
        "scp_cv.apps.dashboard.management.ppt_smoke_runtime.connect_ppt_broker",
        lambda _timeout_seconds: pytest.fail("轮数越界时不应连接 Broker"),
    )

    with pytest.raises(CommandError, match="1-10"):
        call_command(
            "ppt_smoke",
            windows="1,2,3,4",
            source_ids=str(source.pk),
            iterations=0,
            stdout=StringIO(),
        )
