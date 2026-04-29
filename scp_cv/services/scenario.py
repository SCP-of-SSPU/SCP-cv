#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
预案管理服务，负责预案的 CRUD 以及激活（一键应用窗口配置）。
预案通过三态语义（未设置/空/设置）控制每个窗口的行为。
@Project : SCP-cv
@File : scenario.py
@Author : Qintsg
@Date : 2026-04-29
'''
from __future__ import annotations

import logging
from typing import Optional

from scp_cv.apps.playback.models import (
    BigScreenMode,
    MediaSource,
    PlaybackState,
    RuntimeState,
    Scenario,
    ScenarioTarget,
    SourceState,
)
from scp_cv.services.playback import (
    PlaybackError,
    close_source,
    get_all_sessions_snapshot,
    get_or_create_session,
    open_source,
    set_big_screen_mode,
)
from scp_cv.services.volume import set_system_volume

logger = logging.getLogger(__name__)

# 有效的窗口编号范围
VALID_WINDOW_IDS = frozenset({1, 2, 3, 4})


class ScenarioError(Exception):
    """预案操作过程中的业务异常。"""


# ════════════════════════════════════════════════════════════════
# 查询
# ════════════════════════════════════════════════════════════════


def list_scenarios() -> list[dict[str, object]]:
    """
    获取所有预案的摘要列表。
    :return: 预案字典列表（按排序权重和更新时间倒序）
    """
    scenarios = Scenario.objects.prefetch_related("targets__source").all()
    return [_scenario_to_dict(scenario) for scenario in scenarios]


def get_scenario(scenario_id: int) -> dict[str, object]:
    """
    获取指定预案的详细信息。
    :param scenario_id: 预案主键
    :return: 预案字典
    :raises ScenarioError: 预案不存在时
    """
    try:
        scenario = Scenario.objects.prefetch_related("targets__source").get(pk=scenario_id)
    except Scenario.DoesNotExist as not_found:
        raise ScenarioError(f"预案 id={scenario_id} 不存在") from not_found
    return _scenario_to_dict(scenario)


# ════════════════════════════════════════════════════════════════
# 创建 / 更新 / 删除 / 置顶
# ════════════════════════════════════════════════════════════════


def create_scenario(
    name: str,
    description: str = "",
    big_screen_mode_state: str = SourceState.UNSET,
    big_screen_mode: str = BigScreenMode.SINGLE,
    volume_state: str = SourceState.UNSET,
    volume_level: int = 100,
    targets: Optional[list[dict[str, object]]] = None,
) -> Scenario:
    """
    创建新预案。
    :param name: 预案名称
    :param description: 描述
    :param big_screen_mode_state: 大屏模式三态
    :param big_screen_mode: 大屏模式值
    :param volume_state: 音量三态
    :param volume_level: 音量等级
    :param targets: 窗口目标列表，每个元素包含 window_id, source_state, source_id, autoplay, resume
    :return: 创建的 Scenario 实例
    :raises ScenarioError: 参数校验失败时
    """
    if not name.strip():
        raise ScenarioError("预案名称不能为空")

    scenario = Scenario.objects.create(
        name=name.strip(),
        description=description.strip(),
        big_screen_mode_state=big_screen_mode_state,
        big_screen_mode=big_screen_mode,
        volume_state=volume_state,
        volume_level=volume_level,
    )

    _apply_targets(scenario, targets)
    logger.info("创建预案「%s」(id=%d)", scenario.name, scenario.pk)
    return scenario


def update_scenario(
    scenario_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    big_screen_mode_state: Optional[str] = None,
    big_screen_mode: Optional[str] = None,
    volume_state: Optional[str] = None,
    volume_level: Optional[int] = None,
    targets: Optional[list[dict[str, object]]] = None,
) -> Scenario:
    """
    更新已有预案。
    :param scenario_id: 预案主键
    :param name: 新名称
    :param description: 新描述
    :param big_screen_mode_state: 大屏模式三态
    :param big_screen_mode: 大屏模式值
    :param volume_state: 音量三态
    :param volume_level: 音量等级
    :param targets: 窗口目标列表
    :return: 更新后的 Scenario 实例
    :raises ScenarioError: 预案不存在或参数校验失败时
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
    if big_screen_mode_state is not None:
        scenario.big_screen_mode_state = big_screen_mode_state
    if big_screen_mode is not None:
        scenario.big_screen_mode = big_screen_mode
    if volume_state is not None:
        scenario.volume_state = volume_state
    if volume_level is not None:
        scenario.volume_level = volume_level

    scenario.save()

    if targets is not None:
        _apply_targets(scenario, targets)

    logger.info("更新预案「%s」(id=%d)", scenario.name, scenario.pk)
    return scenario


def pin_scenario(scenario_id: int) -> Scenario:
    """
    置顶预案（提升排序权重到最高）。
    :param scenario_id: 预案主键
    :return: 更新后的 Scenario 实例
    :raises ScenarioError: 预案不存在时
    """
    try:
        scenario = Scenario.objects.get(pk=scenario_id)
    except Scenario.DoesNotExist as not_found:
        raise ScenarioError(f"预案 id={scenario_id} 不存在") from not_found

    max_order = Scenario.objects.order_by("-sort_order").values_list("sort_order", flat=True).first() or 0
    scenario.sort_order = max_order + 1
    scenario.save(update_fields=["sort_order"])
    logger.info("置顶预案「%s」(sort_order=%d)", scenario.name, scenario.sort_order)
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


# ════════════════════════════════════════════════════════════════
# 捕获当前状态
# ════════════════════════════════════════════════════════════════


def capture_scenario_from_current_state(
    name: str,
    description: str = "",
    scenario_id: Optional[int] = None,
) -> Scenario:
    """
    从当前窗口 1-4 的播放会话捕获预案。
    :param name: 预案名称
    :param description: 预案描述
    :param scenario_id: 已有预案 ID；传入时覆盖该预案，否则创建新预案
    :return: 创建或更新后的 Scenario 实例
    :raises ScenarioError: 名称为空或目标预案不存在时
    """
    if not name.strip():
        raise ScenarioError("预案名称不能为空")

    runtime = RuntimeState.get_instance()
    targets: list[dict[str, object]] = []

    for window_id in sorted(VALID_WINDOW_IDS):
        session = get_or_create_session(window_id)
        if session.media_source_id is not None:
            active_states = (PlaybackState.LOADING, PlaybackState.PLAYING)
            targets.append({
                "window_id": window_id,
                "source_state": SourceState.SET,
                "source_id": session.media_source_id,
                "autoplay": session.playback_state in active_states,
                "resume": True,
            })
        else:
            targets.append({
                "window_id": window_id,
                "source_state": SourceState.EMPTY,
                "source_id": None,
                "autoplay": True,
                "resume": True,
            })

    if scenario_id is not None and scenario_id > 0:
        return update_scenario(
            scenario_id=scenario_id,
            name=name,
            description=description,
            big_screen_mode_state=SourceState.SET,
            big_screen_mode=runtime.big_screen_mode,
            volume_state=SourceState.SET,
            volume_level=runtime.volume_level,
            targets=targets,
        )

    return create_scenario(
        name=name,
        description=description,
        big_screen_mode_state=SourceState.SET,
        big_screen_mode=runtime.big_screen_mode,
        volume_state=SourceState.SET,
        volume_level=runtime.volume_level,
        targets=targets,
    )


# ════════════════════════════════════════════════════════════════
# 激活预案
# ════════════════════════════════════════════════════════════════


def activate_scenario(scenario_id: int) -> list[dict[str, object]]:
    """
    激活预案：按三态语义应用各窗口配置。
    - unset：不改变该窗口
    - empty：关闭该窗口
    - set：打开绑定的媒体源
    :param scenario_id: 预案主键
    :return: 激活后所有窗口的状态快照列表
    :raises ScenarioError: 预案不存在或激活失败时
    """
    try:
        scenario = Scenario.objects.prefetch_related("targets__source").get(pk=scenario_id)
    except Scenario.DoesNotExist as not_found:
        raise ScenarioError(f"预案 id={scenario_id} 不存在") from not_found

    logger.info("开始激活预案「%s」(id=%d)", scenario.name, scenario.pk)

    # 应用大屏模式
    if scenario.big_screen_mode_state == SourceState.SET:
        set_big_screen_mode(scenario.big_screen_mode)
        logger.info("大屏模式切换为 %s", scenario.get_big_screen_mode_display())

    # 应用音量
    if scenario.volume_state == SourceState.SET:
        set_system_volume(scenario.volume_level)
        logger.info("系统音量设置为 %d", scenario.volume_level)

    # 应用各窗口目标
    for target in scenario.targets.all():
        _apply_window_target(target)

    logger.info("预案「%s」激活完成", scenario.name)
    return get_all_sessions_snapshot()


# ════════════════════════════════════════════════════════════════
# 内部工具函数
# ════════════════════════════════════════════════════════════════


def _resolve_source(source_id: Optional[int]) -> Optional[MediaSource]:
    """根据 ID 查询媒体源，None 或 0 表示不绑定。"""
    if not source_id:
        return None
    try:
        return MediaSource.objects.get(pk=source_id)
    except MediaSource.DoesNotExist as not_found:
        raise ScenarioError(f"媒体源 id={source_id} 不存在") from not_found


def _apply_targets(scenario: Scenario, targets: Optional[list[dict[str, object]]]) -> None:
    """应用窗口目标列表到预案。"""
    if targets is None:
        return

    # 清除旧目标
    scenario.targets.all().delete()

    for target_data in targets:
        window_id = int(target_data.get("window_id", 0))
        if window_id not in VALID_WINDOW_IDS:
            continue
        source_state = str(target_data.get("source_state", SourceState.UNSET))
        source_id = target_data.get("source_id")
        ScenarioTarget.objects.create(
            scenario=scenario,
            window_id=window_id,
            source_state=source_state,
            source=_resolve_source(source_id) if source_state == SourceState.SET else None,
            autoplay=bool(target_data.get("autoplay", True)),
            resume=bool(target_data.get("resume", True)),
        )


def _apply_window_target(target: ScenarioTarget) -> None:
    """应用单个窗口目标。"""
    window_id = target.window_id

    if target.source_state == SourceState.UNSET:
        logger.debug("窗口 %d 未设置，保持原有状态", window_id)
        return

    if target.source_state == SourceState.EMPTY:
        close_source(window_id)
        logger.info("窗口 %d 已清空（黑屏）", window_id)
        return

    if target.source_state == SourceState.SET and target.source_id:
        session = get_or_create_session(window_id)
        # resume 策略：相同源且正在播放时跳过
        if target.resume and session.media_source_id == target.source_id:
            if session.playback_state in (PlaybackState.PLAYING, PlaybackState.PAUSED, PlaybackState.LOADING):
                logger.info("窗口 %d 已在播放相同源，保留进度", window_id)
                return
        try:
            open_source(window_id, target.source_id, autoplay=target.autoplay)
        except PlaybackError as e:
            raise ScenarioError(f"激活窗口 {window_id} 失败：{e}") from e


def _scenario_to_dict(scenario: Scenario) -> dict[str, object]:
    """将 Scenario 模型实例序列化为字典。"""
    targets: list[dict[str, object]] = []
    for target in scenario.targets.all():
        target_dict: dict[str, object] = {
            "window_id": target.window_id,
            "source_state": target.source_state,
            "source_id": target.source_id,
            "source_name": target.source.name if target.source else "",
            "autoplay": target.autoplay,
            "resume": target.resume,
        }
        targets.append(target_dict)

    return {
        "id": scenario.pk,
        "name": scenario.name,
        "description": scenario.description,
        "sort_order": scenario.sort_order,
        "big_screen_mode_state": scenario.big_screen_mode_state,
        "big_screen_mode": scenario.big_screen_mode,
        "big_screen_mode_label": scenario.get_big_screen_mode_display() if scenario.big_screen_mode_state == SourceState.SET else "",
        "volume_state": scenario.volume_state,
        "volume_level": scenario.volume_level,
        "targets": targets,
        "created_at": scenario.created_at.isoformat() if scenario.created_at else "",
        "updated_at": scenario.updated_at.isoformat() if scenario.updated_at else "",
    }
