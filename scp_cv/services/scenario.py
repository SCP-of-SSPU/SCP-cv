#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
预案管理服务，负责预案的 CRUD 以及激活（一键应用窗口配置）。
预案是窗口 1/2 播放配置的快照，支持独立双窗口和拼接两种模式。
激活预案时根据 resume 策略决定是否保留已有播放进度。
@Project : SCP-cv
@File : scenario.py
@Author : Qintsg
@Date : 2026-04-14
'''
from __future__ import annotations

import logging
from typing import Optional

from scp_cv.apps.playback.models import (
    MediaSource,
    PlaybackState,
    Scenario,
)
from scp_cv.services.playback import (
    PlaybackError,
    close_source,
    get_all_sessions_snapshot,
    get_or_create_session,
    open_source,
    set_splice_mode,
)

logger = logging.getLogger(__name__)


class ScenarioError(Exception):
    """预案操作过程中的业务异常。"""


# ══════════════════════════════════════════════════════════════
# 查询
# ══════════════════════════════════════════════════════════════

def list_scenarios() -> list[dict[str, object]]:
    """
    获取所有预案的摘要列表。
    :return: 预案字典列表（按更新时间倒序）
    """
    scenarios = Scenario.objects.select_related(
        "window1_source", "window2_source",
    ).all()
    return [_scenario_to_dict(scenario) for scenario in scenarios]


def get_scenario(scenario_id: int) -> dict[str, object]:
    """
    获取指定预案的详细信息。
    :param scenario_id: 预案主键
    :return: 预案字典
    :raises ScenarioError: 预案不存在时
    """
    try:
        scenario = Scenario.objects.select_related(
            "window1_source", "window2_source",
        ).get(pk=scenario_id)
    except Scenario.DoesNotExist as not_found:
        raise ScenarioError(f"预案 id={scenario_id} 不存在") from not_found
    return _scenario_to_dict(scenario)


# ══════════════════════════════════════════════════════════════
# 创建 / 更新 / 删除
# ══════════════════════════════════════════════════════════════

def create_scenario(
    name: str,
    description: str = "",
    is_splice_mode: bool = False,
    window1_source_id: Optional[int] = None,
    window1_autoplay: bool = True,
    window1_resume: bool = True,
    window2_source_id: Optional[int] = None,
    window2_autoplay: bool = True,
    window2_resume: bool = True,
) -> Scenario:
    """
    创建新预案。
    :param name: 预案名称
    :param description: 描述（可选）
    :param is_splice_mode: 是否启用拼接模式
    :param window1_source_id: 窗口 1 媒体源 ID（None 表示不绑定）
    :param window1_autoplay: 窗口 1 是否自动播放
    :param window1_resume: 窗口 1 是否保留进度
    :param window2_source_id: 窗口 2 媒体源 ID
    :param window2_autoplay: 窗口 2 是否自动播放
    :param window2_resume: 窗口 2 是否保留进度
    :return: 创建后的 Scenario 实例
    :raises ScenarioError: 名称为空或媒体源不存在时
    """
    if not name.strip():
        raise ScenarioError("预案名称不能为空")

    # 校验媒体源引用
    window1_source = _resolve_source(window1_source_id)
    window2_source = _resolve_source(window2_source_id)

    scenario = Scenario.objects.create(
        name=name.strip(),
        description=description.strip(),
        is_splice_mode=is_splice_mode,
        window1_source=window1_source,
        window1_autoplay=window1_autoplay,
        window1_resume=window1_resume,
        window2_source=window2_source,
        window2_autoplay=window2_autoplay,
        window2_resume=window2_resume,
    )
    logger.info("创建预案「%s」(id=%d)", scenario.name, scenario.pk)
    return scenario


def update_scenario(
    scenario_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    is_splice_mode: Optional[bool] = None,
    window1_source_id: Optional[int] = None,
    window1_autoplay: Optional[bool] = None,
    window1_resume: Optional[bool] = None,
    window2_source_id: Optional[int] = None,
    window2_autoplay: Optional[bool] = None,
    window2_resume: Optional[bool] = None,
    # 用于区分"未传入"和"显式传入 None"
    _window1_source_provided: bool = False,
    _window2_source_provided: bool = False,
) -> Scenario:
    """
    更新已有预案的配置。只修改显式传入的字段。
    :param scenario_id: 预案主键
    :param name: 新名称（None 表示不修改）
    :param description: 新描述
    :param is_splice_mode: 新拼接模式设置
    :param window1_source_id: 窗口 1 新媒体源 ID
    :param window1_autoplay: 窗口 1 自动播放
    :param window1_resume: 窗口 1 保留进度
    :param window2_source_id: 窗口 2 新媒体源 ID
    :param window2_autoplay: 窗口 2 自动播放
    :param window2_resume: 窗口 2 保留进度
    :param _window1_source_provided: 内部标记：是否显式设置窗口 1 源
    :param _window2_source_provided: 内部标记：是否显式设置窗口 2 源
    :return: 更新后的 Scenario 实例
    :raises ScenarioError: 预案不存在或参数无效时
    """
    try:
        scenario = Scenario.objects.get(pk=scenario_id)
    except Scenario.DoesNotExist as not_found:
        raise ScenarioError(f"预案 id={scenario_id} 不存在") from not_found

    if name is not None:
        if not name.strip():
            raise ScenarioError("预案名称不能为空")
        scenario.name = name.strip()
    if description is not None:
        scenario.description = description.strip()
    if is_splice_mode is not None:
        scenario.is_splice_mode = is_splice_mode

    # 窗口 1 配置
    if _window1_source_provided:
        scenario.window1_source = _resolve_source(window1_source_id)
    if window1_autoplay is not None:
        scenario.window1_autoplay = window1_autoplay
    if window1_resume is not None:
        scenario.window1_resume = window1_resume

    # 窗口 2 配置
    if _window2_source_provided:
        scenario.window2_source = _resolve_source(window2_source_id)
    if window2_autoplay is not None:
        scenario.window2_autoplay = window2_autoplay
    if window2_resume is not None:
        scenario.window2_resume = window2_resume

    scenario.save()
    logger.info("更新预案「%s」(id=%d)", scenario.name, scenario.pk)
    return scenario


def delete_scenario(scenario_id: int) -> None:
    """
    删除指定预案。
    :param scenario_id: 预案主键
    :raises ScenarioError: 预案不存在时
    """
    try:
        scenario = Scenario.objects.get(pk=scenario_id)
    except Scenario.DoesNotExist as not_found:
        raise ScenarioError(f"预案 id={scenario_id} 不存在") from not_found

    scenario_name = scenario.name
    scenario.delete()
    logger.info("删除预案「%s」(id=%d)", scenario_name, scenario_id)


# ══════════════════════════════════════════════════════════════
# 激活预案
# ══════════════════════════════════════════════════════════════

def activate_scenario(scenario_id: int) -> list[dict[str, object]]:
    """
    激活预案：一键应用预设的窗口 1/2 播放配置。
    根据每个窗口的 resume 策略决定是否保留已有进度：
    - resume=True 且当前窗口已打开相同源 → 跳过重新打开（保持进度）
    - resume=False 或源不同 → 关闭后重新打开
    拼接模式下窗口 2 由拼接逻辑自动同步，不单独配置。
    :param scenario_id: 预案主键
    :return: 激活后所有窗口的状态快照列表
    :raises ScenarioError: 预案不存在或激活失败时
    """
    try:
        scenario = Scenario.objects.select_related(
            "window1_source", "window2_source",
        ).get(pk=scenario_id)
    except Scenario.DoesNotExist as not_found:
        raise ScenarioError(f"预案 id={scenario_id} 不存在") from not_found

    logger.info("开始激活预案「%s」(id=%d)", scenario.name, scenario.pk)

    try:
        if scenario.is_splice_mode:
            _activate_splice_mode(scenario)
        else:
            _activate_independent_mode(scenario)
    except PlaybackError as playback_err:
        raise ScenarioError(f"激活预案失败：{playback_err}") from playback_err

    logger.info("预案「%s」激活完成", scenario.name)
    return get_all_sessions_snapshot()


# ══════════════════════════════════════════════════════════════
# 内部工具函数
# ══════════════════════════════════════════════════════════════

def _resolve_source(source_id: Optional[int]) -> Optional[MediaSource]:
    """
    根据 ID 查询媒体源，None 或 0 表示不绑定。
    :param source_id: 媒体源主键（None 或 0 表示无源）
    :return: MediaSource 实例或 None
    :raises ScenarioError: ID 大于 0 但不存在时
    """
    if not source_id:
        return None
    try:
        return MediaSource.objects.get(pk=source_id)
    except MediaSource.DoesNotExist as not_found:
        raise ScenarioError(f"媒体源 id={source_id} 不存在") from not_found


def _scenario_to_dict(scenario: Scenario) -> dict[str, object]:
    """
    将 Scenario 模型实例序列化为字典。
    :param scenario: Scenario 实例
    :return: 包含所有预案字段的字典
    """
    return {
        "id": scenario.pk,
        "name": scenario.name,
        "description": scenario.description,
        "is_splice_mode": scenario.is_splice_mode,
        # 窗口 1
        "window1_source_id": scenario.window1_source_id,
        "window1_source_name": scenario.window1_source.name if scenario.window1_source else "",
        "window1_autoplay": scenario.window1_autoplay,
        "window1_resume": scenario.window1_resume,
        # 窗口 2
        "window2_source_id": scenario.window2_source_id,
        "window2_source_name": scenario.window2_source.name if scenario.window2_source else "",
        "window2_autoplay": scenario.window2_autoplay,
        "window2_resume": scenario.window2_resume,
        # 时间戳
        "created_at": scenario.created_at.isoformat() if scenario.created_at else "",
        "updated_at": scenario.updated_at.isoformat() if scenario.updated_at else "",
    }


def _should_reopen_source(
    window_id: int,
    target_source: Optional[MediaSource],
    resume: bool,
) -> bool:
    """
    判断是否需要重新打开窗口源。
    resume=True 且当前窗口已在播放相同源时返回 False（保留进度）。
    :param window_id: 窗口编号
    :param target_source: 预案配置的媒体源
    :param resume: 是否保留进度
    :return: True 需要重新打开，False 跳过
    """
    if target_source is None:
        return False

    session = get_or_create_session(window_id)
    # 如果当前窗口正在播放相同源且启用了进度保留，则跳过
    same_source = (
        session.media_source_id is not None
        and session.media_source_id == target_source.pk
    )
    is_active = session.playback_state in (
        PlaybackState.PLAYING,
        PlaybackState.PAUSED,
        PlaybackState.LOADING,
    )
    if resume and same_source and is_active:
        logger.info(
            "窗口 %d 已在播放相同源「%s」，保留进度",
            window_id, target_source.name,
        )
        return False

    return True


def _apply_window_source(
    window_id: int,
    source: Optional[MediaSource],
    autoplay: bool,
    resume: bool,
) -> None:
    """
    为指定窗口应用预案中的媒体源配置。
    :param window_id: 窗口编号（1 或 2）
    :param source: 目标媒体源（None 表示关闭该窗口）
    :param autoplay: 是否自动播放
    :param resume: 是否保留进度
    """
    if source is None:
        # 预案中该窗口无源配置，关闭当前播放
        close_source(window_id)
        return

    if not _should_reopen_source(window_id, source, resume):
        return

    # 打开新源（open_source 内部会先关闭旧源再打开）
    open_source(window_id, source.pk, autoplay=autoplay)


def _activate_splice_mode(scenario: Scenario) -> None:
    """
    拼接模式激活：启用拼接后打开窗口 1 的源，窗口 2 自动同步。
    :param scenario: 预案实例
    """
    # 先启用拼接模式
    set_splice_mode(True)

    # 打开窗口 1 的源（拼接逻辑会自动同步到窗口 2）
    if scenario.window1_source is not None:
        _apply_window_source(
            window_id=1,
            source=scenario.window1_source,
            autoplay=scenario.window1_autoplay,
            resume=scenario.window1_resume,
        )
    else:
        # 无源则关闭两个窗口
        close_source(1)


def _activate_independent_mode(scenario: Scenario) -> None:
    """
    独立模式激活：关闭拼接后分别配置窗口 1 和窗口 2。
    :param scenario: 预案实例
    """
    # 先关闭拼接模式
    set_splice_mode(False)

    # 分别配置两个窗口
    _apply_window_source(
        window_id=1,
        source=scenario.window1_source,
        autoplay=scenario.window1_autoplay,
        resume=scenario.window1_resume,
    )
    _apply_window_source(
        window_id=2,
        source=scenario.window2_source,
        autoplay=scenario.window2_autoplay,
        resume=scenario.window2_resume,
    )
