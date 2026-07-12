#!/user/bin/env python
# -*- coding: UTF-8 -*-
"""
Django 管理命令：运行唯一 PowerPoint Broker。
@Project : SCP-cv
@File : run_ppt_broker.py
@Author : Qintsg
@Date : 2026-07-11
"""
from __future__ import annotations

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """在当前进程中运行 PowerPoint Broker server。"""

    help = "运行唯一 PowerPoint Broker"

    def handle(self, **_options: object) -> None:
        """
        使用 runtime 默认命名管道和认证信息运行 Broker。
        :param _options: Django 管理命令参数
        :return: None
        """
        from scp_cv.player.ppt_broker import serve_broker

        serve_broker()
