#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PowerPoint Broker 的 AF_PIPE JSON 客户端与服务端协议。
@Project : SCP-cv
@File : transport.py
@Author : Qintsg
@Date : 2026-07-11
'''
from __future__ import annotations

import json
import logging
import queue
import threading
import time
import uuid
from dataclasses import asdict
from multiprocessing.connection import Client, Listener
from typing import Any

from scp_cv.player.ppt_broker.contracts import (
    BrokerHealth,
    PptBroker,
    PptCommand,
    PptCommandRequest,
    PptExportResult,
    PptOpenRequest,
    PptPreheatRequest,
    PptSessionKey,
    PptShowExportRequest,
    PptShowFormat,
    PptSlideExportRequest,
    PptState,
)

_PROTOCOL_VERSION = 1
_MAX_MESSAGE_BYTES = 1024 * 1024
_CONNECTION_JOIN_TIMEOUT_SECONDS = 1.0

logger = logging.getLogger(__name__)


class PptBrokerRemoteError(RuntimeError):
    """Broker 远端调用失败。"""

    def __init__(self, remote_type: str, message: str) -> None:
        super().__init__(f"{remote_type}: {message}")
        self.remote_type = remote_type
        self.remote_message = message


class PptBrokerClient:
    """每次调用建立短连接的 AF_PIPE PowerPoint Broker Adapter。"""

    def __init__(
        self,
        address: str | None = None,
        authkey: bytes | None = None,
        *,
        timeout_seconds: float = 120.0,
    ) -> None:
        if address is None or authkey is None:
            from scp_cv.player.ppt_broker.runtime import (
                default_pipe_address,
                load_or_create_authkey,
            )

            address = address or default_pipe_address()
            authkey = authkey or load_or_create_authkey()
        self.address = address
        self._authkey = authkey
        self.timeout_seconds = max(0.1, timeout_seconds)
        self.started_process: object | None = None

    def open(self, request: PptOpenRequest) -> PptState:
        result = self._request("open", _open_request_to_dict(request))
        return _state_from_dict(_require_dict(result))

    def command(self, request: PptCommandRequest) -> PptState:
        result = self._request("command", _command_request_to_dict(request))
        return _state_from_dict(_require_dict(result))

    def get_state(self, session: PptSessionKey) -> PptState:
        result = self._request("get_state", {"session": asdict(session)})
        return _state_from_dict(_require_dict(result))

    def close(self, session: PptSessionKey) -> None:
        self._request("close", {"session": asdict(session)})

    def preheat(self, request: PptPreheatRequest) -> None:
        self._request("preheat", asdict(request))

    def export_show(self, request: PptShowExportRequest) -> PptExportResult:
        payload = asdict(request)
        payload["target_format"] = request.target_format.value
        result = self._request("export_show", payload)
        return _export_result_from_dict(_require_dict(result))

    def export_slides(self, request: PptSlideExportRequest) -> PptExportResult:
        result = self._request("export_slides", asdict(request))
        return _export_result_from_dict(_require_dict(result))

    def health(self) -> BrokerHealth:
        result = self._request("health", {})
        health = _require_dict(result)
        return BrokerHealth(
            ready=bool(health.get("ready", False)),
            generation=str(health.get("generation", "")),
            pid=int(health.get("pid", 0)),
        )

    def shutdown(self) -> None:
        self._request("shutdown", {})

    def _request(self, method: str, params: dict[str, object]) -> object:
        envelope = {
            "version": _PROTOCOL_VERSION,
            "request_id": uuid.uuid4().hex,
            "method": method,
            "params": params,
        }
        payload = _encode_json(envelope)
        outcome: queue.Queue[tuple[bool, object]] = queue.Queue(maxsize=1)

        def exchange() -> None:
            connection = None
            try:
                connection = Client(
                    self.address,
                    family="AF_PIPE",
                    authkey=self._authkey,
                )
                connection.send_bytes(payload)
                response_payload = connection.recv_bytes(_MAX_MESSAGE_BYTES)
                outcome.put((True, _decode_json(response_payload)))
            except BaseException as exchange_error:
                outcome.put((False, exchange_error))
            finally:
                if connection is not None:
                    connection.close()

        exchange_thread = threading.Thread(
            target=exchange,
            name=f"ppt-broker-client-{method}",
            daemon=True,
        )
        exchange_thread.start()
        try:
            succeeded, value = outcome.get(timeout=self.timeout_seconds)
        except queue.Empty as timeout_error:
            raise TimeoutError(
                f"PowerPoint Broker 调用超时：method={method}, "
                f"timeout={self.timeout_seconds:.1f}s"
            ) from timeout_error
        if not succeeded:
            if isinstance(value, BaseException):
                raise value
            raise RuntimeError(f"PowerPoint Broker 传输失败：{value}")
        response = _require_dict(value)
        if response.get("request_id") != envelope["request_id"]:
            raise RuntimeError("PowerPoint Broker 响应 request_id 不匹配")
        if not bool(response.get("ok", False)):
            error = _require_dict(response.get("error"))
            raise PptBrokerRemoteError(
                str(error.get("type", "RemoteError")),
                str(error.get("message", "未知 Broker 错误")),
            )
        return response.get("result")


class PptBrokerServer:
    """一次只接收普通 JSON 数据、业务操作交给 STA 引擎的 AF_PIPE Server。"""

    def __init__(self, broker: PptBroker, address: str, authkey: bytes) -> None:
        self._broker = broker
        self.address = address
        self._authkey = authkey
        self._stop_event = threading.Event()
        self._listener: object | None = None
        self._listener_lock = threading.Lock()
        self._connection_threads: set[threading.Thread] = set()
        self._connection_threads_lock = threading.Lock()

    def serve_forever(self) -> None:
        """监听命名管道，直至客户端请求 shutdown。"""
        listener = Listener(
            self.address,
            family="AF_PIPE",
            authkey=self._authkey,
        )
        with self._listener_lock:
            self._listener = listener
        try:
            while not self._stop_event.is_set():
                try:
                    connection = listener.accept()
                except Exception:
                    if self._stop_event.is_set():
                        break
                    continue
                if self._stop_event.is_set():
                    connection.close()
                    break
                connection_thread = threading.Thread(
                    target=self._serve_connection,
                    args=(connection,),
                    name="ppt-broker-connection",
                    daemon=True,
                )
                with self._connection_threads_lock:
                    self._connection_threads.add(connection_thread)
                connection_thread.start()
        finally:
            self._stop_event.set()
            with self._listener_lock:
                self._listener = None
            listener.close()
            self._join_connection_threads()
            self._broker.shutdown()

    def _serve_connection(self, connection: object) -> None:
        """在独立线程处理一个短连接，业务 COM 仍由 Broker STA 串行。"""
        try:
            request_payload = connection.recv_bytes(_MAX_MESSAGE_BYTES)  # type: ignore[attr-defined]
            response_payload = self._handle_request(request_payload)
            connection.send_bytes(response_payload)  # type: ignore[attr-defined]
        except Exception as transport_error:
            try:
                connection.send_bytes(  # type: ignore[attr-defined]
                    _encode_json(
                        {
                            "version": _PROTOCOL_VERSION,
                            "request_id": "",
                            "ok": False,
                            "error": {
                                "type": type(transport_error).__name__,
                                "message": str(transport_error),
                            },
                        }
                    )
                )
            except Exception:
                pass
        finally:
            connection.close()  # type: ignore[attr-defined]
            current_thread = threading.current_thread()
            with self._connection_threads_lock:
                self._connection_threads.discard(current_thread)

    def _request_stop(self) -> None:
        """停止继续 accept；已接受的请求仍完成响应。"""
        self._stop_event.set()
        threading.Thread(
            target=self._wake_listener,
            name="ppt-broker-stop-wakeup",
            daemon=True,
        ).start()

    def _wake_listener(self) -> None:
        """用一次已认证空连接唤醒 Windows 上不可中断的 accept。"""
        connection = None
        try:
            connection = Client(
                self.address,
                family="AF_PIPE",
                authkey=self._authkey,
            )
        except Exception:
            return
        finally:
            if connection is not None:
                connection.close()

    def _join_connection_threads(self) -> None:
        """等待所有已接受请求完成，避免关闭 STA 时仍有调用方。"""
        deadline = time.monotonic() + _CONNECTION_JOIN_TIMEOUT_SECONDS
        while True:
            with self._connection_threads_lock:
                active_threads = list(self._connection_threads)
            if not active_threads:
                return
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                logger.warning(
                    "PowerPoint Broker 连接线程未在 %.1f 秒内结束，"
                    "将停止等待：active_threads=%d",
                    _CONNECTION_JOIN_TIMEOUT_SECONDS,
                    len(active_threads),
                )
                return
            for connection_thread in active_threads:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                connection_thread.join(min(0.1, remaining))

    def _handle_request(self, payload: bytes) -> bytes:
        request_id = ""
        try:
            request = _require_dict(_decode_json(payload))
            request_id = str(request.get("request_id", ""))
            if int(request.get("version", 0)) != _PROTOCOL_VERSION:
                raise ValueError("不支持的 PowerPoint Broker 协议版本")
            method = str(request.get("method", ""))
            params = _require_dict(request.get("params"))
            result = self._dispatch(method, params)
            response = {
                "version": _PROTOCOL_VERSION,
                "request_id": request_id,
                "ok": True,
                "result": result,
            }
        except Exception as request_error:
            response = {
                "version": _PROTOCOL_VERSION,
                "request_id": request_id,
                "ok": False,
                "error": {
                    "type": type(request_error).__name__,
                    "message": str(request_error),
                },
            }
        return _encode_json(response)

    def _dispatch(self, method: str, params: dict[str, object]) -> object:
        if method == "open":
            return asdict(self._broker.open(_open_request_from_dict(params)))
        if method == "command":
            return asdict(self._broker.command(_command_request_from_dict(params)))
        if method == "get_state":
            return asdict(
                self._broker.get_state(
                    _session_from_dict(_require_dict(params.get("session")))
                )
            )
        if method == "close":
            self._broker.close(
                _session_from_dict(_require_dict(params.get("session")))
            )
            return None
        if method == "preheat":
            self._broker.preheat(
                PptPreheatRequest(
                    uri=str(params.get("uri", "")),
                    source_id=int(params.get("source_id", 0)),
                    request_id=str(params.get("request_id", "")),
                )
            )
            return None
        if method == "export_show":
            return asdict(
                self._broker.export_show(
                    PptShowExportRequest(
                        source_uri=str(params.get("source_uri", "")),
                        target_uri=str(params.get("target_uri", "")),
                        target_format=PptShowFormat(
                            str(params.get("target_format", ""))
                        ),
                        request_id=str(params.get("request_id", "")),
                    )
                )
            )
        if method == "export_slides":
            return asdict(
                self._broker.export_slides(
                    PptSlideExportRequest(
                        source_uri=str(params.get("source_uri", "")),
                        output_dir=str(params.get("output_dir", "")),
                        image_format=str(params.get("image_format", "PNG")),
                        request_id=str(params.get("request_id", "")),
                    )
                )
            )
        if method == "health":
            return asdict(self._broker.health())
        if method == "shutdown":
            self._broker.shutdown()
            self._request_stop()
            return None
        raise ValueError(f"未知 PowerPoint Broker 方法：{method}")


def _open_request_to_dict(request: PptOpenRequest) -> dict[str, object]:
    return asdict(request)


def _command_request_to_dict(request: PptCommandRequest) -> dict[str, object]:
    payload = asdict(request)
    payload["command"] = request.command.value
    return payload


def _open_request_from_dict(payload: dict[str, object]) -> PptOpenRequest:
    return PptOpenRequest(
        session=_session_from_dict(_require_dict(payload.get("session"))),
        uri=str(payload.get("uri", "")),
        parent_hwnd=int(payload.get("parent_hwnd", 0)),
        autoplay=bool(payload.get("autoplay", True)),
        start_slide=int(payload.get("start_slide", 1)),
        source_id=int(payload.get("source_id", 0)),
        request_id=str(payload.get("request_id", "")),
    )


def _command_request_from_dict(payload: dict[str, object]) -> PptCommandRequest:
    return PptCommandRequest(
        session=_session_from_dict(_require_dict(payload.get("session"))),
        command=PptCommand(str(payload.get("command", ""))),
        slide_index=int(payload.get("slide_index", 0)),
        media_id=str(payload.get("media_id", "")),
        media_action=str(payload.get("media_action", "")),
        media_index=int(payload.get("media_index", 0)),
        request_id=str(payload.get("request_id", "")),
    )


def _session_from_dict(payload: dict[str, object]) -> PptSessionKey:
    return PptSessionKey(
        window_id=int(payload.get("window_id", 0)),
        owner_token=str(payload.get("owner_token", "")),
    )


def _state_from_dict(payload: dict[str, object]) -> PptState:
    return PptState(
        playback_state=str(payload.get("playback_state", "idle")),
        current_slide=int(payload.get("current_slide", 0)),
        total_slides=int(payload.get("total_slides", 0)),
        error_message=str(payload.get("error_message", "")),
        powerpoint_pid=int(payload.get("powerpoint_pid", 0)),
        slideshow_hwnd=int(payload.get("slideshow_hwnd", 0)),
        parent_hwnd=int(payload.get("parent_hwnd", 0)),
        generation=str(payload.get("generation", "")),
    )


def _export_result_from_dict(payload: dict[str, object]) -> PptExportResult:
    raw_paths = payload.get("paths", [])
    if not isinstance(raw_paths, list) or not all(
        isinstance(path, str) for path in raw_paths
    ):
        raise TypeError("PowerPoint Broker 导出结果 paths 必须是字符串数组")
    return PptExportResult(
        tuple(raw_paths),
        powerpoint_pid=int(payload.get("powerpoint_pid", 0)),
    )


def _require_dict(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError("PowerPoint Broker 协议字段必须是 JSON object")
    return value


def _encode_json(value: object) -> bytes:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    if len(payload) > _MAX_MESSAGE_BYTES:
        raise ValueError("PowerPoint Broker JSON 消息超过 1 MiB 限制")
    return payload


def _decode_json(payload: bytes) -> object:
    if len(payload) > _MAX_MESSAGE_BYTES:
        raise ValueError("PowerPoint Broker JSON 消息超过 1 MiB 限制")
    return json.loads(payload.decode("utf-8"))


__all__ = [
    "PptBrokerClient",
    "PptBrokerRemoteError",
    "PptBrokerServer",
]
