#!/user/bin/env python
# -*- coding: UTF-8 -*-
"""
runall 前端环境配置辅助函数。
集中解析 Vite 环境文件，避免管理命令继续堆积实现。
@Project : SCP-cv
@File : runall_frontend.py
@Author : Qintsg
@Date : 2026-05-12
"""

from __future__ import annotations
from pathlib import Path


def resolve_frontend_port(frontend_dir: Path) -> int:
    """
    解析前端实际监听端口，优先 Vite 环境文件中的 VITE_FRONTEND_PORT。
    :param frontend_dir: 前端项目目录
    :return: 前端端口；缺省回退 Vite 默认值 5173
    """
    configured_port = (
        read_frontend_env(frontend_dir).get("VITE_FRONTEND_PORT", "").strip()
    )
    if configured_port:
        try:
            return int(configured_port)
        except ValueError:
            pass
    return 5173


def read_frontend_env(frontend_dir: Path) -> dict[str, str]:
    """
    读取 Vite 前端环境文件中的 VITE_* 变量，判断 runall 是否需要提供兜底值。
    :param frontend_dir: 前端项目目录
    :return: 合并后的前端环境变量
    """
    env_values: dict[str, str] = {}
    for env_name in (
        ".env",
        ".env.local",
        ".env.development",
        ".env.development.local",
    ):
        env_path = frontend_dir / env_name
        if not env_path.exists():
            continue
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            parsed_pair = parse_frontend_env_line(raw_line)
            if parsed_pair is None:
                continue
            key, value = parsed_pair
            if key.startswith("VITE_"):
                env_values[key] = value
    return env_values


def parse_frontend_env_line(raw_line: str) -> tuple[str, str] | None:
    """
    解析 Vite .env 的基础 key=value 行，支持常见引号和 export 前缀。
    :param raw_line: 原始行文本
    :return: 变量名和值；空行或注释返回 None
    """
    stripped_line = raw_line.strip()
    if not stripped_line or stripped_line.startswith("#") or "=" not in stripped_line:
        return None
    if stripped_line.startswith("export "):
        stripped_line = stripped_line[7:].lstrip()
    key, value = stripped_line.split("=", 1)
    normalized_key = key.strip()
    normalized_value = value.strip()
    if (
        len(normalized_value) >= 2
        and normalized_value[0] == normalized_value[-1]
        and normalized_value[0] in {"'", '"'}
    ):
        normalized_value = normalized_value[1:-1]
    if not normalized_key:
        return None
    return normalized_key, normalized_value
