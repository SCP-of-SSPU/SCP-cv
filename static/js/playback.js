/**
 * SCP-cv 播放控制模块
 * 职责：播放 / 暂停 / 停止 / 关闭、循环切换、PPT 导航、视频 Seek
 * 所有操作通过 gRPC-Web 调用后端，状态更新由 gRPC 流推送。
 */

import { showBanner, withLoading } from "./utils.js";
import { getActiveWindowId } from "./windows.js";
import {
  controlPlayback as grpcControlPlayback,
  closeSource,
  toggleLoop as grpcToggleLoop,
  navigateContent as grpcNavigateContent,
} from "./grpc-client.bundle.js";

/* ═══════════════════════════════════════════════════════════
 * 基本播放操作
 * ═══════════════════════════════════════════════════════════ */

/**
 * 发送播放控制指令（play / pause / stop）到当前活跃窗口
 * @param {string} action - 控制动作："play" | "pause" | "stop"
 * @param {Event} triggerEvent - 触发事件（用于 withLoading 锁定按钮）
 */
export async function controlPlayback(action, triggerEvent) {
  await withLoading(triggerEvent, async () => {
    const reply = await grpcControlPlayback(getActiveWindowId(), action);
    const result = reply.toObject();
    if (!result.success) {
      showBanner(result.message || "操作失败", true);
    }
    /* 成功时状态更新通过 gRPC 流推送 */
  });
}

/**
 * 关闭当前窗口播放（停止播放并释放源）
 * @param {Event} triggerEvent - 触发事件
 */
export async function closePlayback(triggerEvent) {
  await withLoading(triggerEvent, async () => {
    const reply = await closeSource(getActiveWindowId());
    const result = reply.toObject();
    if (result.success) {
      showBanner("已关闭播放");
    } else {
      showBanner(result.message || "关闭失败", true);
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
  const currentlyEnabled =
    loopButton && loopButton.getAttribute("aria-pressed") === "true";
  const newEnabled = !currentlyEnabled;

  await withLoading(triggerEvent, async () => {
    const reply = await grpcToggleLoop(getActiveWindowId(), newEnabled);
    const result = reply.toObject();
    if (result.success) {
      showBanner(newEnabled ? "循环播放已开启" : "循环播放已关闭");
    } else {
      showBanner(result.message || "切换失败", true);
    }
  });
}

/* ═══════════════════════════════════════════════════════════
 * 内容导航（PPT 翻页 / 视频 Seek）
 * ═══════════════════════════════════════════════════════════ */

/**
 * 发送内容导航指令（next / prev）到当前活跃窗口
 * @param {string} action - 导航动作："next" | "prev"
 * @param {Event} triggerEvent - 触发事件
 */
export async function navigateContent(action, triggerEvent) {
  await withLoading(triggerEvent, async () => {
    const reply = await grpcNavigateContent(getActiveWindowId(), action);
    const result = reply.toObject();
    if (!result.success) {
      showBanner(result.message || "导航失败", true);
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
    const reply = await grpcNavigateContent(
      getActiveWindowId(),
      "goto",
      targetPage,
    );
    const result = reply.toObject();
    if (!result.success) {
      showBanner(result.message || "跳转失败", true);
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
      const reply = await grpcNavigateContent(
        getActiveWindowId(),
        "seek",
        0,
        targetMs,
      );
      const result = reply.toObject();
      if (!result.success) {
        showBanner(result.message || "Seek 失败", true);
      }
    }, 200);
  });
}
