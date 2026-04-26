/**
 * SCP-cv 多窗口状态管理模块
 * 职责：窗口切换、拼接模式、状态缓存、DOM 状态同步、gRPC 流式事件分发
 */

import { showBanner, withLoading, formatDuration } from "./utils.js";
import { setSpliceMode, showWindowIds as grpcShowWindowIds, getAllSessionSnapshots } from "./grpc-client.bundle.js";

/* ═══════════════════════════════════════════════════════════
 * 多窗口共享状态
 * ═══════════════════════════════════════════════════════════ */

/** 当前活跃的控制目标窗口编号（1-4） */
let activeWindowId = 1;

/** 各窗口的会话快照缓存 {windowId: sessionData} */
const windowSessions = {};

/** 拼接模式是否启用 */
let spliceActive = false;

/** 播放状态 → Fluent 2 语义色类 */
const STATE_CHIP_CLASS_MAP = {
  playing: "chip--success",
  paused: "chip--warning",
  loading: "chip--accent",
  stopped: "chip--neutral",
  idle: "chip--neutral",
  error: "chip--error",
};

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
  const pptRemoteWinId = document.getElementById("ppt-remote-window-id");
  const toolbarWin = document.getElementById("toolbar-active-window");
  const sourceTargetWinId = document.getElementById("source-target-window-id");
  if (heroWinId) heroWinId.textContent = String(windowId);
  if (ctrlWinId) ctrlWinId.textContent = String(windowId);
  if (pptRemoteWinId) pptRemoteWinId.textContent = String(windowId);
  if (toolbarWin) toolbarWin.textContent = "窗口 " + windowId;
  if (sourceTargetWinId) sourceTargetWinId.textContent = String(windowId);

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
    const reply = await setSpliceMode(newEnabled);
    const result = reply.toObject();
    if (result.success) {
      spliceActive = result.spliceActive;
      showBanner(spliceActive ? "拼接模式已开启（窗口 1+2）" : "拼接模式已关闭");
      updateSpliceUI();
      if (result.sessionsList) {
        result.sessionsList.forEach((snapshot) => {
          applyWindowSession(snapshot.windowId, snapshot);
        });
      }
    } else {
      showBanner("拼接切换失败", true);
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
    const reply = await grpcShowWindowIds();
    const result = reply.toObject();
    if (result.success) {
      showBanner("已触发窗口 ID 显示（5 秒）");
    } else {
      showBanner(result.message || "操作失败", true);
    }
  });
}

/* ═══════════════════════════════════════════════════════════
 * 会话状态分发与 DOM 同步
 * ═══════════════════════════════════════════════════════════ */

/**
 * 将会话数据写入缓存，并同步到选择器标签和主面板
 * @param {number} windowId - 窗口编号
 * @param {object} sessionData - gRPC SessionSnapshot.toObject() 快照
 */
export function applyWindowSession(windowId, sessionData) {
  windowSessions[windowId] = sessionData;

  /* 更新窗口选择器上的状态标签 */
  const stateEl = document.getElementById("win-state-" + windowId);
  const settingsStateEl = document.getElementById("settings-win-state-" + windowId);
  const settingsSourceEl = document.getElementById("settings-win-source-" + windowId);
  const settingsProgressEl = document.getElementById("settings-win-progress-" + windowId);
  const stateLabel = sessionData.playbackStateLabel || "空闲";
  const sourceName = sessionData.sourceName || "未打开媒体源";
  const stateClassName = STATE_CHIP_CLASS_MAP[sessionData.playbackState] || "chip--neutral";
  if (stateEl) {
    stateEl.textContent = stateLabel;
    stateEl.dataset.state = sessionData.playbackState || "idle";
  }
  if (settingsStateEl) {
    settingsStateEl.textContent = stateLabel;
    settingsStateEl.className = `chip ${stateClassName}`;
  }
  if (settingsSourceEl) settingsSourceEl.textContent = sourceName;
  if (settingsProgressEl) settingsProgressEl.textContent = formatSessionProgress(sessionData);

  /* 如果是当前活跃窗口，同步到主面板 */
  if (windowId === activeWindowId) {
    applySessionToDOM(sessionData);
  }
}

/**
 * 将窗口快照格式化为设置页进度文本。
 * @param {object} sessionData - gRPC SessionSnapshot.toObject() 快照
 * @returns {string} 可读进度文本
 */
function formatSessionProgress(sessionData) {
  const totalSlides = sessionData.totalSlides || 0;
  if (totalSlides > 0) {
    return `第 ${sessionData.currentSlide || 0} / ${totalSlides} 页`;
  }

  const durationMs = sessionData.durationMs || 0;
  if (durationMs > 0) {
    return `${formatDuration(sessionData.positionMs || 0)} / ${formatDuration(durationMs)}`;
  }

  return "暂无进度";
}

