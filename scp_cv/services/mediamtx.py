#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
MediaMTX 集成服务：管理 MediaMTX 进程、检测流状态、提供 SRT/RTSP 连接入口。
与 Django 应用解耦，仅通过服务层调用。
@Project : SCP-cv
@File : mediamtx.py
@Author : Qintsg
@Date : 2026-04-14
'''
from __future__ import annotations

import logging
import socket
import subprocess
from typing import Optional

import requests
from django.conf import settings
from django.utils import timezone

from scp_cv.apps.streams.models import StreamSource, StreamState
from scp_cv.services.executables import get_mediamtx_executable

logger = logging.getLogger(__name__)

# MediaMTX 连接参数默认读取 Django settings，便于部署时按局域网环境覆盖。
_MEDIAMTX_API_BASE = str(getattr(settings, "MEDIAMTX_API_BASE", "http://127.0.0.1:9997"))

# RTSP 服务端口（与 mediamtx.yml 中 rtspAddress 一致）
_RTSP_PORT = int(getattr(settings, "MEDIAMTX_RTSP_PORT", 8554))

# SRT 服务端口（与 mediamtx.yml 中 srtAddress 一致）
_SRT_PORT = int(getattr(settings, "MEDIAMTX_SRT_PORT", 8890))

# MediaMTX 进程引用
_mediamtx_process: Optional[subprocess.Popen[bytes]] = None


def _detect_lan_host() -> str:
    """
    推断本机局域网地址，用于给 OBS / 外部设备展示可连接的推流入口。
    :return: 优先返回显式配置，其次返回当前默认网卡 IP，失败时回退 127.0.0.1
    """
    configured_host = str(getattr(settings, "MEDIAMTX_SRT_PUBLIC_HOST", "")).strip()
    if configured_host:
        return configured_host
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
            udp_socket.connect(("8.8.8.8", 80))
            return str(udp_socket.getsockname()[0])
    except OSError:
        return "127.0.0.1"


def _detect_read_host() -> str:
    """
    获取拉流地址主机名，默认使用局域网地址以支持其它设备读取。
    :return: SRT/RTSP 读取入口主机名
    """
    configured_host = str(getattr(settings, "MEDIAMTX_SRT_READ_HOST", "")).strip()
    if configured_host:
        return configured_host
    return _detect_lan_host()


def get_srt_publish_url(stream_identifier: str) -> str:
    """
    获取 SRT 推流地址（供 OBS 等外部设备通过 SRT 推送使用）。
    OBS 原生支持 SRT 输出，延迟 30ms。
    :param stream_identifier: 流标识符（路径名）
    :return: SRT 推流 URL
    """
    public_host = _detect_lan_host()
    return f"srt://{public_host}:{_SRT_PORT}?streamid=publish:{stream_identifier}&latency=30000"


def get_srt_read_url(stream_identifier: str) -> str:
    """
    获取 SRT 拉流地址（供播放器通过 SRT 直接读取使用）。
    跳过 RTSP 转换环节，播放器直接从 MediaMTX SRT 端口拉流，延迟更低。
    :param stream_identifier: 流标识符（路径名）
    :return: SRT 拉流 URL
    """
    read_host = _detect_read_host()
    return f"srt://{read_host}:{_SRT_PORT}?streamid=read:{stream_identifier}&latency=30000"


def get_rtsp_read_url(stream_identifier: str) -> str:
    """
    获取 RTSP 拉流地址（供播放器通过 RTSP 读取使用）。
    MediaMTX 自动将 SRT 入流转为 RTSP 供 QMediaPlayer 消费。
    :param stream_identifier: 流标识符（路径名）
    :return: RTSP 拉流 URL
    """
    read_host = _detect_read_host()
    return f"rtsp://{read_host}:{_RTSP_PORT}/{stream_identifier}"


def start_mediamtx() -> bool:
    """
    启动 MediaMTX 进程。若已在运行则跳过。
    :return: 是否成功启动
    """
    global _mediamtx_process

    if _mediamtx_process is not None and _mediamtx_process.poll() is None:
        logger.info("MediaMTX 进程已存在（pid=%d）", _mediamtx_process.pid)
        return True

    mediamtx_bin = get_mediamtx_executable()
    if mediamtx_bin is None:
        logger.error("未找到 MediaMTX 可执行文件")
        return False

    # 查找配置文件（与可执行文件同目录）
    config_path = mediamtx_bin.parent / "mediamtx.yml"
    if not config_path.exists():
        logger.warning("MediaMTX 配置文件不存在：%s", config_path)
        config_path = None

    command_args = [str(mediamtx_bin)]
    if config_path is not None:
        command_args.append(str(config_path))

    try:
        _mediamtx_process = subprocess.Popen(
            command_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(mediamtx_bin.parent),
        )
        logger.info("MediaMTX 已启动（pid=%d）", _mediamtx_process.pid)
        return True
    except OSError as start_error:
        logger.error("启动 MediaMTX 失败：%s", start_error)
        return False


def stop_mediamtx() -> None:
    """停止 MediaMTX 进程。"""
    global _mediamtx_process

    if _mediamtx_process is None:
        return

    if _mediamtx_process.poll() is None:
        _mediamtx_process.terminate()
        try:
            _mediamtx_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _mediamtx_process.kill()
            _mediamtx_process.wait(timeout=3)
        logger.info("MediaMTX 已停止")

    _mediamtx_process = None


def is_mediamtx_running() -> bool:
    """
    检测 MediaMTX 进程是否在运行。
    :return: True 表示进程活跃
    """
    if _mediamtx_process is not None and _mediamtx_process.poll() is None:
        return True

    # 备用检测：尝试访问 API
    try:
        api_response = requests.get(f"{_MEDIAMTX_API_BASE}/v3/paths/list", timeout=2)
        return api_response.status_code == 200
    except requests.RequestException:
        return False


def query_stream_paths() -> list[dict[str, object]]:
    """
    从 MediaMTX API 查询当前所有活跃路径（流）。
    :return: 路径信息列表
    """
    try:
        api_response = requests.get(
            f"{_MEDIAMTX_API_BASE}/v3/paths/list",
            timeout=3,
        )
        if api_response.status_code != 200:
            logger.warning("MediaMTX API 返回状态 %d", api_response.status_code)
            return []
        response_data = api_response.json()
        return response_data.get("items", [])
    except requests.RequestException as api_error:
        logger.warning("查询 MediaMTX 路径失败：%s", api_error)
        return []


def sync_stream_states() -> dict[str, int]:
    """
    从 MediaMTX API 同步所有流状态到数据库，并自动注册新发现的流。
    - 新发现的路径 → 创建 StreamSource 记录，标记为在线
    - 已注册且在线 → 更新 last_seen_at
    - 已注册但消失 → 标记为离线
    :return: 包含 registered / updated / went_offline 计数的字典
    """
    active_paths = query_stream_paths()

    # 构建活跃路径名称集合及详情映射
    online_path_details: dict[str, dict[str, object]] = {}
    for path_info in active_paths:
        path_name = path_info.get("name", "")
        if path_name:
            online_path_details[path_name] = path_info

    now_timestamp = timezone.now()
    result_counts = {"registered": 0, "updated": 0, "went_offline": 0}

    # 获取已注册的所有流标识符
    existing_identifiers: set[str] = set(
        StreamSource.objects.values_list("stream_identifier", flat=True)
    )

    # 自动注册新发现的流
    new_identifiers = set(online_path_details.keys()) - existing_identifiers
    for new_identifier in new_identifiers:
        # 自动生成流名称：使用路径名作为显示名
        auto_name = f"[自动] {new_identifier}"
        # 生成 SRT 读取地址供播放器使用
        srt_url = get_srt_read_url(new_identifier)
        StreamSource.objects.create(
            name=auto_name,
            stream_identifier=new_identifier,
            stream_url=srt_url,
            is_active=True,
            is_online=True,
            current_state=StreamState.ONLINE,
            last_connected_at=now_timestamp,
            last_seen_at=now_timestamp,
        )
        logger.info("自动注册新流：%s（%s）", auto_name, new_identifier)
        result_counts["registered"] += 1

    # 更新已注册流的在线/离线状态
    for stream in StreamSource.objects.all():
        if stream.stream_identifier in online_path_details:
            # 流在线
            if not stream.is_online:
                stream.is_online = True
                stream.current_state = StreamState.ONLINE
                stream.last_connected_at = now_timestamp
                stream.last_seen_at = now_timestamp
                stream.save(update_fields=[
                    "is_online", "current_state",
                    "last_connected_at", "last_seen_at",
                ])
                result_counts["updated"] += 1
            else:
                # 已在线，仅更新 last_seen_at
                stream.last_seen_at = now_timestamp
                stream.save(update_fields=["last_seen_at"])
        else:
            # 流离线
            if stream.is_online:
                stream.is_online = False
                stream.current_state = StreamState.OFFLINE
                stream.save(update_fields=["is_online", "current_state"])
                result_counts["went_offline"] += 1

    total_changes = sum(result_counts.values())
    if total_changes > 0:
        logger.info(
            "流同步完成：新注册 %d，状态更新 %d，离线 %d",
            result_counts["registered"],
            result_counts["updated"],
            result_counts["went_offline"],
        )

    return result_counts
