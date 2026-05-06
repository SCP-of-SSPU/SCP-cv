#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
gRPC 预案管理 mixin：CRUD、激活、从当前状态捕获。
@Project : SCP-cv
@File : scenario.py
@Author : Qintsg
@Date : 2026-04-29
'''
from __future__ import annotations

import grpc

from scp_cv.grpc_generated.scp_cv.v1 import control_pb2
from scp_cv.services.scenario import (
    ScenarioError,
    activate_scenario,
    capture_scenario_from_current_state,
    create_scenario,
    delete_scenario,
    list_scenarios,
    update_scenario,
)

from .helpers import (
    _error_reply,
    _publish_playback_state_event,
    _scenario_dict_to_proto,
    _snapshot_to_proto,
    _success_reply,
)


class ScenarioMixin:
    """预案 CRUD 与激活相关的 gRPC 方法。"""

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
        :param request: ScenarioDetail（名称、描述、窗口配置）
        :param context: gRPC 服务上下文
        :return: ScenarioReply
        """
        if not request.name.strip():
            return control_pb2.ScenarioReply(
                success=False, message="预案名称不能为空",
            )

        w1 = request.window1
        w2 = request.window2
        targets = [
            {
                "window_id": 1,
                "source_state": "set" if w1 and w1.source_id else "empty",
                "source_id": int(w1.source_id) if w1 and w1.source_id else None,
                "autoplay": w1.autoplay if w1 else True,
                "resume": w1.resume if w1 else True,
            },
            {
                "window_id": 2,
                "source_state": "set" if w2 and w2.source_id else "empty",
                "source_id": int(w2.source_id) if w2 and w2.source_id else None,
                "autoplay": w2.autoplay if w2 else True,
                "resume": w2.resume if w2 else True,
            },
        ]

        try:
            scenario = create_scenario(
                name=request.name.strip(),
                description=request.description.strip(),
                targets=targets,
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
        targets = None
        if detail is not None:
            targets = [
                {
                    "window_id": 1,
                    "source_state": "set" if w1 and w1.source_id else "empty",
                    "source_id": int(w1.source_id) if w1 and w1.source_id else None,
                    "autoplay": w1.autoplay if w1 else True,
                    "resume": w1.resume if w1 else True,
                },
                {
                    "window_id": 2,
                    "source_state": "set" if w2 and w2.source_id else "empty",
                    "source_id": int(w2.source_id) if w2 and w2.source_id else None,
                    "autoplay": w2.autoplay if w2 else True,
                    "resume": w2.resume if w2 else True,
                },
            ]

        try:
            scenario = update_scenario(
                scenario_id=int(request.scenario_id),
                name=detail.name.strip() if detail and detail.name else None,
                description=detail.description if detail else None,
                targets=targets,
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
            _publish_playback_state_event()
            return control_pb2.ActivateScenarioReply(
                success=True,
                message="预案激活成功",
                sessions=session_protos,
            )
        except ScenarioError as act_err:
            return control_pb2.ActivateScenarioReply(
                success=False, message=str(act_err),
            )

    def CaptureScenario(
        self,
        request: control_pb2.CaptureScenarioRequest,
        context: grpc.ServicerContext,
    ) -> control_pb2.ScenarioReply:
        """
        从当前窗口状态捕获预案，支持创建或覆盖已有预案。
        :param request: CaptureScenarioRequest（name, description, scenario_id）
        :param context: gRPC 服务上下文
        :return: ScenarioReply
        """
        if not request.name.strip():
            return control_pb2.ScenarioReply(
                success=False, message="预案名称不能为空",
            )

        target_scenario_id = (
            int(request.scenario_id) if request.scenario_id > 0 else None
        )

        try:
            scenario = capture_scenario_from_current_state(
                name=request.name.strip(),
                description=request.description.strip(),
                scenario_id=target_scenario_id,
            )
        except ScenarioError as capture_err:
            return control_pb2.ScenarioReply(
                success=False, message=str(capture_err),
            )

        from scp_cv.services.scenario import _scenario_to_dict
        item = _scenario_dict_to_proto(_scenario_to_dict(scenario))
        operation_label = "覆盖" if target_scenario_id is not None else "创建"
        return control_pb2.ScenarioReply(
            success=True, message=f"预案已从当前状态{operation_label}", scenario=item,
        )
