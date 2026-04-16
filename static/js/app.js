/**
 * SCP-cv 播放控制台 — 入口模块
 * 职责：导入各功能模块、注册全局函数到 window、初始化时钟与轮询
 *
 * 模块拆分：
 *   utils.js    — 通用工具（CSRF、fetch、通知、格式化、加载态、弹窗）
 *   tabs.js     — Tab 导航
 *   windows.js  — 多窗口状态管理与 DOM 同步
 *   sources.js  — 媒体源 CRUD
 *   playback.js — 播放控制与导航
 *   sse.js      — SSE 实时事件流
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
import { connectSSE } from "./sse.js";

/* ═══════════════════════════════════════════════════════════
 * 注册全局函数（供 HTML onclick 属性调用）
 * ═══════════════════════════════════════════════════════════ */

/* 窗口管理 */
window.selectWindow = selectWindow;
window.toggleSplice = toggleSplice;
window.showWindowIds = showWindowIds;

/* 媒体源 */
window.refreshSources = refreshSources;
window.openSource = openSource;
window.removeSource = removeSource;

/* 播放控制 */
window.controlPlayback = controlPlayback;
window.closePlayback = closePlayback;
window.stopPlayback = stopPlayback;
window.toggleLoop = toggleLoop;
window.navigateContent = navigateContent;
window.gotoPage = gotoPage;

/** 刷新整个页面 */
window.refreshPage = function refreshPage() {
  location.reload();
};

/* ═══════════════════════════════════════════════════════════
 * 初始化
 * ═══════════════════════════════════════════════════════════ */

/* 时钟 */
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

/* SSE 实时连接 */
connectSSE();

/* 加载所有窗口初始状态 */
fetchAllSessions();

/* 源列表自动轮询（每 15 秒同步流状态） */
setInterval(refreshSources, 15000);
