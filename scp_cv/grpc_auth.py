#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
gRPC 鉴权拦截器与 metadata 解析助手。
通过请求 metadata 中的 sessionid（或 cookie 头）解出 Django session，
未登录的请求一律返回 UNAUTHENTICATED 状态码，与 REST 链路保持一致。
@Project : SCP-cv
@File : grpc_auth.py
@Author : Qintsg
@Date : 2026-05-21
'''
from __future__ import annotations

from typing import Awaitable, Callable, Iterable

import grpc
from grpc.aio import ServerInterceptor, ServicerContext

from django.contrib.auth import get_user_model
from django.contrib.sessions.backends.db import SessionStore


_SESSION_COOKIE = "sessionid"


def _extract_session_key(metadata: Iterable[tuple[str, str]]) -> str | None:
    """
    从 gRPC metadata 中提取 Django session id。
    优先使用直接传递的 `sessionid` metadata；其次解析 `cookie` 头中的同名键。
    :param metadata: gRPC metadata 列表
    :return: session key 字符串或 None
    """
    cookie_value: str | None = None
    for key, value in metadata or ():
        lowered = key.lower()
        if lowered == _SESSION_COOKIE and value:
            return value
        if lowered == "cookie" and value:
            cookie_value = value
    if not cookie_value:
        return None
    for chunk in cookie_value.split(";"):
        if "=" not in chunk:
            continue
        name, _, val = chunk.strip().partition("=")
        if name == _SESSION_COOKIE and val:
            return val
    return None


def resolve_user_from_metadata(metadata: Iterable[tuple[str, str]]):
    """
    根据 metadata 中的 session 信息解析出已认证用户。
    :param metadata: gRPC metadata 列表
    :return: User 实例；未登录返回 None
    """
    session_key = _extract_session_key(metadata)
    if not session_key:
        return None
    store = SessionStore(session_key=session_key)
    try:
        user_id = store.get("_auth_user_id")
    except Exception:
        return None
    if not user_id:
        return None
    try:
        return get_user_model().objects.get(pk=int(user_id), is_active=True)
    except (ValueError, TypeError):
        return None
    except get_user_model().DoesNotExist:
        return None


class GrpcAuthInterceptor(ServerInterceptor):
    """
    异步 gRPC 服务端拦截器：所有 RPC 调用必须携带有效的 Django session。
    未登录请求统一以 UNAUTHENTICATED 状态码 abort，外部自动化脚本可据此做凭据刷新。
    """

    async def intercept_service(
        self,
        continuation: Callable[[grpc.HandlerCallDetails], Awaitable[grpc.RpcMethodHandler]],
        handler_call_details: grpc.HandlerCallDetails,
    ) -> grpc.RpcMethodHandler:
        """
        拦截每个 RPC 服务的方法分发，包一层鉴权检查。
        :param continuation: socio-grpc 提供的下一节点
        :param handler_call_details: 当前 RPC 调用信息
        :return: 包装后的 RpcMethodHandler
        """
        handler = await continuation(handler_call_details)
        if handler is None:
            return handler

        if handler.unary_unary:
            return grpc.unary_unary_rpc_method_handler(
                self._wrap_unary(handler.unary_unary),
                request_deserializer=handler.request_deserializer,
                response_serializer=handler.response_serializer,
            )
        if handler.unary_stream:
            return grpc.unary_stream_rpc_method_handler(
                self._wrap_unary_stream(handler.unary_stream),
                request_deserializer=handler.request_deserializer,
                response_serializer=handler.response_serializer,
            )
        if handler.stream_unary:
            return grpc.stream_unary_rpc_method_handler(
                self._wrap_stream_unary(handler.stream_unary),
                request_deserializer=handler.request_deserializer,
                response_serializer=handler.response_serializer,
            )
        if handler.stream_stream:
            return grpc.stream_stream_rpc_method_handler(
                self._wrap_stream_stream(handler.stream_stream),
                request_deserializer=handler.request_deserializer,
                response_serializer=handler.response_serializer,
            )
        return handler

    @staticmethod
    async def _ensure_authenticated(context: ServicerContext) -> None:
        """
        校验请求 metadata 是否对应已登录用户。
        :param context: gRPC ServicerContext
        :return: None；未通过校验时直接 abort
        """
        user = resolve_user_from_metadata(context.invocation_metadata())
        if user is None:
            await context.abort(grpc.StatusCode.UNAUTHENTICATED, "未登录或会话已过期")
        # 把已解析的 user 挂到 context 上，供 servicer 内部业务取用。
        setattr(context, "grpc_user", user)

    def _wrap_unary(self, inner):
        async def handler(request, context):
            await self._ensure_authenticated(context)
            return await inner(request, context)
        return handler

    def _wrap_unary_stream(self, inner):
        async def handler(request, context):
            await self._ensure_authenticated(context)
            async for item in inner(request, context):
                yield item
        return handler

    def _wrap_stream_unary(self, inner):
        async def handler(request_iterator, context):
            await self._ensure_authenticated(context)
            return await inner(request_iterator, context)
        return handler

    def _wrap_stream_stream(self, inner):
        async def handler(request_iterator, context):
            await self._ensure_authenticated(context)
            async for item in inner(request_iterator, context):
                yield item
        return handler