/**
 * 将会话快照应用到主面板 DOM 元素
 * @param {object} sessionData - gRPC SessionSnapshot.toObject() 快照（camelCase 字段）
 */
function applySessionToDOM(sessionData) {
  /* Hero 面板 */
  const heroSourceName = document.getElementById("hero-source-name");
  const heroSourceType = document.getElementById("hero-source-type");
  const heroPlaybackState = document.getElementById("hero-playback-state");
  const heroDisplayMode = document.getElementById("hero-display-mode");
  const pptRemoteSourceName = document.getElementById("ppt-remote-source-name");
  const pptRemotePlaybackState = document.getElementById("ppt-remote-playback-state");
  if (heroSourceName) heroSourceName.textContent = sessionData.sourceName || "无";
  if (heroSourceType) heroSourceType.textContent = sessionData.sourceTypeLabel || "无";
  if (heroPlaybackState) heroPlaybackState.textContent = sessionData.playbackStateLabel || "—";
  if (heroDisplayMode) heroDisplayMode.textContent = sessionData.displayModeLabel || "—";
  if (pptRemoteSourceName) pptRemoteSourceName.textContent = sessionData.sourceName || "无";
  if (pptRemotePlaybackState) {
    pptRemotePlaybackState.textContent = sessionData.playbackStateLabel || "—";
  }

  /* PPT 翻页状态 */
  const slideCurrent = document.getElementById("slide-current");
  const slideTotal = document.getElementById("slide-total");
  const pptRemoteCurrent = document.getElementById("ppt-remote-current-slide");
  const pptRemoteTotal = document.getElementById("ppt-remote-total-slides");
  if (slideCurrent) slideCurrent.textContent = sessionData.currentSlide || 0;
  if (slideTotal) slideTotal.textContent = sessionData.totalSlides || 0;
  if (pptRemoteCurrent) pptRemoteCurrent.textContent = sessionData.currentSlide || 0;
  if (pptRemoteTotal) pptRemoteTotal.textContent = sessionData.totalSlides || 0;

  const totalSlides = sessionData.totalSlides || 0;
  ["goto-page-input", "ppt-remote-goto-input"].forEach((inputId) => {
    const pageInput = document.getElementById(inputId);
    if (!pageInput) return;
    pageInput.max = totalSlides > 0 ? String(totalSlides) : "";
  });

  /* 时间线 */
  const positionLabel = document.getElementById("position-label");
  const durationLabel = document.getElementById("duration-label");
  const positionMs = sessionData.positionMs || 0;
  const durationMs = sessionData.durationMs || 0;
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
    const isLoopOn = !!sessionData.loopEnabled;
    loopButton.setAttribute("aria-pressed", String(isLoopOn));
    loopButton.classList.toggle("action-button--active", isLoopOn);
  }
}

/** 重置主面板为空状态 */
function resetSessionDOM() {
  applySessionToDOM({
    sourceName: "—",
    sourceTypeLabel: "—",
    playbackStateLabel: "—",
    displayModeLabel: "—",
    currentSlide: 0,
    totalSlides: 0,
    positionMs: 0,
    durationMs: 0,
    loopEnabled: false,
  });
}

/* ═══════════════════════════════════════════════════════════
 * gRPC 流式事件处理入口
 * ═══════════════════════════════════════════════════════════ */

/**
 * 处理 gRPC 流式推送的 PlaybackStateEvent 载荷
 * @param {object} eventPayload - PlaybackStateEvent.toObject() 结果
 */
export function handlePlaybackStateEvent(eventPayload) {
  /* gRPC 流式事件：sessionsList 包含所有变更的窗口快照 */
  if (eventPayload.sessionsList && Array.isArray(eventPayload.sessionsList)) {
    eventPayload.sessionsList.forEach((snapshot) => {
      applyWindowSession(snapshot.windowId, snapshot);
    });
  }
  /* 拼接状态可能从全局快照同步到来 */
  if (eventPayload.spliceActive !== undefined) {
    spliceActive = eventPayload.spliceActive;
    updateSpliceUI();
  }
}

/* ═══════════════════════════════════════════════════════════
 * 初始化
 * ═══════════════════════════════════════════════════════════ */

/**
 * 通过 gRPC 加载所有窗口的初始状态
 */
export async function fetchAllSessions() {
  try {
    const reply = await getAllSessionSnapshots();
    const result = reply.toObject();
    if (result.success) {
      spliceActive = !!result.spliceActive;
      updateSpliceUI();
      if (result.sessionsList) {
        result.sessionsList.forEach((snapshot) => {
          applyWindowSession(snapshot.windowId, snapshot);
        });
      }
    }
  } catch (fetchError) {
    /* 初始化阶段静默处理网络异常 */
  }
}
