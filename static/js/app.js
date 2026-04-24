/**
 * SCP-cv 播放控制台 — 入口模块
 * 职责：导入各功能模块、初始化时钟、注册全局事件委托
 *
 * 模块拆分：
 *   utils.js      — 通用工具（CSRF、fetch、通知、格式化、加载态、弹窗）
 *   tabs.js       — Tab 导航
 *   windows.js    — 多窗口状态管理与 DOM 同步
 *   sources.js    — 媒体源 CRUD
 *   playback.js   — 播放控制与导航
 *   streaming.js  — gRPC 流式订阅（替代 SSE）
 *   scenarios.js  — 预案管理
 */

import { initTabNavigation } from "./tabs.js";
import {
  selectWindow,
  toggleSplice,
  showWindowIds,
  fetchAllSessions,
} from "./windows.js";
import {
  refreshSources,
  openSource,
  removeSource,
  initSourceForms,
} from "./sources.js";
import {
  controlPlayback,
  closePlayback,
  stopPlayback,
  toggleLoop,
  navigateContent,
  gotoPage,
  initSeekSlider,
} from "./playback.js";
import { connectStream } from "./streaming.js";
import {
  onSpliceModeToggle,
  saveScenario,
  deleteScenario,
  activateScenario,
  editScenario,
  captureCurrentScenario,
  resetScenarioForm,
} from "./scenarios.js";

/* ═══════════════════════════════════════════════════════════
 * 事件委托：根据 data-action 属性分发点击事件
 * ═══════════════════════════════════════════════════════════ */

/** data-action 名称 → 处理函数的映射表 */
const ACTION_HANDLERS = {
  /* 工具栏 */
  "stop-playback": (event) => stopPlayback(event),
  "refresh-page": () => location.reload(),

  /* 窗口管理 */
  "select-window": (event, target) => {
    const windowId = parseInt(target.dataset.windowId, 10);
    selectWindow(windowId, target);
  },
  "toggle-splice": (event) => toggleSplice(event),
  "show-window-ids": (event) => showWindowIds(event),

  /* 媒体源 */
  "refresh-sources": () => refreshSources(),
  "open-source": (event, target) => {
    const sourceId = parseInt(target.dataset.sourceId, 10);
    openSource(sourceId, event);
  },
  "remove-source": (event, target) => {
    const sourceId = parseInt(target.dataset.sourceId, 10);
    removeSource(sourceId, event);
  },

  /* 播放控制 */
  "playback-control": (event, target) => {
    controlPlayback(target.dataset.playbackAction, event);
  },
  "close-playback": (event) => closePlayback(event),
  "toggle-loop": (event) => toggleLoop(event),
  "navigate-content": (event, target) => {
    navigateContent(target.dataset.navAction, event);
  },
  "goto-page": (event) => gotoPage(event),

  /* 预案管理 */
  "activate-scenario": (event, target) => {
    const scenarioId = parseInt(target.dataset.scenarioId, 10);
    activateScenario(scenarioId, event);
  },
  "edit-scenario": (_event, target) => {
    const scenarioId = parseInt(target.dataset.scenarioId, 10);
    editScenario(scenarioId);
  },
  "delete-scenario": (event, target) => {
    const scenarioId = parseInt(target.dataset.scenarioId, 10);
    deleteScenario(scenarioId, event);
  },
  "save-scenario": (event) => saveScenario(event),
  "capture-current-scenario": (event) => captureCurrentScenario(event),
  "reset-scenario-form": () => resetScenarioForm(),
  "splice-mode-toggle": () => onSpliceModeToggle(),
};

/**
 * 全局点击事件委托：从被点击元素向上查找最近的 [data-action] 节点，
 * 匹配到对应处理函数后执行。
 */
document.addEventListener("click", (clickEvent) => {
  const actionTarget = clickEvent.target.closest("[data-action]");
  if (!actionTarget) return;

  const actionName = actionTarget.dataset.action;
  const handler = ACTION_HANDLERS[actionName];
  if (handler) {
    handler(clickEvent, actionTarget);
  }
});

/**
 * change 事件委托：处理 checkbox、select 等表单元素的 data-action
 */
document.addEventListener("change", (changeEvent) => {
  const actionTarget = changeEvent.target.closest("[data-action]");
  if (!actionTarget) return;

  const actionName = actionTarget.dataset.action;
  const handler = ACTION_HANDLERS[actionName];
  if (handler) {
    handler(changeEvent, actionTarget);
  }
});

/* ═══════════════════════════════════════════════════════════
 * 初始化
 * ═══════════════════════════════════════════════════════════ */

/* 页脚时钟 */
const clockElement = document.querySelector("[data-clock]");
const timeFormatter = new Intl.DateTimeFormat("zh-CN", {
  dateStyle: "medium",
  timeStyle: "medium",
});
const refreshClock = () => {
  if (clockElement) {
    clockElement.textContent = timeFormatter.format(new Date());
  }
};
refreshClock();
setInterval(refreshClock, 1000);

/* Tab 导航 */
initTabNavigation();

/* 媒体源表单事件绑定 */
initSourceForms();

/* Seek 滑块事件绑定 */
initSeekSlider();

/* gRPC 流式订阅（替代 SSE） */
connectStream();

/* 加载所有窗口初始状态 */
fetchAllSessions();

/* 源列表自动轮询（每 15 秒同步流状态） */
setInterval(refreshSources, 15000);
