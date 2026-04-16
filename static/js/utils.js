/**
 * SCP-cv 通用工具函数
 * 职责：CSRF 提取、网络请求封装、通知横幅、HTML 转义、时间格式化、
 *       按钮加载态管理、确认弹窗
 */

/* ═══════════════════════════════════════════════════════════
 * 网络请求
 * ═══════════════════════════════════════════════════════════ */

/**
 * 从页面 cookie 中提取 CSRF token
 * @returns {string} CSRF token 值
 */
export function getCSRFToken() {
  const cookieValue = document.cookie
    .split("; ")
    .find((row) => row.startsWith("csrftoken="));
  return cookieValue ? cookieValue.split("=")[1] : "";
}

/**
 * 统一的 POST 请求封装（application/x-www-form-urlencoded）
 * @param {string} url - 请求地址
 * @param {object} bodyParams - 请求体键值对
 * @returns {Promise<object>} 解析后的 JSON 响应
 */
export async function postAction(url, bodyParams = {}) {
  const formData = new URLSearchParams();
  for (const [key, value] of Object.entries(bodyParams)) {
    formData.append(key, String(value));
  }
  const response = await fetch(url, {
    method: "POST",
    headers: {
      "X-CSRFToken": getCSRFToken(),
      "X-Requested-With": "XMLHttpRequest",
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: formData.toString(),
  });
  return response.json();
}

/**
 * 发送 multipart/form-data 请求（用于文件上传）
 * @param {string} url - 请求地址
 * @param {FormData} formData - 包含文件的 FormData 对象
 * @returns {Promise<object>} 解析后的 JSON 响应
 */
export async function postFormData(url, formData) {
  const response = await fetch(url, {
    method: "POST",
    headers: {
      "X-CSRFToken": getCSRFToken(),
      "X-Requested-With": "XMLHttpRequest",
    },
    body: formData,
  });
  return response.json();
}

/* ═══════════════════════════════════════════════════════════
 * 通知横幅：成功消息自动隐藏，错误消息需手动关闭
 * ═══════════════════════════════════════════════════════════ */

/**
 * 在全局横幅中展示消息
 * 成功消息 4 秒后自动淡出，错误消息保持不消失直到下次操作
 * @param {string} message - 消息文本
 * @param {boolean} isError - 是否为错误消息
 */
export function showBanner(message, isError = false) {
  const bannerElement = document.getElementById("global-banner");
  if (!bannerElement) return;

  bannerElement.textContent = message;
  bannerElement.style.display = "";

  /* 移除旧状态类，添加新状态类 */
  bannerElement.classList.remove("banner--error", "banner--success");
  bannerElement.classList.add(isError ? "banner--error" : "banner--success");

  clearTimeout(bannerElement._hideTimer);
  /* 错误消息不自动隐藏，成功消息 4 秒后淡出 */
  if (!isError) {
    bannerElement._hideTimer = setTimeout(() => {
      bannerElement.style.display = "none";
    }, 4000);
  }
}

/* ═══════════════════════════════════════════════════════════
 * 文本工具
 * ═══════════════════════════════════════════════════════════ */

/**
 * 转义 HTML 特殊字符，防止 XSS
 * @param {string} unsafeText - 需要转义的文本
 * @returns {string} 转义后的安全文本
 */
export function escapeHtml(unsafeText) {
  const escapeDiv = document.createElement("div");
  escapeDiv.textContent = unsafeText;
  return escapeDiv.innerHTML;
}

/**
 * 将毫秒时长格式化为 MM:SS
 * @param {number} milliseconds - 毫秒数
 * @returns {string} 格式化后的时间字符串
 */
export function formatDuration(milliseconds) {
  const totalSeconds = Math.max(0, Math.floor(milliseconds / 1000));
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

/* ═══════════════════════════════════════════════════════════
 * 按钮加载状态管理：防止重复提交
 * ═══════════════════════════════════════════════════════════ */

/**
 * 将按钮置为加载中状态，禁止交互
 * @param {HTMLButtonElement} buttonElement - 目标按钮
 */
function setButtonLoading(buttonElement) {
  if (!buttonElement) return;
  buttonElement.disabled = true;
  buttonElement.classList.add("action-button--loading");
}

/**
 * 恢复按钮为可交互状态
 * @param {HTMLButtonElement} buttonElement - 目标按钮
 */
function clearButtonLoading(buttonElement) {
  if (!buttonElement) return;
  buttonElement.disabled = false;
  buttonElement.classList.remove("action-button--loading");
}

/**
 * 包装异步操作，自动管理触发按钮的加载态
 * @param {Event|HTMLElement|null} triggerEvent - 触发事件或按钮元素
 * @param {Function} asyncCallback - 要执行的异步函数
 */
export async function withLoading(triggerEvent, asyncCallback) {
  /* 从事件或直接传入的元素中获取按钮 */
  const buttonElement = triggerEvent instanceof HTMLElement
    ? triggerEvent
    : (triggerEvent && triggerEvent.currentTarget) || null;

  setButtonLoading(buttonElement);
  try {
    await asyncCallback();
  } catch (error) {
    showBanner(error.message || "操作异常", true);
  } finally {
    clearButtonLoading(buttonElement);
  }
}

/* ═══════════════════════════════════════════════════════════
 * 确认弹窗：用于删除等危险操作
 * ═══════════════════════════════════════════════════════════ */

/**
 * 显示确认弹窗，返回 Promise<boolean>
 * @param {string} title - 弹窗标题
 * @param {string} message - 弹窗正文
 * @returns {Promise<boolean>} 用户是否确认
 */
export function confirmAction(title, message) {
  return new Promise((resolve) => {
    const backdrop = document.getElementById("confirm-dialog-backdrop");
    const titleElement = document.getElementById("confirm-dialog-title");
    const messageElement = document.getElementById("confirm-dialog-message");
    const confirmButton = document.getElementById("confirm-dialog-ok");
    const cancelButton = document.getElementById("confirm-dialog-cancel");

    /* 弹窗元素不存在时降级为 window.confirm */
    if (!backdrop || !confirmButton || !cancelButton) {
      resolve(window.confirm(message));
      return;
    }

    if (titleElement) titleElement.textContent = title;
    if (messageElement) messageElement.textContent = message;
    backdrop.classList.add("confirm-dialog-backdrop--visible");

    /** 清理侦听器并关闭弹窗 */
    function cleanup(userConfirmed) {
      backdrop.classList.remove("confirm-dialog-backdrop--visible");
      confirmButton.removeEventListener("click", onConfirm);
      cancelButton.removeEventListener("click", onCancel);
      backdrop.removeEventListener("keydown", onKeydown);
      resolve(userConfirmed);
    }

    function onConfirm() { cleanup(true); }
    function onCancel() { cleanup(false); }

    /** Escape 键关闭弹窗 */
    function onKeydown(keyEvent) {
      if (keyEvent.key === "Escape") cleanup(false);
    }

    confirmButton.addEventListener("click", onConfirm);
    cancelButton.addEventListener("click", onCancel);
    backdrop.addEventListener("keydown", onKeydown);

    /* 自动聚焦到取消按钮，防止误操作 */
    cancelButton.focus();
  });
}
