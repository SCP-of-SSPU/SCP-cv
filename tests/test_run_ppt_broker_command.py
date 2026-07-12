#!/user/bin/env python
# -*- coding: UTF-8 -*-
"""
run_ppt_broker 管理命令测试。
@Project : SCP-cv
@File : test_run_ppt_broker_command.py
@Author : Qintsg
@Date : 2026-07-11
"""
from __future__ import annotations

from pytest import MonkeyPatch

from scp_cv.apps.dashboard.management.commands.run_ppt_broker import Command


def test_run_ppt_broker_command_serves_default_runtime(
    monkeypatch: MonkeyPatch,
) -> None:
    """
    管理命令应把生命周期交给 Broker 深模块的默认 server。
    :param monkeypatch: pytest monkeypatch fixture
    :return: None
    """
    serve_calls: list[bool] = []
    monkeypatch.setattr(
        "scp_cv.player.ppt_broker.serve_broker",
        lambda: serve_calls.append(True),
        raising=False,
    )

    Command().handle()

    assert serve_calls == [True]
