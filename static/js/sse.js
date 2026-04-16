/**
 * SCP-cv SSE 实时事件流模块
 * 职责：建立 EventSource 连接、分发状态更新事件、自动重连
 */

import { handlePlaybackStateEvent } from "./windows.js";

/** SSE 连接状态显示元素 */
const sseStatusElement = document.getElementById("sse-status");

/**
 * 更新 SSE 连接状态显示
 * @param {string} label - 状态文本
 * @param {string} stateClass - 附加 CSS 类
 */
function setSseStatus(label, stateClass) {
  if (!sseStatusElement) return;
  sseStatusElement.textContent = label;
  sseStatusElement.className = "toolbar__status";
  if (stateClass) {
    sseStatusElement.classList.add(stateClass);
  }
}

/**
 * 建立 SSE 连接，处理事件和自动重连
 */
export function connectSSE() {
  setSseStatus("SSE: 连接中…", "");
  const eventSource = new EventSource("/events/");

  eventSource.onopen = () => {
    setSseStatus("SSE: 已连接", "toolbar__status--connected");
  };

  /* 播放状态变更 → 委托给 windows 模块处理 */
  eventSource.addEventListener("playback_state", (sseEvent) => {
    try {
      const statePayload = JSON.parse(sseEvent.data);
      handlePlaybackStateEvent(statePayload);
    } catch (parseError) {
      /* 忽略格式异常的事件 */
    }
  });

  /* 心跳事件（无操作，仅保持连接） */
  eventSource.addEventListener("heartbeat", () => {
    /* 连接保活，无需处理 */
  });

  eventSource.onerror = () => {
    setSseStatus("SSE: 已断开", "toolbar__status--error");
    eventSource.close();
    /* 5 秒后自动重连 */
    setTimeout(connectSSE, 5000);
  };
}
