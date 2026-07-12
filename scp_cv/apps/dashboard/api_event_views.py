#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
控制台 SSE 事件视图。
@Project : SCP-cv
@File : api_event_views.py
@Author : Qintsg
@Date : 2026-07-12
'''
from __future__ import annotations

from django.http import HttpRequest, StreamingHttpResponse
from django.views.decorators.http import require_GET

from scp_cv.services.sse import event_stream


@require_GET
def events_api(request: HttpRequest) -> StreamingHttpResponse:
    """
    播放状态 SSE 事件流。
    :param request: HTTP 请求
    :return: SSE 响应
    """
    try:
        last_sequence = int(request.GET.get("last_id", "0"))
    except (TypeError, ValueError):
        last_sequence = 0
    response = StreamingHttpResponse(event_stream(last_sequence), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response
