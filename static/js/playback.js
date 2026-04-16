/**
 * SCP-cv 播放控制模块
 * 职责：播放 / 暂停 / 停止 / 关闭、循环切换、PPT 导航、视频 Seek
 */

import { postAction, showBanner, withLoading } from "./utils.js";
import { getActiveWindowId, applyWindowSession } from "./windows.js";

/* ═══════════════════════════════════════════════════════════
 * 基本播放操作
 * ═══════════════════════════════════════════════════════════ */

/**
 * 发送播放控制指令（play / pause / stop）到当前活跃窗口
 * @param {string} action - 控制动作
 * @param {Event} triggerEvent - 触发事件
 */
export async function controlPlayback(action, triggerEvent) {
  await withLoading(triggerEvent, async () => {
    const controlResult = await postAction(
      `/playback/${getActiveWindowId()}/control/`,
      { action },
    );
    if (controlResult.success) {
      if (controlResult.session) {
        applyWindowSession(getActiveWindowId(), controlResult.session);
      }
    } else {
      showBanner(controlResult.error || "操作失败", true);
    }
  });
}

/**
 * 关闭当前窗口播放（停止播放并释放源）
 * @param {Event} triggerEvent - 触发事件
 */
export async function closePlayback(triggerEvent) {
  await withLoading(triggerEvent, async () => {
    const closeResult = await postAction(`/playback/${getActiveWindowId()}/close/`);
    if (closeResult.success) {
      showBanner("已关闭播放");
      if (closeResult.session) {
        applyWindowSession(getActiveWindowId(), closeResult.session);
      }
    } else {
      showBanner(closeResult.error || "关闭失败", true);
    }
  });
}

/**
 * 停止当前播放（toolbar 快捷操作，等价于 closePlayback）
 * @param {Event} triggerEvent - 触发事件
 */
export async function stopPlayback(triggerEvent) {
  await closePlayback(triggerEvent);
}

/**
 * 切换循环播放状态
 * @param {Event} triggerEvent - 触发事件
 */
export async function toggleLoop(triggerEvent) {
  const loopButton = document.getElementById("loop-toggle-btn");
  /* 读取当前状态，取反后发送 */
  const currentlyEnabled = loopButton && loopButton.getAttribute("aria-pressed") === "true";
  const newEnabled = !currentlyEnabled;

  await withLoading(triggerEvent, async () => {
    const loopResult = await postAction(
      `/playback/${getActiveWindowId()}/toggle-loop/`,
      { enabled: newEnabled ? "true" : "false" },
    );
    if (loopResult.success) {
      showBanner(newEnabled ? "循环播放已开启" : "循环播放已关闭");
      if (loopResult.session) {
        applyWindowSession(getActiveWindowId(), loopResult.session);
      }
    } else {
      showBanner(loopResult.error || "切换失败", true);
    }
  });
}

/* ═══════════════════════════════════════════════════════════
 * 内容导航（PPT 翻页 / 视频 Seek）
 * ═══════════════════════════════════════════════════════════ */

/**
 * 发送内容导航指令（next / prev）到当前活跃窗口
 * @param {string} action - 导航动作
 * @param {Event} triggerEvent - 触发事件
 */
export async function navigateContent(action, triggerEvent) {
  await withLoading(triggerEvent, async () => {
    const navResult = await postAction(
      `/playback/${getActiveWindowId()}/navigate/`,
      { action },
    );
    if (navResult.success) {
      if (navResult.session) {
        applyWindowSession(getActiveWindowId(), navResult.session);
      }
    } else {
      showBanner(navResult.error || "导航失败", true);
    }
  });
}

/**
 * 跳转到指定页码（读取 goto-page-input 输入框）
 * @param {Event} triggerEvent - 触发事件
 */
export async function gotoPage(triggerEvent) {
  const pageInput = document.getElementById("goto-page-input");
  const targetPage = pageInput ? parseInt(pageInput.value, 10) : 0;
  if (!targetPage || targetPage < 1) {
    showBanner("请输入有效页码", true);
    return;
  }

  await withLoading(triggerEvent, async () => {
    const gotoResult = await postAction(
      `/playback/${getActiveWindowId()}/navigate/`,
      { action: "goto", target_index: targetPage },
    );
    if (gotoResult.success) {
      if (gotoResult.session) {
        applyWindowSession(getActiveWindowId(), gotoResult.session);
      }
    } else {
      showBanner(gotoResult.error || "跳转失败", true);
    }
  });
}

/**
 * 初始化 Seek 滑块事件绑定
 */
export function initSeekSlider() {
  const seekSlider = document.getElementById("seek-slider");
  if (!seekSlider) return;

  /** Seek 操作节流锁 */
  let _seekThrottleTimer = null;

  /* 用户拖拽滑块完成后发送 Seek 指令 */
  seekSlider.addEventListener("change", () => {
    clearTimeout(_seekThrottleTimer);
    _seekThrottleTimer = setTimeout(async () => {
      const sliderValue = parseInt(seekSlider.value, 10);
      const durationMs = parseInt(seekSlider.dataset.durationMs || "0", 10);
      if (durationMs <= 0) return;
      /* 将滑块百分比转换为毫秒位置 */
      const targetMs = Math.round((sliderValue / 1000) * durationMs);
      const seekResult = await postAction(
        `/playback/${getActiveWindowId()}/navigate/`,
        { action: "seek", position_ms: targetMs },
      );
      if (!seekResult.success) {
        showBanner(seekResult.error || "Seek 失败", true);
      }
    }, 200);
  });
}
