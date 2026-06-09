#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PPT 预览 worker 测试，验证隔离进程入口的 JSON 协议。
@Project : SCP-cv
@File : test_ppt_preview_worker.py
@Author : Qintsg
@Date : 2026-05-27
'''
from __future__ import annotations

import json
import os
import subprocess
import types
from pathlib import Path

from pytest import CaptureFixture, MonkeyPatch

from scp_cv.services import ppt_preview, ppt_preview_worker


def test_worker_main_outputs_preview_json(
    monkeypatch: MonkeyPatch,
    capsys: CaptureFixture[str],
) -> None:
    """worker 成功时应输出单行 JSON 供父进程解析。"""
    calls: list[tuple[str, int]] = []

    def fake_export(file_path: object, source_id: int) -> list[str]:
        """
        模拟进程内 PPT 预览导出。
        :param file_path: PPT 文件路径
        :param source_id: 媒体源 ID
        :return: 预览 URL 列表
        """
        calls.append((str(file_path), source_id))
        return ["/media/ppt_previews/21/slide-1.png"]

    monkeypatch.setitem(
        ppt_preview_worker.sys.modules,
        "django",
        types.SimpleNamespace(setup=lambda: None),
    )
    monkeypatch.setattr(ppt_preview, "export_ppt_slide_previews_in_process", fake_export)

    exit_code = ppt_preview_worker.main(["demo.pptx", "21"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out.strip())
    assert exit_code == 0
    assert calls == [("demo.pptx", 21)]
    assert payload == {
        "success": True,
        "previews": ["/media/ppt_previews/21/slide-1.png"],
        "error": "",
    }


def test_worker_main_reports_invalid_arguments(capsys: CaptureFixture[str]) -> None:
    """worker 参数错误时应返回非零退出码和 JSON 错误。"""
    exit_code = ppt_preview_worker.main([])

    captured = capsys.readouterr()
    payload = json.loads(captured.out.strip())
    assert exit_code == 2
    assert payload["success"] is False
    assert payload["previews"] == []


def test_preview_worker_subprocess_receives_project_pythonpath(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    """父进程启动预览 worker 时应显式传入项目根 PYTHONPATH。"""
    captured: dict[str, object] = {}
    ppt_file = tmp_path / "demo.pptx"
    ppt_file.write_bytes(_minimal_pptx_bytes())

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        """
        记录 worker 启动参数并返回空预览结果。
        :param command: 子进程命令
        :param kwargs: subprocess.run 关键字参数
        :return: 完成结果
        """
        captured["command"] = command
        captured["kwargs"] = kwargs
        return subprocess.CompletedProcess(command, 0, stdout='{"success": true, "previews": []}\n', stderr="")

    monkeypatch.setattr(ppt_preview.subprocess, "run", fake_run)

    previews = ppt_preview.export_ppt_slide_previews(ppt_file, 9)

    assert previews == []
    env = captured["kwargs"]["env"]  # type: ignore[index]
    assert str(ppt_preview.settings.BASE_DIR) in str(env["PYTHONPATH"]).split(os.pathsep)  # type: ignore[index]
    assert captured["kwargs"]["cwd"] == str(ppt_preview.settings.BASE_DIR)  # type: ignore[index]


def test_worker_adds_project_root_to_sys_path(monkeypatch: MonkeyPatch) -> None:
    """worker 脚本直跑时应自行把项目根目录加入 sys.path。"""
    project_root = str(Path(ppt_preview_worker.__file__).resolve().parents[2])
    original_path = list(ppt_preview_worker.sys.path)
    monkeypatch.setattr(
        ppt_preview_worker.sys,
        "path",
        [path for path in original_path if path != project_root],
    )

    ppt_preview_worker._ensure_project_root_on_path()

    assert ppt_preview_worker.sys.path[0] == project_root


def _minimal_pptx_bytes() -> bytes:
    """
    生成可通过粗略格式检查的最小 pptx zip。
    :return: pptx 字节
    """
    import io
    import zipfile

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types />")
    return buffer.getvalue()
