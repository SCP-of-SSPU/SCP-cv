/**
 * SCP-cv 多窗口状态管理模块
 * 职责：窗口切换、拼接模式、状态缓存、DOM 状态同步、SSE 事件分发
 */

import { postAction, showBanner, withLoading, formatDuration } from "./utils.js";

/* ═══════════════════════════════════════════════════════════
 * 多窗口共享状态
 * ═══════════════════════════════════════════════════════════ */

/** 当前活跃的控制目标窗口编号（1-4） */
let activeWindowId = 1;

/** 各窗口的会话快照缓存 {windowId: sessionData} */
const windowSessions = {};

/** 拼接模式是否启用 */
let spliceActive = false;

/**
 * 获取当前活跃窗口编号
 * @returns {number} 窗口编号（1-4）
 */
export function getActiveWindowId() {
  return activeWindowId;
}

/* ═══════════════════════════════════════════════════════════
 * 窗口切换
 * ═══════════════════════════════════════════════════════════ */

/**
 * 切换当前控制的目标窗口
 * @param {number} windowId - 窗口编号（1-4）
 * @param {HTMLElement} btnElement - 点击的按钮（未使用，保留兼容签名）
 */
export function selectWindow(windowId, btnElement) {
  activeWindowId = windowId;

  /* 更新窗口选择器按钮状态 */
  document.querySelectorAll(".window-selector__btn[data-window-id]").forEach((btn) => {
    const isActive = parseInt(btn.dataset.windowId, 10) === windowId;
    btn.classList.toggle("window-selector__btn--active", isActive);
    btn.setAttribute("aria-selected", String(isActive));
  });

  /* 更新各处窗口号显示 */
  const heroWinId = document.getElementById("hero-window-id");
  const ctrlWinId = document.getElementById("ctrl-window-id");
  const toolbarWin = document.getElementById("toolbar-active-window");
  if (heroWinId) heroWinId.textContent = String(windowId);
  if (ctrlWinId) ctrlWinId.textContent = String(windowId);
  if (toolbarWin) toolbarWin.textContent = "窗口 " + windowId;

  /* 从缓存恢复该窗口的会话状态 */
  const cached = windowSessions[windowId];
  if (cached) {
    applySessionToDOM(cached);
  } else {
    resetSessionDOM();
  }
}

/* ═══════════════════════════════════════════════════════════
 * 拼接模式
 * ═══════════════════════════════════════════════════════════ */

/**
 * 切换窗口 1+2 拼接模式
 * @param {Event} triggerEvent - 触发事件
 */
export async function toggleSplice(triggerEvent) {
  const newEnabled = !spliceActive;
  await withLoading(triggerEvent, async () => {
    const result = await postAction("/playback/splice/", {
      enabled: newEnabled ? "true" : "false",
    });
    if (result.success) {
      spliceActive = result.splice_active;
      showBanner(spliceActive ? "拼接模式已开启（窗口 1+2）" : "拼接模式已关闭");
      updateSpliceUI();
      if (result.sessions) {
        result.sessions.forEach((sessionItem) => {
          applyWindowSession(sessionItem.window_id, sessionItem);
        });
      }
    } else {
      showBanner(result.error || "拼接切换失败", true);
    }
  });
}

/** 更新拼接按钮的 UI 状态（播放控制区 + 设置区两处） */
function updateSpliceUI() {
  const spliceBtn = document.getElementById("splice-toggle-btn");
  const settingsSpliceBtn = document.getElementById("settings-splice-btn");
  [spliceBtn, settingsSpliceBtn].forEach((btn) => {
    if (!btn) return;
    btn.setAttribute("aria-pressed", String(spliceActive));
    btn.classList.toggle("window-selector__btn--active-splice", spliceActive);
    btn.classList.toggle("action-button--active", spliceActive);
  });
}

/* ═══════════════════════════════════════════════════════════
 * 窗口 ID 叠加显示
 * ═══════════════════════════════════════════════════════════ */

/**
 * 触发所有窗口显示 5 秒窗口 ID 叠加
 * @param {Event} triggerEvent - 触发事件
 */
export async function showWindowIds(triggerEvent) {
  await withLoading(triggerEvent, async () => {
    const result = await postAction("/playback/show-ids/");
    if (result.success) {
      showBanner("已触发窗口 ID 显示（5 秒）");
    } else {
      showBanner(result.error || "操作失败", true);
    }
  });
}

/* ═══════════════════════════════════════════════════════════
 * 会话状态分发与 DOM 同步
 * ═══════════════════════════════════════════════════════════ */

/**
 * 将会话数据写入缓存，并同步到选择器标签和主面板
 * @param {number} windowId - 窗口编号
 * @param {object} sessionData - 来自 get_session_snapshot 的字典
 */
