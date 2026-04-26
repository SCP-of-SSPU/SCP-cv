/**
 * SCP-cv gRPC 流式订阅模块（替代 SSE）
 * 职责：通过 WatchPlaybackState 服务端流接收实时状态更新，
 *       自动重连并带指数退避。
 */

import { watchPlaybackState } from "./grpc-client.bundle.js";
import { handlePlaybackStateEvent } from "./windows.js";

/* ═══════════════════════════════════════════════════════════
 * 连接状态 UI
 * ═══════════════════════════════════════════════════════════ */

/** 连接状态显示元素 */
const streamStatusElement = document.getElementById("stream-status");

/**
 * 更新连接状态显示
 * @param {string} label - 状态文本
 * @param {string} stateClass - 附加 CSS 类
 */
function setStreamStatus(label, stateClass) {
  if (!streamStatusElement) return;
  streamStatusElement.textContent = label;
  streamStatusElement.className = "toolbar__status";
  if (stateClass) {
    streamStatusElement.classList.add(stateClass);
  }
}

/* ═══════════════════════════════════════════════════════════
 * 指数退避重连
 * ═══════════════════════════════════════════════════════════ */

/** 退避状态 */
const BACKOFF_INITIAL_MS = 1000;
const BACKOFF_MAX_MS = 30000;
const BACKOFF_FACTOR = 2;

let currentBackoffMs = BACKOFF_INITIAL_MS;
let reconnectTimer = null;
let cancelCurrentStream = null;
let hasReceivedEvent = false;

/**
 * 安排延迟重连
 */
function scheduleReconnect() {
  if (reconnectTimer) return;
  setStreamStatus(`gRPC: ${(currentBackoffMs / 1000).toFixed(0)}s 后重连…`, "toolbar__status--error");
  reconnectTimer = setTimeout(() => {
    reconnectTimer = null;
    currentBackoffMs = Math.min(currentBackoffMs * BACKOFF_FACTOR, BACKOFF_MAX_MS);
    connectStream();
  }, currentBackoffMs);
}

/* ═══════════════════════════════════════════════════════════
 * 流式连接
 * ═══════════════════════════════════════════════════════════ */

/**
 * 建立 gRPC 流式订阅，接收播放状态变更事件
 */
export function connectStream() {
  /* 关闭上一个流（如有） */
  if (cancelCurrentStream) {
    cancelCurrentStream();
    cancelCurrentStream = null;
  }

  hasReceivedEvent = false;
  setStreamStatus("gRPC: 连接中…", "");

  cancelCurrentStream = watchPlaybackState(
    /* onEvent — 每次收到服务端推送 */
    (eventResponse) => {
      /* 首次收到事件时标记为已连接并重置退避 */
      if (!hasReceivedEvent) {
        hasReceivedEvent = true;
        currentBackoffMs = BACKOFF_INITIAL_MS;
        setStreamStatus("gRPC: 已连接", "toolbar__status--connected");
      }

      try {
        const eventPayload = eventResponse.toObject();
        handlePlaybackStateEvent(eventPayload);
      } catch (parseError) {
        /* 忽略格式异常的事件 */
      }
    },

    /* onError — 流异常时重连 */
    (_streamError) => {
      setStreamStatus("gRPC: 已断开", "toolbar__status--error");
      cancelCurrentStream = null;
      scheduleReconnect();
    },

    /* onEnd — 流正常结束时重连（服务端可能重启） */
    () => {
      setStreamStatus("gRPC: 已断开", "toolbar__status--error");
      cancelCurrentStream = null;
      scheduleReconnect();
    },
  );
}
