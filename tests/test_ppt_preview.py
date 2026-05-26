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

    previews = ppt_preview.export_ppt_slide_previews(_make_ppt_file(tmp_path), 7)

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

    previews = ppt_preview.export_ppt_slide_previews(_make_ppt_file(tmp_path), 8)

    assert previews == ["/media/ppt_previews/8/slide-1.png"]
    assert calls == ["powerpoint"]


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

    previews = ppt_preview.export_ppt_slide_previews(_make_ppt_file(tmp_path), 9)

    assert previews == []
    assert calls == ["libreoffice"]
