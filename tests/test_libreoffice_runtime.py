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

from pathlib import Path

from pytest import MonkeyPatch

from scp_cv import libreoffice


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
