/**
 * SCP-cv 播放控制台前端逻辑
 * 职责：AJAX 操作提交、SSE 实时状态推送、DOM 动态更新
 */
document.addEventListener("DOMContentLoaded", () => {

  /* ═══ 通用工具 ═══ */

  /**
   * 从页面 cookie 中提取 CSRF token
   * @returns {string} CSRF token 值
   */
  function getCSRFToken() {
    const cookieValue = document.cookie
      .split("; ")
      .find((row) => row.startsWith("csrftoken="));
    return cookieValue ? cookieValue.split("=")[1] : "";
  }

  /**
   * 统一的 POST 请求封装，自动附加 CSRF token
   * @param {string} url - 请求地址
   * @param {object} bodyParams - 请求体键值对
   * @returns {Promise<object>} 解析后的 JSON 响应
   */
  async function postAction(url, bodyParams = {}) {
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
   * 在全局横幅中展示消息（自动淡出）
   * @param {string} message - 消息文本
   * @param {boolean} isError - 是否为错误消息
   */
  function showBanner(message, isError = false) {
    const bannerElement = document.getElementById("global-banner");
    if (!bannerElement) return;
    bannerElement.textContent = message;
    bannerElement.style.display = "";
    bannerElement.style.color = isError ? "var(--warning)" : "var(--accent-strong)";
    clearTimeout(bannerElement._hideTimer);
    bannerElement._hideTimer = setTimeout(() => {
      bannerElement.style.display = "none";
    }, 4000);
  }

  /* ═══ 时钟 ═══ */
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

  /* ═══ 文件上传 ═══ */
  const uploadForm = document.getElementById("upload-form");
  if (uploadForm) {
    uploadForm.addEventListener("submit", async (submitEvent) => {
      submitEvent.preventDefault();
      const fileInput = document.getElementById("ppt-file-input");
      if (!fileInput || !fileInput.files.length) {
        showBanner("请先选择 PPT/PPTX 文件", true);
        return;
      }

      const formData = new FormData();
      formData.append("ppt_file", fileInput.files[0]);

      showBanner("正在上传并解析文件，请稍候…");
      try {
        const uploadResponse = await fetch("/upload/", {
          method: "POST",
          headers: {
            "X-CSRFToken": getCSRFToken(),
            "X-Requested-With": "XMLHttpRequest",
          },
          body: formData,
        });
        const uploadResult = await uploadResponse.json();
        if (uploadResult.success) {
          showBanner(`上传成功：${uploadResult.display_name}`);
          fileInput.value = "";
          /* SSE 会推送 resource_updated 事件，触发页面刷新 */
        } else {
          showBanner(`上传失败：${uploadResult.error}`, true);
        }
      } catch (networkError) {
        showBanner("网络错误，上传失败", true);
      }
    });
  }

  /* ═══ PPT 操作 ═══ */

  /** 翻页（上一页/下一页） */
  window.pptNavigate = async function pptNavigate(direction) {
    const navigateResult = await postAction("/ppt-navigate/", { direction });
    if (!navigateResult.success) {
      showBanner(navigateResult.error, true);
    }
  };

  /** 跳转到指定页 */
  window.pptJump = async function pptJump() {
    const jumpInput = document.getElementById("jump-page-input");
    const targetPage = jumpInput ? jumpInput.value.trim() : "";
    if (!targetPage) {
      showBanner("请输入目标页码", true);
      return;
    }
    const jumpResult = await postAction("/ppt-navigate/", {
      direction: "goto",
      target_page: targetPage,
    });
    if (jumpResult.success && jumpInput) {
      jumpInput.value = "";
    } else if (!jumpResult.success) {
      showBanner(jumpResult.error, true);
    }
  };

  /** 打开指定 PPT 资源 */
  window.openResource = async function openResource(resourceId) {
    const openResult = await postAction("/open-resource/", { resource_id: resourceId });
    if (!openResult.success) {
      showBanner(openResult.error, true);
    }
  };

  /** 删除指定资源（带确认） */
  window.deleteResource = async function deleteResource(resourceId, displayName) {
    if (!confirm(`确认删除「${displayName}」？此操作不可撤销。`)) return;
    const deleteResult = await postAction("/delete/", { resource_id: resourceId });
    if (deleteResult.success) {
      showBanner(`已删除「${displayName}」`);
    } else {
      showBanner(deleteResult.error, true);
    }
  };

  /* ═══ 播放控制 ═══ */

  /** 停止当前播放 */
  window.stopPlayback = async function stopPlayback() {
    const stopResult = await postAction("/stop/");
    if (!stopResult.success) {
      showBanner(stopResult.error, true);
    }
  };

  /** 切换显示模式/显示器 */
  window.switchDisplay = async function switchDisplay(displayMode, targetDisplayName) {
    const switchResult = await postAction("/switch-display/", {
      display_mode: displayMode,
      target_display_name: targetDisplayName,
    });
    if (!switchResult.success) {
      showBanner(switchResult.error, true);
    }
  };

  /** 打开 SRT 流 */
  window.openStream = async function openStream(streamId) {
    const streamResult = await postAction("/open-stream/", { stream_id: streamId });
    if (!streamResult.success) {
      showBanner(streamResult.error, true);
    }
  };

  /** 刷新页面 */
  window.refreshPage = function refreshPage() {
    location.reload();
  };

  /* ═══ SSE 实时事件流 ═══ */
  const sseStatusElement = document.getElementById("sse-status");

  /** 更新 SSE 连接状态显示 */
  function setSseStatus(label, stateClass) {
    if (!sseStatusElement) return;
    sseStatusElement.textContent = label;
    sseStatusElement.className = "toolbar__status";
    if (stateClass) {
      sseStatusElement.classList.add(stateClass);
    }
  }

  /**
   * 处理 SSE 收到的状态事件，更新 Hero 面板和 PPT 控件
   * @param {object} sessionData - 来自 playback_state 事件的会话快照
   */
  function applySessionState(sessionData) {
    /* Hero 面板 */
    const heroTitle = document.getElementById("hero-title");
    const heroKind = document.getElementById("hero-kind");
    const heroState = document.getElementById("hero-state");
    const heroDisplay = document.getElementById("hero-display");
    const heroPage = document.getElementById("hero-page");

    if (heroTitle) {
      if (sessionData.content_kind === "ppt") {
        heroTitle.textContent = sessionData.resource_title || "PPT 资源";
      } else if (sessionData.content_kind === "stream") {
        heroTitle.textContent = sessionData.stream_name || "SRT 流";
      } else {
        heroTitle.textContent = "尚未打开资源";
      }
    }
    if (heroKind) heroKind.textContent = sessionData.content_kind_label || "—";
    if (heroState) heroState.textContent = sessionData.playback_state_label || "—";
    if (heroDisplay) heroDisplay.textContent = sessionData.display_mode_label || "—";
    if (heroPage) heroPage.textContent = sessionData.page_progress || "—";

    /* 翻页 badge */
    const pageBadge = document.getElementById("ppt-page-badge");
    if (pageBadge) pageBadge.textContent = sessionData.page_progress || "—";
  }

  /**
   * 建立 SSE 连接，处理事件和自动重连
   */
  function connectSSE() {
    setSseStatus("SSE: 连接中…", "");
    const eventSource = new EventSource("/events/");

    eventSource.onopen = () => {
      setSseStatus("SSE: 已连接", "toolbar__status--connected");
    };

    /* 播放状态变更 → 更新 Hero 面板 */
    eventSource.addEventListener("playback_state", (sseEvent) => {
      try {
        const statePayload = JSON.parse(sseEvent.data);
        applySessionState(statePayload);
      } catch (parseError) {
        /* 忽略格式异常的事件 */
      }
    });

    /* 资源列表变更 → 整页刷新（资源表格结构较复杂，直接刷新） */
    eventSource.addEventListener("resource_updated", () => {
      location.reload();
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

  connectSSE();
});