export function applyWindowSession(windowId, sessionData) {
  windowSessions[windowId] = sessionData;

  /* 更新窗口选择器上的状态标签 */
  const stateEl = document.getElementById("win-state-" + windowId);
  const settingsStateEl = document.getElementById("settings-win-state-" + windowId);
  const settingsSourceEl = document.getElementById("settings-win-source-" + windowId);
  const stateLabel = sessionData.playback_state_label || "空闲";
  const sourceName = sessionData.source_name || "未打开媒体源";
  if (stateEl) stateEl.textContent = stateLabel;
  if (settingsStateEl) settingsStateEl.textContent = stateLabel;
  if (settingsSourceEl) settingsSourceEl.textContent = sourceName;

  /* 如果是当前活跃窗口，同步到主面板 */
  if (windowId === activeWindowId) {
    applySessionToDOM(sessionData);
  }
}

/**
 * 将会话快照应用到主面板 DOM 元素
 * @param {object} sessionData - 会话快照数据
 */
function applySessionToDOM(sessionData) {
  /* Hero 面板 */
  const heroSourceName = document.getElementById("hero-source-name");
  const heroSourceType = document.getElementById("hero-source-type");
  const heroPlaybackState = document.getElementById("hero-playback-state");
  const heroDisplayMode = document.getElementById("hero-display-mode");
  if (heroSourceName) heroSourceName.textContent = sessionData.source_name || "无";
  if (heroSourceType) heroSourceType.textContent = sessionData.source_type_label || "无";
  if (heroPlaybackState) heroPlaybackState.textContent = sessionData.playback_state_label || "—";
  if (heroDisplayMode) heroDisplayMode.textContent = sessionData.display_mode_label || "—";

  /* PPT 翻页状态 */
  const slideCurrent = document.getElementById("slide-current");
  const slideTotal = document.getElementById("slide-total");
  if (slideCurrent) slideCurrent.textContent = sessionData.current_slide || 0;
  if (slideTotal) slideTotal.textContent = sessionData.total_slides || 0;

  /* 时间线 */
  const positionLabel = document.getElementById("position-label");
  const durationLabel = document.getElementById("duration-label");
  const positionMs = sessionData.position_ms || 0;
  const durationMs = sessionData.duration_ms || 0;
  if (positionLabel) positionLabel.textContent = formatDuration(positionMs);
  if (durationLabel) durationLabel.textContent = formatDuration(durationMs);

  /* 更新 Seek 滑块位置（仅在用户未拖拽时更新） */
  const seekSlider = document.getElementById("seek-slider");
  if (seekSlider && !seekSlider.matches(":active")) {
    seekSlider.dataset.durationMs = String(durationMs);
    if (durationMs > 0) {
      seekSlider.max = "1000";
      seekSlider.value = String(Math.round((positionMs / durationMs) * 1000));
    } else {
      seekSlider.value = "0";
    }
  }

  /* 循环播放按钮状态 */
  const loopButton = document.getElementById("loop-toggle-btn");
  if (loopButton) {
    const isLoopOn = !!sessionData.loop_enabled;
    loopButton.setAttribute("aria-pressed", String(isLoopOn));
    loopButton.classList.toggle("action-button--active", isLoopOn);
  }
}

/** 重置主面板为空状态 */
function resetSessionDOM() {
  applySessionToDOM({
    source_name: "—",
    source_type_label: "—",
    playback_state_label: "—",
    display_mode_label: "—",
    current_slide: 0,
    total_slides: 0,
    position_ms: 0,
    duration_ms: 0,
    loop_enabled: false,
  });
}

/* ═══════════════════════════════════════════════════════════
 * SSE 事件处理入口
 * ═══════════════════════════════════════════════════════════ */

/**
 * 处理 SSE 推送的 playback_state 事件载荷
 * 支持两种格式：
 *   - 多窗口广播：{sessions: [...], splice_active: bool}
 *   - 单窗口更新：{window_id: N, ...sessionFields}
 * @param {object} payload - 已解析的 JSON 载荷
 */
export function handlePlaybackStateEvent(payload) {
  /* 多窗口广播（来自拼接切换等批量操作） */
  if (payload.sessions && Array.isArray(payload.sessions)) {
    payload.sessions.forEach((sessionItem) => {
      applyWindowSession(sessionItem.window_id, sessionItem);
    });
    if (payload.splice_active !== undefined) {
      spliceActive = payload.splice_active;
      updateSpliceUI();
    }
    return;
  }
  /* 单窗口更新（来自 open/control/close 等逐窗口操作） */
  if (payload.window_id) {
    applyWindowSession(payload.window_id, payload);
  }
}

/* ═══════════════════════════════════════════════════════════
 * 初始化
 * ═══════════════════════════════════════════════════════════ */

/**
 * 从 API 加载所有窗口的初始状态
 */
export async function fetchAllSessions() {
  try {
    const response = await fetch("/api/session/");
    const result = await response.json();
    if (result.success) {
      spliceActive = !!result.splice_active;
      updateSpliceUI();
      if (result.sessions) {
        result.sessions.forEach((sessionItem) => {
          applyWindowSession(sessionItem.window_id, sessionItem);
        });
      }
    }
  } catch (fetchError) {
    /* 初始化阶段静默处理网络异常 */
  }
}
