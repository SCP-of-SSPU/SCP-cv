#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
播放控制台视图，负责主页面渲染与所有 HTTP 操作端点。
包含三大功能区：统一源列表管理、多窗口播放控制、系统设置。
所有播放/显示操作均通过 window_id 路径参数定位目标窗口。
@Project : SCP-cv
@File : views.py
@Author : Qintsg
@Date : 2026-04-14
'''
from __future__ import annotations

import json
import logging

from django.conf import settings
from django.http import (
    HttpRequest,
    HttpResponse,
    JsonResponse,
    StreamingHttpResponse,
)
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from scp_cv.services.display import list_display_targets
from scp_cv.services.executables import get_mediamtx_executable
from scp_cv.services.media import (
    MediaError,
    add_local_path,
    add_uploaded_file,
    add_web_url,
    delete_media_source,
    list_media_sources,
    sync_streams_to_media_sources,
)
from scp_cv.services.mediamtx import sync_stream_states
from scp_cv.apps.playback.models import PlaybackCommand
from scp_cv.services.playback import (
    VALID_WINDOW_IDS,
    PlaybackError,
    close_source,
    control_playback,
    get_all_sessions_snapshot,
    get_or_create_session,
    get_session_snapshot,
    is_splice_mode_active,
    navigate_content,
    open_source,
    set_splice_mode,
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
from scp_cv.services.sse import event_stream, publish_event

logger = logging.getLogger(__name__)


def _parse_window_id(raw_window_id: str) -> int:
    """
    解析并校验路径中的 window_id。
    :param raw_window_id: URL 路径捕获的窗口编号字符串
    :return: 合法的窗口编号（int）
    :raises PlaybackError: window_id 无效时
    """
    try:
        window_id = int(raw_window_id)
    except (ValueError, TypeError) as parse_err:
        raise PlaybackError(f"window_id 格式无效：{raw_window_id}") from parse_err
    if window_id not in VALID_WINDOW_IDS:
        raise PlaybackError(f"window_id 不在有效范围内：{window_id}")
    return window_id


# ══════════════════════════════════════════════════════════════
# 页面渲染
# ══════════════════════════════════════════════════════════════

@require_GET
def home(request: HttpRequest) -> HttpResponse:
    """
    渲染播放控制台主页面，展示所有窗口状态和源列表。
    :param request: HTTP 请求
    :return: 渲染后的控制台页面
    """
    display_targets = list_display_targets()
    all_sessions = get_all_sessions_snapshot()

    # 同步流状态并获取源列表
    sync_stream_states()
    sync_streams_to_media_sources()
    media_sources = list_media_sources()

    context = {
        # 多窗口会话快照
        "sessions": all_sessions,
        "valid_window_ids": sorted(VALID_WINDOW_IDS),
        "splice_active": is_splice_mode_active(),
        # 显示器
        "display_targets": display_targets,
        # 媒体源
        "media_sources": media_sources,
        # 预案列表
        "scenarios": list_scenarios(),
        # 外部组件
        "mediamtx_path": str(get_mediamtx_executable() or "未检测到"),
        "refresh_timestamp": timezone.localtime(timezone.now()).strftime("%Y-%m-%d %H:%M:%S"),
        "debug_mode_label": "DEBUG 模式" if settings.DEBUG else "生产模式",
    }
    return render(request, "dashboard/home.html", context)


# ══════════════════════════════════════════════════════════════
# 源管理 API（全局，不分窗口）
# ══════════════════════════════════════════════════════════════

@require_POST
def upload_source(request: HttpRequest) -> JsonResponse:
    """
    通过文件上传添加媒体源。
    :param request: HTTP 请求（multipart/form-data，包含 file 字段）
    :return: JSON 响应
    """
    uploaded_file = request.FILES.get("file")
    if not uploaded_file:
        return JsonResponse({"success": False, "error": "缺少 file 字段"}, status=400)

    display_name = request.POST.get("name", "").strip() or None
    source_type = request.POST.get("source_type", "").strip() or None

    try:
        source = add_uploaded_file(uploaded_file, display_name, source_type)
    except MediaError as upload_err:
        return JsonResponse({"success": False, "error": str(upload_err)}, status=400)

    return JsonResponse({
        "success": True,
        "source": {
            "id": source.pk,
            "name": source.name,
            "source_type": source.source_type,
            "uri": source.uri,
        },
    })


@require_POST
def add_local_source(request: HttpRequest) -> JsonResponse:
    """
    通过本地路径注册媒体源。
    :param request: HTTP 请求（JSON body 或 POST form，包含 path 字段）
    :return: JSON 响应
    """
    local_path = request.POST.get("path", "").strip()
    display_name = request.POST.get("name", "").strip() or None
    source_type = request.POST.get("source_type", "").strip() or None

    if not local_path and request.content_type == "application/json":
        try:
            body = json.loads(request.body)
            local_path = body.get("path", "").strip()
            display_name = body.get("name", "").strip() or display_name
            source_type = body.get("source_type", "").strip() or source_type
        except (json.JSONDecodeError, AttributeError):
            pass

    if not local_path:
        return JsonResponse({"success": False, "error": "缺少 path 字段"}, status=400)

    try:
        source = add_local_path(local_path, display_name, source_type)
    except MediaError as path_err:
        return JsonResponse({"success": False, "error": str(path_err)}, status=400)

    return JsonResponse({
        "success": True,
        "source": {
            "id": source.pk,
            "name": source.name,
            "source_type": source.source_type,
            "uri": source.uri,
        },
    })


@require_POST
def add_web_source(request: HttpRequest) -> JsonResponse:
    """
    通过 URL 添加网页类型媒体源。
    :param request: HTTP 请求（POST form，包含 url 字段）
    :return: JSON 响应
    """
    web_url = request.POST.get("url", "").strip()
    display_name = request.POST.get("name", "").strip() or None

    if not web_url:
        return JsonResponse({"success": False, "error": "缺少 url 字段"}, status=400)

    try:
        source = add_web_url(web_url, display_name)
    except MediaError as web_err:
        return JsonResponse({"success": False, "error": str(web_err)}, status=400)

    return JsonResponse({
        "success": True,
        "source": {
            "id": source.pk,
            "name": source.name,
            "source_type": source.source_type,
            "uri": source.uri,
        },
    })


@require_POST
def remove_source(request: HttpRequest) -> JsonResponse:
    """
    删除指定媒体源。
    :param request: HTTP 请求（POST form，包含 source_id 字段）
    :return: JSON 响应
    """
    source_id = request.POST.get("source_id")
    if not source_id:
        return JsonResponse({"success": False, "error": "缺少 source_id"}, status=400)

    try:
        source_id_int = int(source_id)
    except (ValueError, TypeError):
        return JsonResponse({"success": False, "error": "source_id 格式无效"}, status=400)

    try:
        delete_media_source(source_id_int)
    except MediaError as delete_err:
        return JsonResponse({"success": False, "error": str(delete_err)}, status=400)

    return JsonResponse({"success": True})


@require_GET
def api_sources(request: HttpRequest) -> JsonResponse:
    """
    获取所有媒体源列表（含流同步）。
    :param request: HTTP 请求
    :return: JSON 格式的媒体源列表
    """
    sync_result = sync_stream_states()
    stream_sync = sync_streams_to_media_sources()

    source_type_filter = request.GET.get("source_type", "").strip() or None
    sources = list_media_sources(source_type_filter)

    return JsonResponse({
        "success": True,
        "sources": sources,
        "sync_result": {**sync_result, **stream_sync},
    }, json_dumps_params={"default": str})


# ══════════════════════════════════════════════════════════════
# 播放控制 API（按窗口操作）
# ══════════════════════════════════════════════════════════════

@require_POST
def open_media_source(request: HttpRequest, window_id: str) -> JsonResponse:
    """
    打开指定媒体源到指定窗口。
    :param request: HTTP 请求（POST form，包含 source_id 字段）
    :param window_id: URL 路径中的窗口编号
    :return: JSON 响应
    """
    try:
        wid = _parse_window_id(window_id)
    except PlaybackError as wid_err:
        return JsonResponse({"success": False, "error": str(wid_err)}, status=400)

    source_id = request.POST.get("source_id")
    if not source_id:
        return JsonResponse({"success": False, "error": "缺少 source_id"}, status=400)

    try:
        source_id_int = int(source_id)
    except (ValueError, TypeError):
        return JsonResponse({"success": False, "error": "source_id 格式无效"}, status=400)

    autoplay = request.POST.get("autoplay", "true").lower() in ("true", "1", "yes")

    try:
        open_source(wid, source_id_int, autoplay=autoplay)
    except PlaybackError as open_err:
        return JsonResponse({"success": False, "error": str(open_err)}, status=400)

    snapshot = get_session_snapshot(wid)
    publish_event("playback_state", snapshot)
    return JsonResponse({"success": True, "session": snapshot})


@require_POST
def playback_control(request: HttpRequest, window_id: str) -> JsonResponse:
    """
    播放控制（play / pause / stop）。
    :param request: HTTP 请求（POST form，包含 action 字段）
    :param window_id: URL 路径中的窗口编号
    :return: JSON 响应
    """
    try:
        wid = _parse_window_id(window_id)
    except PlaybackError as wid_err:
        return JsonResponse({"success": False, "error": str(wid_err)}, status=400)

    action = request.POST.get("action", "").strip()
    if not action:
        return JsonResponse({"success": False, "error": "缺少 action 字段"}, status=400)

    try:
        control_playback(wid, action)
    except PlaybackError as ctrl_err:
        return JsonResponse({"success": False, "error": str(ctrl_err)}, status=400)

    snapshot = get_session_snapshot(wid)
    publish_event("playback_state", snapshot)
    return JsonResponse({"success": True, "session": snapshot})


@require_POST
def navigate(request: HttpRequest, window_id: str) -> JsonResponse:
    """
    内容导航（下一页/上一页/跳转/Seek）。
    :param request: HTTP 请求（POST form，包含 action 字段）
    :param window_id: URL 路径中的窗口编号
    :return: JSON 响应
    """
    try:
        wid = _parse_window_id(window_id)
    except PlaybackError as wid_err:
        return JsonResponse({"success": False, "error": str(wid_err)}, status=400)

    action = request.POST.get("action", "").strip()
    if not action:
        return JsonResponse({"success": False, "error": "缺少 action 字段"}, status=400)

    target_index = 0
    position_ms = 0
    try:
        target_index = int(request.POST.get("target_index", "0"))
        position_ms = int(request.POST.get("position_ms", "0"))
    except (ValueError, TypeError):
        pass

    try:
        navigate_content(wid, action, target_index=target_index, position_ms=position_ms)
    except PlaybackError as nav_err:
        return JsonResponse({"success": False, "error": str(nav_err)}, status=400)

    snapshot = get_session_snapshot(wid)
    publish_event("playback_state", snapshot)
    return JsonResponse({"success": True, "session": snapshot})


@require_POST
def close_current(request: HttpRequest, window_id: str) -> JsonResponse:
    """
    关闭指定窗口当前播放的源。
    :param request: HTTP 请求
    :param window_id: URL 路径中的窗口编号
    :return: JSON 响应
    """
    try:
        wid = _parse_window_id(window_id)
    except PlaybackError as wid_err:
        return JsonResponse({"success": False, "error": str(wid_err)}, status=400)

    try:
        close_source(wid)
    except PlaybackError as close_err:
        return JsonResponse({"success": False, "error": str(close_err)}, status=400)

    snapshot = get_session_snapshot(wid)
    publish_event("playback_state", snapshot)
    return JsonResponse({"success": True, "session": snapshot})


@require_POST
def toggle_loop(request: HttpRequest, window_id: str) -> JsonResponse:
    """
    切换指定窗口的循环播放状态。
    :param request: HTTP 请求（POST form，包含 enabled 字段）
    :param window_id: URL 路径中的窗口编号
    :return: JSON 响应
    """
    try:
        wid = _parse_window_id(window_id)
    except PlaybackError as wid_err:
        return JsonResponse({"success": False, "error": str(wid_err)}, status=400)

    enabled_raw = request.POST.get("enabled", "false").strip().lower()
    loop_enabled = enabled_raw in ("true", "1", "yes")

    try:
        toggle_loop_playback(wid, loop_enabled)
    except PlaybackError as loop_err:
        return JsonResponse({"success": False, "error": str(loop_err)}, status=400)

    snapshot = get_session_snapshot(wid)
    publish_event("playback_state", snapshot)
    return JsonResponse({"success": True, "session": snapshot})


# ══════════════════════════════════════════════════════════════
# 拼接模式 API
# ══════════════════════════════════════════════════════════════

@require_POST
def toggle_splice(request: HttpRequest) -> JsonResponse:
    """
    切换窗口 1+2 的拼接模式。
    :param request: HTTP 请求（POST form，包含 enabled 字段）
    :return: JSON 响应
    """
    enabled_raw = request.POST.get("enabled", "false").strip().lower()
    splice_enabled = enabled_raw in ("true", "1", "yes")

    try:
        set_splice_mode(splice_enabled)
    except PlaybackError as splice_err:
        return JsonResponse({"success": False, "error": str(splice_err)}, status=400)

    all_snapshots = get_all_sessions_snapshot()
    publish_event("playback_state", {"sessions": all_snapshots})
    return JsonResponse({
        "success": True,
        "splice_active": splice_enabled,
        "sessions": all_snapshots,
    })


# ══════════════════════════════════════════════════════════════
# 窗口 ID 叠加显示
# ══════════════════════════════════════════════════════════════

@require_POST
def show_window_ids(request: HttpRequest) -> JsonResponse:
    """
    触发所有输出窗口显示 5 秒窗口 ID 叠加标识。
    向每个窗口的 PlaybackSession 写入 SHOW_ID 指令，
    播放器轮询消费后会在窗口上渲染半透明 ID 文字。
    :param request: HTTP 请求（POST）
    :return: JSON 响应
    """
    for wid in VALID_WINDOW_IDS:
        session = get_or_create_session(wid)
        session.pending_command = PlaybackCommand.SHOW_ID
        session.save(update_fields=["pending_command"])
    return JsonResponse({"success": True})


# ══════════════════════════════════════════════════════════════
# 状态查询 & SSE
# ══════════════════════════════════════════════════════════════

@require_GET
def api_session_state(request: HttpRequest) -> JsonResponse:
    """
    获取所有窗口播放会话状态。
    可选 ?window_id=N 获取单个窗口状态。
    :param request: HTTP 请求
    :return: JSON 格式的会话快照
    """
    single_window = request.GET.get("window_id", "").strip()
    if single_window:
        try:
            wid = _parse_window_id(single_window)
        except PlaybackError as wid_err:
            return JsonResponse({"success": False, "error": str(wid_err)}, status=400)
        snapshot = get_session_snapshot(wid)
        return JsonResponse({"success": True, "session": snapshot})

    all_snapshots = get_all_sessions_snapshot()
    return JsonResponse({
        "success": True,
        "sessions": all_snapshots,
        "splice_active": is_splice_mode_active(),
    })


@require_GET
def sse_events(request: HttpRequest) -> StreamingHttpResponse:
    """
    SSE 事件流端点，客户端通过 EventSource 连接。
    :param request: HTTP 请求
    :return: 持续推送的 SSE 响应流
    """
    last_id = request.GET.get("last_id", "0")
    try:
        last_sequence = int(last_id)
    except (ValueError, TypeError):
        last_sequence = 0

    response = StreamingHttpResponse(
        event_stream(last_sequence),
        content_type="text/event-stream",
    )
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response


# ════════════════════════════════════════════════════════════════
# 预案管理 API
# ════════════════════════════════════════════════════════════════

@require_GET
def api_scenarios(request: HttpRequest) -> JsonResponse:
    """
    获取所有预案列表。
    :param request: HTTP 请求
    :return: JSON 格式的预案列表
    """
    return JsonResponse({
        "success": True,
        "scenarios": list_scenarios(),
    }, json_dumps_params={"default": str})


def _parse_scenario_body(request: HttpRequest) -> dict[str, object]:
    """
    从 POST 请求中解析预案配置参数（支持 JSON body 和 form-data）。
    :param request: HTTP 请求
    :return: 解析后的参数字典
    """
    # 优先尝试 JSON body
    if request.content_type and "json" in request.content_type:
        try:
            return json.loads(request.body)
        except (json.JSONDecodeError, AttributeError):
            pass

    # 回退到 form-data
    return dict(request.POST)


def _extract_int(raw_value: object, default: int = 0) -> int:
    """
    安全提取整数值。
    :param raw_value: 原始值（字符串、数字或 None）
    :param default: 解析失败时的默认值
    :return: 整数结果
    """
    if raw_value is None:
        return default
    try:
        return int(raw_value)
    except (ValueError, TypeError):
        return default


def _extract_bool(raw_value: object, default: bool = True) -> bool:
    """
    安全提取布尔值。
    :param raw_value: 原始值（字符串、布尔或 None）
    :param default: 解析失败时的默认值
    :return: 布尔结果
    """
    if raw_value is None:
        return default
    if isinstance(raw_value, bool):
        return raw_value
    return str(raw_value).strip().lower() in ("true", "1", "yes")


@require_POST
def create_scenario_view(request: HttpRequest) -> JsonResponse:
    """
    创建新预案。
    接受 JSON body 或 form-data，参数包含名称、描述、拼接模式及窗口 1/2 配置。
    :param request: HTTP 请求
    :return: JSON 响应（含创建后的预案详情）
    """
    body = _parse_scenario_body(request)
    name = str(body.get("name", "")).strip()
    if not name:
        return JsonResponse({"success": False, "error": "缺少 name 字段"}, status=400)

    try:
        scenario = create_scenario(
            name=name,
            description=str(body.get("description", "")),
            is_splice_mode=_extract_bool(body.get("is_splice_mode"), default=False),
            window1_source_id=_extract_int(body.get("window1_source_id")) or None,
            window1_autoplay=_extract_bool(body.get("window1_autoplay"), default=True),
            window1_resume=_extract_bool(body.get("window1_resume"), default=True),
            window2_source_id=_extract_int(body.get("window2_source_id")) or None,
            window2_autoplay=_extract_bool(body.get("window2_autoplay"), default=True),
            window2_resume=_extract_bool(body.get("window2_resume"), default=True),
        )
    except ScenarioError as create_err:
        return JsonResponse({"success": False, "error": str(create_err)}, status=400)

    from scp_cv.services.scenario import _scenario_to_dict
    return JsonResponse({"success": True, "scenario": _scenario_to_dict(scenario)})


@require_POST
def update_scenario_view(request: HttpRequest, scenario_id: str) -> JsonResponse:
    """
    更新已有预案。
    :param request: HTTP 请求（JSON body 或 form-data）
    :param scenario_id: URL 路径中的预案 ID
    :return: JSON 响应
    """
    try:
        sid = int(scenario_id)
    except (ValueError, TypeError):
        return JsonResponse({"success": False, "error": "预案 ID 格式无效"}, status=400)

    body = _parse_scenario_body(request)

    # 判断窗口源是否显式传入（区分“未传入”与“显式置空”）
    window1_source_provided = "window1_source_id" in body
    window2_source_provided = "window2_source_id" in body

    try:
        scenario = update_scenario(
            scenario_id=sid,
            name=body.get("name") if "name" in body else None,
            description=body.get("description") if "description" in body else None,
            is_splice_mode=_extract_bool(body.get("is_splice_mode"), default=False) if "is_splice_mode" in body else None,
            window1_source_id=_extract_int(body.get("window1_source_id")) or None,
            window1_autoplay=_extract_bool(body.get("window1_autoplay")) if "window1_autoplay" in body else None,
            window1_resume=_extract_bool(body.get("window1_resume")) if "window1_resume" in body else None,
            window2_source_id=_extract_int(body.get("window2_source_id")) or None,
            window2_autoplay=_extract_bool(body.get("window2_autoplay")) if "window2_autoplay" in body else None,
            window2_resume=_extract_bool(body.get("window2_resume")) if "window2_resume" in body else None,
            _window1_source_provided=window1_source_provided,
            _window2_source_provided=window2_source_provided,
        )
    except ScenarioError as update_err:
        return JsonResponse({"success": False, "error": str(update_err)}, status=400)

    from scp_cv.services.scenario import _scenario_to_dict
    return JsonResponse({"success": True, "scenario": _scenario_to_dict(scenario)})


@require_POST
def delete_scenario_view(request: HttpRequest, scenario_id: str) -> JsonResponse:
    """
    删除指定预案。
    :param request: HTTP 请求
    :param scenario_id: URL 路径中的预案 ID
    :return: JSON 响应
    """
    try:
        sid = int(scenario_id)
    except (ValueError, TypeError):
        return JsonResponse({"success": False, "error": "预案 ID 格式无效"}, status=400)

    try:
        delete_scenario(sid)
    except ScenarioError as del_err:
        return JsonResponse({"success": False, "error": str(del_err)}, status=400)

    return JsonResponse({"success": True})


@require_POST
def activate_scenario_view(request: HttpRequest, scenario_id: str) -> JsonResponse:
    """
    激活预案：一键应用预设的窗口配置。
    :param request: HTTP 请求
    :param scenario_id: URL 路径中的预案 ID
    :return: JSON 响应（含激活后的窗口快照）
    """
    try:
        sid = int(scenario_id)
    except (ValueError, TypeError):
        return JsonResponse({"success": False, "error": "预案 ID 格式无效"}, status=400)

    try:
        session_snapshots = activate_scenario(sid)
    except ScenarioError as act_err:
        return JsonResponse({"success": False, "error": str(act_err)}, status=400)

    # 发布 SSE 事件通知前端状态变更
    publish_event("playback_state", {"sessions": session_snapshots})
    return JsonResponse({
        "success": True,
        "sessions": session_snapshots,
        "splice_active": is_splice_mode_active(),
    })
