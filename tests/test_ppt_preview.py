#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PPT 预览导出后端选择测试，覆盖媒体源显式播放器策略。
@Project : SCP-cv
@File : test_ppt_preview.py
@Author : Qintsg
@Date : 2026-05-26
'''
from __future__ import annotations

import subprocess
from pathlib import Path

from pytest import MonkeyPatch

from scp_cv.services import ppt_preview


def _make_ppt_file(tmp_path: Path) -> Path:
    """
    创建可通过候选判断的传统 PPT 文件。
    :param tmp_path: pytest 临时目录
    :return: PPT 文件路径
    """
    ppt_file = tmp_path / "demo.ppt"
    ppt_file.write_bytes(b"placeholder")
    return ppt_file


def test_preview_uses_selected_libreoffice(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    """媒体源选择 LibreOffice 时应只使用 LibreOffice 导出预览。"""
    calls: list[str] = []

    def libreoffice_export(file_path: Path, source_id: int) -> list[str]:
        """
        模拟 LibreOffice 导出成功。
        :param file_path: PPT 文件路径
        :param source_id: 媒体源 ID
        :return: 预览 URL 列表
        """
        calls.append("libreoffice")
        return [f"/media/ppt_previews/{source_id}/slide-1.png"]

    def powerpoint_export(file_path: Path, source_id: int) -> list[str]:
        """
        PowerPoint 不应被调用。
        :param file_path: PPT 文件路径
        :param source_id: 媒体源 ID
        :return: 空列表
        """
        calls.append("powerpoint")
        return []

    monkeypatch.setattr(ppt_preview.os, "name", "nt")
    monkeypatch.setattr(ppt_preview, "_source_ppt_backend", lambda _source_id: "libreoffice")
    monkeypatch.setattr(ppt_preview, "export_ppt_slide_previews_with_libreoffice", libreoffice_export)
    monkeypatch.setattr(ppt_preview, "export_ppt_slide_previews_with_powerpoint", powerpoint_export)

    previews = ppt_preview.export_ppt_slide_previews_in_process(_make_ppt_file(tmp_path), 7)

    assert previews == ["/media/ppt_previews/7/slide-1.png"]
    assert calls == ["libreoffice"]


def test_preview_uses_selected_powerpoint(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    """媒体源选择 PowerPoint 时应只使用 PowerPoint 导出预览。"""
    calls: list[str] = []

    def libreoffice_export(file_path: Path, source_id: int) -> list[str]:
        """
        LibreOffice 不应被调用。
        :param file_path: PPT 文件路径
        :param source_id: 媒体源 ID
        :return: 空列表
        """
        calls.append("libreoffice")
        return []

    def powerpoint_export(file_path: Path, source_id: int) -> list[str]:
        """
        模拟 PowerPoint 导出成功。
        :param file_path: PPT 文件路径
        :param source_id: 媒体源 ID
        :return: 预览 URL 列表
        """
        calls.append("powerpoint")
        return [f"/media/ppt_previews/{source_id}/slide-1.png"]

    monkeypatch.setattr(ppt_preview.os, "name", "nt")
    monkeypatch.setattr(ppt_preview, "_source_ppt_backend", lambda _source_id: "powerpoint")
    monkeypatch.setattr(ppt_preview, "export_ppt_slide_previews_with_libreoffice", libreoffice_export)
    monkeypatch.setattr(ppt_preview, "export_ppt_slide_previews_with_powerpoint", powerpoint_export)

    previews = ppt_preview.export_ppt_slide_previews_in_process(_make_ppt_file(tmp_path), 8)

    assert previews == ["/media/ppt_previews/8/slide-1.png"]
    assert calls == ["powerpoint"]


def test_preview_uses_selected_wps(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    """媒体源选择 WPS 时应只使用 WPS 导出预览。"""
    calls: list[str] = []

    def libreoffice_export(file_path: Path, source_id: int) -> list[str]:
        """
        LibreOffice 不应被调用。
        :param file_path: PPT 文件路径
        :param source_id: 媒体源 ID
        :return: 空列表
        """
        calls.append("libreoffice")
        return []

    def powerpoint_export(file_path: Path, source_id: int) -> list[str]:
        """
        PowerPoint 不应被调用。
        :param file_path: PPT 文件路径
        :param source_id: 媒体源 ID
        :return: 空列表
        """
        calls.append("powerpoint")
        return []

    def wps_export(file_path: Path, source_id: int) -> list[str]:
        """
        模拟 WPS 导出成功。
        :param file_path: PPT 文件路径
        :param source_id: 媒体源 ID
        :return: 预览 URL 列表
        """
        calls.append("wps")
        return [f"/media/ppt_previews/{source_id}/slide-1.png"]

    monkeypatch.setattr(ppt_preview.os, "name", "nt")
    monkeypatch.setattr(ppt_preview, "_source_ppt_backend", lambda _source_id: "wps")
    monkeypatch.setattr(ppt_preview, "export_ppt_slide_previews_with_libreoffice", libreoffice_export)
    monkeypatch.setattr(ppt_preview, "export_ppt_slide_previews_with_powerpoint", powerpoint_export)
    monkeypatch.setattr(ppt_preview, "export_ppt_slide_previews_with_wps", wps_export)

    previews = ppt_preview.export_ppt_slide_previews_in_process(_make_ppt_file(tmp_path), 10)

    assert previews == ["/media/ppt_previews/10/slide-1.png"]
    assert calls == ["wps"]


def test_selected_libreoffice_never_falls_back_to_powerpoint(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    """选择 LibreOffice 时即使导出失败也不应回退 PowerPoint。"""
    calls: list[str] = []

    def libreoffice_export(file_path: Path, source_id: int) -> list[str]:
        """
        模拟 LibreOffice 导出失败。
        :param file_path: PPT 文件路径
        :param source_id: 媒体源 ID
        :return: 空列表
        """
        calls.append("libreoffice")
        return []

    def powerpoint_export(file_path: Path, source_id: int) -> list[str]:
        """
        PowerPoint 不应被调用。
        :param file_path: PPT 文件路径
        :param source_id: 媒体源 ID
        :return: 空列表
        """
        calls.append("powerpoint")
        return []

    monkeypatch.setattr(ppt_preview.os, "name", "nt")
    monkeypatch.setattr(ppt_preview, "_source_ppt_backend", lambda _source_id: "libreoffice")
    monkeypatch.setattr(ppt_preview, "export_ppt_slide_previews_with_libreoffice", libreoffice_export)
    monkeypatch.setattr(ppt_preview, "export_ppt_slide_previews_with_powerpoint", powerpoint_export)

    previews = ppt_preview.export_ppt_slide_previews_in_process(_make_ppt_file(tmp_path), 9)

    assert previews == []
    assert calls == ["libreoffice"]


def test_preview_dispatches_worker_with_selected_backend(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    """公网入口应只启动隔离 worker，不在 Django 进程内加载 Office 运行时。"""
    captured: dict[str, object] = {}

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        """
        模拟 PPT 预览 worker 成功返回。
        :param command: 子进程命令
        :param kwargs: subprocess.run 关键字参数
        :return: 模拟完成结果
        """
        captured["command"] = command
        captured["kwargs"] = kwargs
        return subprocess.CompletedProcess(
            args=command,
            returncode=0,
            stdout='{"success": true, "previews": ["/media/ppt_previews/11/slide-1.png"], "error": ""}\n',
            stderr="",
        )

    ppt_file = _make_ppt_file(tmp_path)
    monkeypatch.setattr(ppt_preview.os, "name", "nt")
    monkeypatch.setattr(ppt_preview, "_source_ppt_backend", lambda _source_id: "wps")
    monkeypatch.setattr(ppt_preview.subprocess, "run", fake_run)

    previews = ppt_preview.export_ppt_slide_previews(ppt_file, 11)

    assert previews == ["/media/ppt_previews/11/slide-1.png"]
    assert captured["command"] == [
        ppt_preview.sys.executable,
        "-m",
        "scp_cv.services.ppt_preview_worker",
        str(ppt_file),
        "11",
        "wps",
    ]
    assert captured["kwargs"]["capture_output"] is True
    assert captured["kwargs"]["check"] is False


def test_preview_worker_failure_returns_empty(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    """worker 异常退出不应影响上传流程。"""
    ppt_file = _make_ppt_file(tmp_path)

    def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        """
        模拟 worker 异常退出。
        :param command: 子进程命令
        :param _kwargs: subprocess.run 关键字参数
        :return: 模拟完成结果
        """
        return subprocess.CompletedProcess(args=command, returncode=1, stdout="", stderr="boom")

    monkeypatch.setattr(ppt_preview.os, "name", "nt")
    monkeypatch.setattr(ppt_preview, "_source_ppt_backend", lambda _source_id: "libreoffice")
    monkeypatch.setattr(ppt_preview.subprocess, "run", fake_run)

    assert ppt_preview.export_ppt_slide_previews(ppt_file, 12) == []


def test_parse_worker_preview_output_ignores_noisy_lines() -> None:
    """worker stdout 中有普通输出时应解析最后一行 JSON 结果。"""
    stdout = "noise\n{\"success\": true, \"previews\": [\"/media/ppt_previews/13/slide-1.png\"]}\n"

    previews = ppt_preview._parse_worker_preview_output(stdout)

    assert previews == ["/media/ppt_previews/13/slide-1.png"]


def test_libreoffice_preview_uses_libreoffice_python_worker(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    """LibreOffice 预览应由 LibreOffice 自带 Python 执行，避免导入项目 Python 的 pyuno。"""
    captured: dict[str, object] = {}
    lo_python = tmp_path / "lo-python.exe"
    ppt_file = _make_ppt_file(tmp_path)
    preview_dir = tmp_path / "previews"

    def fail_start_session(**_kwargs: object) -> object:
        """
        确认不会走项目 Python 进程内 pyuno 导入路径。
        :param _kwargs: 启动参数
        :return: 不返回
        """
        raise AssertionError("should not import pyuno in project Python")

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        """
        模拟 LibreOffice Python worker 成功导出。
        :param command: 子进程命令
        :param kwargs: subprocess.run 参数
        :return: 模拟完成结果
        """
        captured["command"] = command
        captured["kwargs"] = kwargs
        return subprocess.CompletedProcess(
            args=command,
            returncode=0,
            stdout='{"success": true, "previews": ["slide-1.png", "slide-2.png"], "error": ""}\n',
            stderr="",
        )

    monkeypatch.setattr(ppt_preview.lo_runtime, "start_libreoffice_session", fail_start_session)
    monkeypatch.setattr(ppt_preview.lo_runtime, "resolve_libreoffice_python_executable", lambda: lo_python)
    monkeypatch.setattr(ppt_preview.subprocess, "run", fake_run)

    previews = ppt_preview._run_libreoffice_preview_worker(ppt_file, Path("ppt_previews/31"), preview_dir)

    assert previews == ["/media/ppt_previews/31/slide-1.png", "/media/ppt_previews/31/slide-2.png"]
    assert captured["command"] == [
        str(lo_python),
        "-m",
        "scp_cv.libreoffice_worker",
        "preview",
        str(ppt_file),
        str(preview_dir),
    ]
