#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
gRPC PlaybackControlService 实现，将 proto 定义的 RPC
委托给 Django 服务层执行，并返回 protobuf 响应。
每个 RPC 方法从请求中提取 window_id（proto3 int32 默认为 0），
若未提供则回退到窗口 1，确保与旧版客户端的向后兼容。
@Project : SCP-cv
@File : grpc_servicers.py
@Author : Qintsg
@Date : 2026-04-14
'''
from __future__ import annotations

import logging
import time

import grpc
from django.conf import settings

from scp_cv.grpc_generated.scp_cv.v1 import control_pb2
from scp_cv.grpc_generated.scp_cv.v1 import control_pb2_grpc
from scp_cv.services.display import (
    build_left_right_splice_target,
    list_display_targets,
)
from scp_cv.services.media import (
    MediaError,
    add_local_path,
    add_web_url,
    delete_media_source,
    list_media_sources,
)
from scp_cv.services.playback import (
    PlaybackError,
    close_source,
    control_playback,
    get_all_sessions_snapshot,
    get_session_snapshot,
    is_splice_mode_active,
    navigate_content,
    open_source,
    select_display_target,
    set_splice_mode,
    stop_current_content,
    toggle_loop_playback,
)
from scp_cv.services.scenario import (
    ScenarioError,
    activate_scenario,
    create_scenario,
    delete_scenario,
    list_scenarios,
    update_scenario,
)

logger = logging.getLogger(__name__)

# 当 proto 请求中未携带 window_id（int32 默认值 0）时，回退到窗口 1
_DEFAULT_WINDOW_ID: int = 1

# ── Proto Action → PlaybackCommand 映射 ──
_PLAYBACK_ACTION_MAP: dict[int, str] = {
    control_pb2.ACTION_PLAY: "play",
    control_pb2.ACTION_PAUSE: "pause",
    control_pb2.ACTION_STOP: "stop",
}

_NAVIGATE_ACTION_MAP: dict[int, str] = {
    control_pb2.NAV_NEXT: "next",
    control_pb2.NAV_PREV: "prev",
    control_pb2.NAV_GOTO: "goto",
    control_pb2.NAV_SEEK: "seek",
}


def _extract_window_id(request: object) -> int:
    """
    从 proto 请求中提取 window_id，未设置时回退到默认窗口。
    proto3 的 int32 默认值为 0，此处将 0 视为"未指定"并回退。
    :param request: protobuf 请求对象
    :return: 有效的窗口编号（1-4）
    """
    raw_window_id = getattr(request, "window_id", 0)
    return raw_window_id if raw_window_id > 0 else _DEFAULT_WINDOW_ID


def _success_reply(message: str = "操作成功", detail: str = "") -> control_pb2.OperationReply:
    """
    构建成功的 OperationReply。
    :param message: 简要描述
    :param detail: 补充信息
    :return: OperationReply protobuf 实例
    """
    return control_pb2.OperationReply(success=True, message=message, detail=detail)


def _error_reply(message: str, detail: str = "") -> control_pb2.OperationReply:
    """
    构建失败的 OperationReply。
    :param message: 错误描述
    :param detail: 补充信息
    :return: OperationReply protobuf 实例
    """
    return control_pb2.OperationReply(success=False, message=message, detail=detail)


def _snapshot_to_proto(snapshot: dict[str, object]) -> control_pb2.SessionSnapshot:
    """
    将服务层返回的会话快照字典转换为 proto SessionSnapshot 消息。
    :param snapshot: get_session_snapshot() 返回的字典
    :return: proto SessionSnapshot 实例
    """
    return control_pb2.SessionSnapshot(
        window_id=int(snapshot["window_id"]),
        session_id=int(snapshot["session_id"]),
        source_name=str(snapshot["source_name"]),
        source_type=str(snapshot["source_type"]),
        source_type_label=str(snapshot["source_type_label"]),
        source_uri=str(snapshot["source_uri"]),
        playback_state=str(snapshot["playback_state"]),
        playback_state_label=str(snapshot["playback_state_label"]),
        display_mode=str(snapshot["display_mode"]),
        display_mode_label=str(snapshot["display_mode_label"]),
        target_display_label=str(snapshot["target_display_label"]),
        spliced_display_label=str(snapshot["spliced_display_label"]),
        is_spliced=bool(snapshot["is_spliced"]),
        current_slide=int(snapshot["current_slide"]),
        total_slides=int(snapshot["total_slides"]),
        position_ms=int(snapshot["position_ms"]),
        duration_ms=int(snapshot["duration_ms"]),
        pending_command=str(snapshot["pending_command"]),
        last_updated_at=str(snapshot["last_updated_at"]),
        loop_enabled=bool(snapshot["loop_enabled"]),
    )


def _source_to_proto(source_dict: dict[str, object]) -> control_pb2.SourceItem:
    """
    将服务层返回的媒体源字典转换为 proto SourceItem 消息。
    :param source_dict: list_media_sources() 返回的字典元素
    :return: proto SourceItem 实例
    """
    return control_pb2.SourceItem(
        id=int(source_dict["id"]),
        source_type=str(source_dict["source_type"]),
        name=str(source_dict["name"]),
        uri=str(source_dict["uri"]),
        is_available=bool(source_dict["is_available"]),
        stream_identifier=str(source_dict.get("stream_identifier", "") or ""),
        created_at=str(source_dict.get("created_at", "")),
    )


def _scenario_dict_to_proto(scenario_dict: dict[str, object]) -> control_pb2.ScenarioItem:
    """
    将服务层返回的预案字典转换为 proto ScenarioItem 消息。
    :param scenario_dict: list_scenarios() / _scenario_to_dict() 返回的字典
    :return: proto ScenarioItem 实例
    """
    return control_pb2.ScenarioItem(
        id=int(scenario_dict["id"]),
        name=str(scenario_dict["name"]),
        description=str(scenario_dict.get("description", "")),
        is_splice_mode=bool(scenario_dict["is_splice_mode"]),
        window1=control_pb2.ScenarioWindowSlot(
            source_id=int(scenario_dict.get("window1_source_id") or 0),
            autoplay=bool(scenario_dict.get("window1_autoplay", True)),
            resume=bool(scenario_dict.get("window1_resume", True)),
        ),
        window2=control_pb2.ScenarioWindowSlot(
            source_id=int(scenario_dict.get("window2_source_id") or 0),
            autoplay=bool(scenario_dict.get("window2_autoplay", True)),
            resume=bool(scenario_dict.get("window2_resume", True)),
        ),
        created_at=str(scenario_dict.get("created_at", "")),
        updated_at=str(scenario_dict.get("updated_at", "")),
    )


class PlaybackControlServicer(control_pb2_grpc.PlaybackControlServiceServicer):
    """PlaybackControlService 的具体实现，委托 Django 服务层处理业务逻辑。"""

    # ------------------------------------------------------------------
    # 源管理
    # ------------------------------------------------------------------
    def OpenSource(
        self,
        request: control_pb2.OpenSourceRequest,
        context: grpc.ServicerContext,
    ) -> control_pb2.OperationReply:
        """
        打开指定媒体源到指定窗口的播放区域。
        :param request: OpenSourceRequest（window_id, media_source_id, autoplay）
        :param context: gRPC 服务上下文
        :return: OperationReply
        """
        window_id = _extract_window_id(request)
        media_source_id = request.media_source_id
        if media_source_id <= 0:
            return _error_reply("media_source_id 必须大于 0")

        try:
            session = open_source(
                window_id=window_id,
                media_source_id=int(media_source_id),
                autoplay=request.autoplay,
            )
            source_name = session.media_source.name if session.media_source else "未知"
            return _success_reply(
                message=f"窗口 {window_id} 源已打开",
                detail=source_name,
            )
        except PlaybackError as playback_err:
            return _error_reply(str(playback_err))

    def CloseSource(
        self,
        request: control_pb2.CloseSourceRequest,
        context: grpc.ServicerContext,
    ) -> control_pb2.OperationReply:
        """
        关闭指定窗口当前播放的源。
        :param request: CloseSourceRequest（window_id）
        :param context: gRPC 服务上下文
        :return: OperationReply
        """
        window_id = _extract_window_id(request)
        try:
            close_source(window_id)
            return _success_reply(message=f"窗口 {window_id} 源已关闭")
        except PlaybackError as playback_err:
            return _error_reply(str(playback_err))

    # ------------------------------------------------------------------
    # 播放控制
    # ------------------------------------------------------------------
    def ControlPlayback(
        self,
        request: control_pb2.ControlPlaybackRequest,
        context: grpc.ServicerContext,
    ) -> control_pb2.OperationReply:
        """
        发送播放控制命令（play / pause / stop）到指定窗口。
        :param request: ControlPlaybackRequest（window_id, action）
        :param context: gRPC 服务上下文
        :return: OperationReply
        """
        window_id = _extract_window_id(request)
        action = _PLAYBACK_ACTION_MAP.get(request.action)
        if action is None:
            return _error_reply("无效的播放控制动作")

        try:
            control_playback(window_id, action)
            return _success_reply(message=f"窗口 {window_id} 已发送 {action} 指令")
        except PlaybackError as playback_err:
            return _error_reply(str(playback_err))

    # ------------------------------------------------------------------
    # 内容导航
    # ------------------------------------------------------------------
    def NavigateContent(
        self,
        request: control_pb2.NavigateContentRequest,
        context: grpc.ServicerContext,
    ) -> control_pb2.OperationReply:
        """
        发送内容导航指令（翻页 / 跳转位置）到指定窗口。
        :param request: NavigateContentRequest（window_id, action, target_index, position_ms）
        :param context: gRPC 服务上下文
        :return: OperationReply
        """
        window_id = _extract_window_id(request)
        action = _NAVIGATE_ACTION_MAP.get(request.action)
        if action is None:
            return _error_reply("无效的导航动作")

        try:
            navigate_content(
                window_id=window_id,
                action=action,
                target_index=request.target_index,
                position_ms=request.position_ms,
            )
            return _success_reply(message=f"窗口 {window_id} 已发送 {action} 指令")
        except PlaybackError as playback_err:
            return _error_reply(str(playback_err))

    # ------------------------------------------------------------------
    # 状态查询
    # ------------------------------------------------------------------
    def GetRuntimeStatus(
        self,
        request: control_pb2.WindowRequest,
        context: grpc.ServicerContext,
    ) -> control_pb2.RuntimeStatusReply:
        """
        返回指定窗口播放会话的运行时状态摘要。
        :param request: WindowRequest（window_id）
        :param context: gRPC 服务上下文
        :return: RuntimeStatusReply
        """
        window_id = _extract_window_id(request)
        snapshot = get_session_snapshot(window_id)
        grpc_port: int = getattr(settings, "GRPC_PORT", 50051)
        is_debug: bool = getattr(settings, "DEBUG", False)

        return control_pb2.RuntimeStatusReply(
            source_type=str(snapshot["source_type"]),
            source_name=str(snapshot["source_name"]),
            playback_state=str(snapshot["playback_state"]),
            display_mode=str(snapshot["display_mode"]),
            grpc_endpoint=f"0.0.0.0:{grpc_port}",
            debug_mode=is_debug,
        )

    def GetPlaybackState(
        self,
        request: control_pb2.WindowRequest,
        context: grpc.ServicerContext,
    ) -> control_pb2.PlaybackStateReply:
        """
        返回指定窗口的详细播放状态（含 PPT 页码和视频进度）。
        :param request: WindowRequest（window_id）
        :param context: gRPC 服务上下文
        :return: PlaybackStateReply
        """
        window_id = _extract_window_id(request)
        snapshot = get_session_snapshot(window_id)
        return control_pb2.PlaybackStateReply(
            playback_state=str(snapshot["playback_state"]),
            source_type=str(snapshot["source_type"]),
            source_name=str(snapshot["source_name"]),
            source_uri=str(snapshot["source_uri"]),
            current_slide=int(snapshot["current_slide"]),
            total_slides=int(snapshot["total_slides"]),
            position_ms=int(snapshot["position_ms"]),
            duration_ms=int(snapshot["duration_ms"]),
            display_mode=str(snapshot["display_mode"]),
            target_display=str(snapshot["target_display_label"]),
            is_spliced=bool(snapshot["is_spliced"]),
            loop_enabled=bool(snapshot["loop_enabled"]),
        )

    # ------------------------------------------------------------------
    # 显示器管理
    # ------------------------------------------------------------------
    def ListDisplayTargets(
        self,
        request: control_pb2.EmptyRequest,
        context: grpc.ServicerContext,
    ) -> control_pb2.DisplayTargetsReply:
        """
        列出当前主机可用的显示器和拼接标签。
        :param request: EmptyRequest
        :param context: gRPC 服务上下文
        :return: DisplayTargetsReply
        """
        display_targets = list_display_targets()
        target_items = [
            control_pb2.DisplayTargetItem(
                index=dt.index,
                name=dt.name,
                width=dt.width,
                height=dt.height,
                x=dt.x,
                y=dt.y,
                is_primary=dt.is_primary,
            )
            for dt in display_targets
        ]

        splice_label = ""
        splice_target = build_left_right_splice_target(display_targets)
        if splice_target is not None:
            splice_label = f"{splice_target.left.name} + {splice_target.right.name}"

        return control_pb2.DisplayTargetsReply(
            targets=target_items,
            splice_label=splice_label,
        )

    def SelectDisplayTarget(
        self,
        request: control_pb2.SelectDisplayTargetRequest,
        context: grpc.ServicerContext,
    ) -> control_pb2.OperationReply:
        """
        切换指定窗口的显示目标（单屏或左右拼接模式）。
        :param request: SelectDisplayTargetRequest（window_id, display_mode, target_label）
        :param context: gRPC 服务上下文
        :return: OperationReply
        """
        window_id = _extract_window_id(request)
        display_mode = request.display_mode.strip()
        target_label = request.target_label.strip()

        if not display_mode:
            return _error_reply("display_mode 不能为空")

        try:
            session = select_display_target(
                window_id=window_id,
                display_mode=display_mode,
                target_display_name=target_label,
            )
            return _success_reply(
                message=f"窗口 {window_id} 显示目标已切换",
                detail=f"{session.get_display_mode_display()} — {session.target_display_label}",
            )
        except PlaybackError as playback_err:
            return _error_reply(str(playback_err))

    # ------------------------------------------------------------------
    # 兼容旧接口
    # ------------------------------------------------------------------
    def StopCurrentContent(
        self,
        request: control_pb2.EmptyRequest,
        context: grpc.ServicerContext,
    ) -> control_pb2.OperationReply:
        """
        停止窗口 1 当前播放的内容（兼容旧接口，内部调用 close_source）。
        :param request: EmptyRequest
        :param context: gRPC 服务上下文
        :return: OperationReply
        """
        try:
            stop_current_content(_DEFAULT_WINDOW_ID)
            return _success_reply(message="播放已停止")
        except PlaybackError as playback_err:
            return _error_reply(str(playback_err))

    # ------------------------------------------------------------------
    # 媒体源管理
    # ------------------------------------------------------------------
    def ListSources(
        self,
        request: control_pb2.ListSourcesRequest,
        context: grpc.ServicerContext,
    ) -> control_pb2.ListSourcesReply:
        """
        列出所有可用媒体源。可按 source_type 过滤。
        :param request: ListSourcesRequest（source_type）
        :param context: gRPC 服务上下文
        :return: ListSourcesReply
        """
        filter_type = request.source_type.strip() if request.source_type else None
        source_dicts = list_media_sources(source_type=filter_type)
        source_items = [_source_to_proto(s) for s in source_dicts]
        return control_pb2.ListSourcesReply(success=True, sources=source_items)

    def AddLocalPathSource(
        self,
        request: control_pb2.AddLocalPathSourceRequest,
        context: grpc.ServicerContext,
    ) -> control_pb2.SourceReply:
        """
        通过本地文件路径注册媒体源。
        :param request: AddLocalPathSourceRequest（path, name, source_type）
        :param context: gRPC 服务上下文
        :return: SourceReply
        """
        local_path = request.path.strip()
        if not local_path:
            return control_pb2.SourceReply(success=False, message="path 不能为空")

        display_name = request.name.strip() or None
        source_type = request.source_type.strip() or None

        try:
            media_source = add_local_path(
                local_path, display_name=display_name, source_type=source_type,
            )
            source_item = control_pb2.SourceItem(
                id=media_source.pk,
                source_type=media_source.source_type,
                name=media_source.name,
                uri=media_source.uri,
                is_available=media_source.is_available,
                stream_identifier=media_source.stream_identifier or "",
                created_at=(
                    media_source.created_at.isoformat()
                    if media_source.created_at else ""
                ),
            )
            return control_pb2.SourceReply(
                success=True, message="添加成功", source=source_item,
            )
        except MediaError as media_err:
            return control_pb2.SourceReply(success=False, message=str(media_err))

    def AddWebUrlSource(
        self,
        request: control_pb2.AddWebUrlSourceRequest,
        context: grpc.ServicerContext,
    ) -> control_pb2.SourceReply:
        """
        通过 URL 添加网页类型媒体源。
        :param request: AddWebUrlSourceRequest（url, name）
        :param context: gRPC 服务上下文
        :return: SourceReply
        """
        web_url = request.url.strip()
        if not web_url:
            return control_pb2.SourceReply(success=False, message="url 不能为空")

        display_name = request.name.strip() or None

        try:
            media_source = add_web_url(web_url, display_name=display_name)
            source_item = control_pb2.SourceItem(
                id=media_source.pk,
                source_type=media_source.source_type,
                name=media_source.name,
                uri=media_source.uri,
                is_available=media_source.is_available,
                stream_identifier=media_source.stream_identifier or "",
                created_at=(
                    media_source.created_at.isoformat()
                    if media_source.created_at else ""
                ),
            )
            return control_pb2.SourceReply(
                success=True, message="添加成功", source=source_item,
            )
        except MediaError as media_err:
            return control_pb2.SourceReply(success=False, message=str(media_err))

    def DeleteSource(
        self,
        request: control_pb2.DeleteSourceRequest,
        context: grpc.ServicerContext,
    ) -> control_pb2.OperationReply:
        """
        删除指定媒体源。
        :param request: DeleteSourceRequest（media_source_id）
        :param context: gRPC 服务上下文
        :return: OperationReply
        """
        if request.media_source_id <= 0:
            return _error_reply("media_source_id 必须大于 0")

        try:
            delete_media_source(int(request.media_source_id))
            return _success_reply(message="媒体源已删除")
        except MediaError as media_err:
            return _error_reply(str(media_err))

    # ------------------------------------------------------------------
    # 播放模式控制
    # ------------------------------------------------------------------
    def ToggleLoop(
        self,
        request: control_pb2.ToggleLoopRequest,
        context: grpc.ServicerContext,
    ) -> control_pb2.OperationReply:
        """
        切换指定窗口的循环播放模式。
        :param request: ToggleLoopRequest（window_id, enabled）
        :param context: gRPC 服务上下文
        :return: OperationReply
        """
        window_id = _extract_window_id(request)
        try:
            toggle_loop_playback(window_id, request.enabled)
            state_label = "开启" if request.enabled else "关闭"
            return _success_reply(
                message=f"窗口 {window_id} 循环播放已{state_label}",
            )
        except PlaybackError as playback_err:
            return _error_reply(str(playback_err))

    def SetSpliceMode(
        self,
        request: control_pb2.SetSpliceModeRequest,
        context: grpc.ServicerContext,
    ) -> control_pb2.SpliceModeReply:
        """
        设置窗口 1+2 的左右拼接模式。
        :param request: SetSpliceModeRequest（enabled）
        :param context: gRPC 服务上下文
        :return: SpliceModeReply
        """
        try:
            set_splice_mode(request.enabled)
            all_snapshots = get_all_sessions_snapshot()
            session_protos = [_snapshot_to_proto(s) for s in all_snapshots]
            return control_pb2.SpliceModeReply(
                success=True,
                splice_active=request.enabled,
                sessions=session_protos,
            )
        except PlaybackError as playback_err:
            logger.warning("设置拼接模式失败：%s", playback_err)
            # 拼接模式失败时仍返回当前状态
            return control_pb2.SpliceModeReply(
                success=False,
                splice_active=is_splice_mode_active(),
                sessions=[],
            )

    # ------------------------------------------------------------------
    # 窗口与会话查询
    # ------------------------------------------------------------------
    def ShowWindowIds(
        self,
        request: control_pb2.EmptyRequest,
        context: grpc.ServicerContext,
    ) -> control_pb2.OperationReply:
        """
        触发所有窗口显示 5 秒窗口 ID 叠加标识。
        向每个窗口写入 SHOW_ID 指令。
        :param request: EmptyRequest
        :param context: gRPC 服务上下文
        :return: OperationReply
        """
        from scp_cv.apps.playback.models import PlaybackCommand as PBCmd
        from scp_cv.services.playback import get_or_create_session, VALID_WINDOW_IDS

        for wid in VALID_WINDOW_IDS:
            session = get_or_create_session(wid)
            session.pending_command = PBCmd.SHOW_ID
            session.command_args = {}
            session.save(update_fields=["pending_command", "command_args"])
        return _success_reply(message="窗口 ID 显示指令已下发")

    def GetAllSessionSnapshots(
        self,
        request: control_pb2.EmptyRequest,
        context: grpc.ServicerContext,
    ) -> control_pb2.AllSessionSnapshotsReply:
        """
        获取所有窗口的播放会话快照列表。
        :param request: EmptyRequest
        :param context: gRPC 服务上下文
        :return: AllSessionSnapshotsReply
        """
        all_snapshots = get_all_sessions_snapshot()
        session_protos = [_snapshot_to_proto(s) for s in all_snapshots]
        return control_pb2.AllSessionSnapshotsReply(
            success=True,
            splice_active=is_splice_mode_active(),
            sessions=session_protos,
        )

    # ------------------------------------------------------------------
    # 预案管理
    # ------------------------------------------------------------------
    def ListScenarios(
        self,
        request: control_pb2.EmptyRequest,
        context: grpc.ServicerContext,
    ) -> control_pb2.ListScenariosReply:
        """
        获取所有预案列表。
        :param request: EmptyRequest
        :param context: gRPC 服务上下文
        :return: ListScenariosReply
        """
        scenario_dicts = list_scenarios()
        items = [_scenario_dict_to_proto(s) for s in scenario_dicts]
        return control_pb2.ListScenariosReply(success=True, scenarios=items)

    def CreateScenario(
        self,
        request: control_pb2.ScenarioDetail,
        context: grpc.ServicerContext,
    ) -> control_pb2.ScenarioReply:
        """
        创建新预案。
        :param request: ScenarioDetail（名称、描述、拼接模式、窗口配置）
        :param context: gRPC 服务上下文
        :return: ScenarioReply
        """
        if not request.name.strip():
            return control_pb2.ScenarioReply(
                success=False, message="预案名称不能为空",
            )

        # 提取窗口 1/2 配置
        w1 = request.window1
        w2 = request.window2

        try:
            scenario = create_scenario(
                name=request.name.strip(),
                description=request.description.strip(),
                is_splice_mode=request.is_splice_mode,
                window1_source_id=int(w1.source_id) if w1 and w1.source_id else None,
                window1_autoplay=w1.autoplay if w1 else True,
                window1_resume=w1.resume if w1 else True,
                window2_source_id=int(w2.source_id) if w2 and w2.source_id else None,
                window2_autoplay=w2.autoplay if w2 else True,
                window2_resume=w2.resume if w2 else True,
            )
        except ScenarioError as create_err:
            return control_pb2.ScenarioReply(
                success=False, message=str(create_err),
            )

        from scp_cv.services.scenario import _scenario_to_dict
        item = _scenario_dict_to_proto(_scenario_to_dict(scenario))
        return control_pb2.ScenarioReply(
            success=True, message="预案创建成功", scenario=item,
        )

    def UpdateScenario(
        self,
        request: control_pb2.UpdateScenarioRequest,
        context: grpc.ServicerContext,
    ) -> control_pb2.ScenarioReply:
        """
        更新已有预案配置。
        :param request: UpdateScenarioRequest（scenario_id, detail）
        :param context: gRPC 服务上下文
        :return: ScenarioReply
        """
        if request.scenario_id <= 0:
            return control_pb2.ScenarioReply(
                success=False, message="scenario_id 必须大于 0",
            )

        detail = request.detail
        w1 = detail.window1 if detail else None
        w2 = detail.window2 if detail else None

        try:
            scenario = update_scenario(
                scenario_id=int(request.scenario_id),
                name=detail.name.strip() if detail and detail.name else None,
                description=detail.description if detail else None,
                is_splice_mode=detail.is_splice_mode if detail else None,
                window1_source_id=int(w1.source_id) if w1 and w1.source_id else None,
                window1_autoplay=w1.autoplay if w1 else None,
                window1_resume=w1.resume if w1 else None,
                window2_source_id=int(w2.source_id) if w2 and w2.source_id else None,
                window2_autoplay=w2.autoplay if w2 else None,
                window2_resume=w2.resume if w2 else None,
                _window1_source_provided=w1 is not None,
                _window2_source_provided=w2 is not None,
            )
        except ScenarioError as update_err:
            return control_pb2.ScenarioReply(
                success=False, message=str(update_err),
            )

        from scp_cv.services.scenario import _scenario_to_dict
        item = _scenario_dict_to_proto(_scenario_to_dict(scenario))
        return control_pb2.ScenarioReply(
            success=True, message="预案更新成功", scenario=item,
        )

    def DeleteScenario(
        self,
        request: control_pb2.DeleteScenarioRequest,
        context: grpc.ServicerContext,
    ) -> control_pb2.OperationReply:
        """
        删除指定预案。
        :param request: DeleteScenarioRequest（scenario_id）
        :param context: gRPC 服务上下文
        :return: OperationReply
        """
        if request.scenario_id <= 0:
            return _error_reply("scenario_id 必须大于 0")

        try:
            delete_scenario(int(request.scenario_id))
            return _success_reply(message="预案已删除")
        except ScenarioError as del_err:
            return _error_reply(str(del_err))

    def ActivateScenario(
        self,
        request: control_pb2.ActivateScenarioRequest,
        context: grpc.ServicerContext,
    ) -> control_pb2.ActivateScenarioReply:
        """
        激活预案：一键应用预设的窗口配置。
        :param request: ActivateScenarioRequest（scenario_id）
        :param context: gRPC 服务上下文
        :return: ActivateScenarioReply（含激活后的窗口快照）
        """
        if request.scenario_id <= 0:
            return control_pb2.ActivateScenarioReply(
                success=False, message="scenario_id 必须大于 0",
            )

        try:
            session_snapshots = activate_scenario(int(request.scenario_id))
            session_protos = [_snapshot_to_proto(s) for s in session_snapshots]
            return control_pb2.ActivateScenarioReply(
                success=True,
                message="预案激活成功",
                sessions=session_protos,
            )
        except ScenarioError as act_err:
            return control_pb2.ActivateScenarioReply(
                success=False, message=str(act_err),
            )

    # ------------------------------------------------------------------
    # 服务端流式推送
    # ------------------------------------------------------------------
    def WatchPlaybackState(
        self,
        request: control_pb2.EmptyRequest,
        context: grpc.ServicerContext,
    ) -> None:
        """
        服务端流式推送播放状态变更，替代 SSE。
        客户端发起此调用后持续接收状态变化事件，直到断开连接。
        使用 SSE 事件总线的 _event_condition 监听新事件，避免轮询。
        :param request: EmptyRequest
        :param context: gRPC 服务上下文（客户端取消时 is_active() 返回 False）
        """
        from scp_cv.services.sse import (
            _event_condition,
            _latest_event_data,
        )

        current_sequence: int = 0

        # 先推送当前完整状态作为初始帧
        initial_snapshots = get_all_sessions_snapshot()
        initial_event = control_pb2.PlaybackStateEvent(
            event_type="initial_state",
            sequence=0,
            sessions=[_snapshot_to_proto(s) for s in initial_snapshots],
            timestamp=time.time(),
        )
        yield initial_event

        # 持续监听新事件
        while context.is_active():
            with _event_condition:
                # 等待新事件（30 秒超时发心跳）
                _event_condition.wait(timeout=30.0)

                pending_events: list[tuple[str, int]] = []
                for event_type, event_record in _latest_event_data.items():
                    record_sequence = int(event_record.get("sequence", 0))
                    if record_sequence > current_sequence:
                        pending_events.append((str(event_type), record_sequence))

            # DB 查询和 yield 都放在条件锁外，保证发布线程不被慢客户端阻塞。
            for event_type, record_sequence in pending_events:
                current_sequence = max(current_sequence, record_sequence)
                all_snapshots = get_all_sessions_snapshot()
                state_event = control_pb2.PlaybackStateEvent(
                    event_type=event_type,
                    sequence=record_sequence,
                    sessions=[
                        _snapshot_to_proto(s) for s in all_snapshots
                    ],
                    timestamp=time.time(),
                )
                yield state_event
