/**
 * SCP-cv 播放控制台前端逻辑
 * 职责：Tab 切换、媒体源 CRUD、播放控制、导航/Seek、SSE 实时状态推送
 */
document.addEventListener("DOMContentLoaded", () => {

  /* ═══════════════════════════════════════════════════════════
   * 通用工具
   * ═══════════════════════════════════════════════════════════ */

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
   * 统一的 POST 请求封装（application/x-www-form-urlencoded）
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
   * 发送 multipart/form-data 请求（用于文件上传）
   * @param {string} url - 请求地址
   * @param {FormData} formData - 包含文件的 FormData 对象
   * @returns {Promise<object>} 解析后的 JSON 响应
   */
  async function postFormData(url, formData) {
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

  /**
   * 转义 HTML 特殊字符，防止 XSS
   * @param {string} unsafeText - 需要转义的文本
   * @returns {string} 转义后的安全文本
   */
  function escapeHtml(unsafeText) {
    const escapeDiv = document.createElement("div");
    escapeDiv.textContent = unsafeText;
    return escapeDiv.innerHTML;
  }

  /**
   * 将毫秒时长格式化为 MM:SS
   * @param {number} milliseconds - 毫秒数
   * @returns {string} 格式化后的时间字符串
   */
  function formatDuration(milliseconds) {
    const totalSeconds = Math.max(0, Math.floor(milliseconds / 1000));
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
  }

  /* ═══════════════════════════════════════════════════════════
   * 时钟
   * ═══════════════════════════════════════════════════════════ */
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

  /* ═══════════════════════════════════════════════════════════
   * Tab 切换
   * ═══════════════════════════════════════════════════════════ */

  /** 初始化 Tab 导航的点击事件与面板切换 */
  function initTabNavigation() {
    const tabButtons = document.querySelectorAll(".tab-bar__item[data-tab]");
    tabButtons.forEach((tabButton) => {
      tabButton.addEventListener("click", () => {
        const targetTabId = tabButton.dataset.tab;

        /* 更新按钮激活态 */
        tabButtons.forEach((otherButton) => {
          const isActive = otherButton === tabButton;
          otherButton.classList.toggle("tab-bar__item--active", isActive);
          otherButton.setAttribute("aria-selected", String(isActive));
        });

        /* 切换面板显示 */
        document.querySelectorAll(".tab-panel").forEach((panel) => {
          const isPanelActive = panel.id === `tab-${targetTabId}`;
          panel.classList.toggle("tab-panel--active", isPanelActive);
          panel.hidden = !isPanelActive;
        });
      });
    });
  }

  initTabNavigation();

  /* ═══════════════════════════════════════════════════════════
   * 媒体源管理
   * ═══════════════════════════════════════════════════════════ */

  /** 防止并发的源列表刷新锁 */
  let _sourceSyncInFlight = false;

  /**
   * 刷新媒体源列表，从 API 拉取最新数据并重新渲染
   */
  window.refreshSources = async function refreshSources() {
    if (_sourceSyncInFlight) return;
    _sourceSyncInFlight = true;
    try {
      const response = await fetch("/api/sources/");
      const result = await response.json();
      if (result.success) {
        renderSourceList(result.sources);
        /* 同步结果提示 */
        const registered = (result.sync_result && result.sync_result.registered) || 0;
        if (registered > 0) {
          showBanner(`发现 ${registered} 条新流，已自动注册`);
        }
      }
    } catch (networkError) {
      /* 网络异常静默处理 */
    } finally {
      _sourceSyncInFlight = false;
    }
  };

  /**
   * 动态渲染媒体源列表到 DOM
   * @param {Array<object>} sourceList - 媒体源数据数组
   */
  function renderSourceList(sourceList) {
    const sourceContainer = document.getElementById("source-list-container");
    const sourceBadge = document.getElementById("source-count-badge");
    if (!sourceContainer) return;

    if (sourceBadge) {
      sourceBadge.textContent = `${sourceList.length} 个`;
    }

    if (!sourceList || sourceList.length === 0) {
      sourceContainer.innerHTML = '<p class="empty-state">暂无媒体源，请上传文件或添加本地路径。</p>';
      return;
    }

    const listHtml = sourceList.map((source) => {
      const availableButton = source.is_available
        ? `<button class="action-button action-button--primary action-button--small"
                   type="button" onclick="openSource(${source.id})">播放</button>`
        : '<span class="chip chip--neutral">不可用</span>';

      const truncatedUri = source.uri && source.uri.length > 60
        ? source.uri.substring(0, 60) + "…"
        : (source.uri || "");

      return `<li class="source-item" data-source-id="${source.id}">
        <div class="source-item__info">
          <span class="source-item__type chip chip--accent">${escapeHtml(source.source_type)}</span>
          <strong class="source-item__name">${escapeHtml(source.name)}</strong>
          <span class="source-item__uri" title="${escapeHtml(source.uri || "")}">${escapeHtml(truncatedUri)}</span>
        </div>
        <div class="source-item__actions">
          ${availableButton}
          <button class="action-button action-button--danger action-button--small"
                  type="button" onclick="removeSource(${source.id})">删除</button>
        </div>
      </li>`;
    }).join("");

    sourceContainer.innerHTML = `<ul class="source-list">${listHtml}</ul>`;
  }

  /**
   * 打开指定媒体源到播放区
   * @param {number} sourceId - MediaSource 主键
   */
  window.openSource = async function openSource(sourceId) {
    const openResult = await postAction("/playback/open/", { source_id: sourceId });
    if (openResult.success) {
      showBanner("已打开媒体源");
      if (openResult.session) {
        applySessionState(openResult.session);
      }
    } else {
      showBanner(openResult.error || "打开失败", true);
    }
  };

  /**
   * 删除指定媒体源
   * @param {number} sourceId - MediaSource 主键
   */
  window.removeSource = async function removeSource(sourceId) {
    const removeResult = await postAction("/sources/remove/", { source_id: sourceId });
    if (removeResult.success) {
      showBanner("已删除媒体源");
      refreshSources();
    } else {
      showBanner(removeResult.error || "删除失败", true);
    }
  };

  /* ── 上传表单处理 ── */

  const uploadForm = document.getElementById("upload-form");
  const uploadFileInput = document.getElementById("upload-file-input");
  const uploadNameRow = document.getElementById("upload-name-row");
  const uploadDropzone = uploadForm ? uploadForm.querySelector(".upload-dropzone") : null;

  if (uploadFileInput) {
    /* 选择文件后显示名称输入行 */
    uploadFileInput.addEventListener("change", () => {
      if (uploadFileInput.files.length > 0 && uploadNameRow) {
        uploadNameRow.style.display = "";
      }
    });
  }

  if (uploadForm) {
    uploadForm.addEventListener("submit", async (submitEvent) => {
      submitEvent.preventDefault();
      if (!uploadFileInput || uploadFileInput.files.length === 0) {
        showBanner("请先选择文件", true);
        return;
      }
      const formPayload = new FormData(uploadForm);
      const uploadResult = await postFormData("/sources/upload/", formPayload);
      if (uploadResult.success) {
        showBanner(`已上传「${uploadResult.source.name}」`);
        uploadForm.reset();
        if (uploadNameRow) uploadNameRow.style.display = "none";
        refreshSources();
      } else {
        showBanner(uploadResult.error || "上传失败", true);
      }
    });
  }

  /* 文件拖拽支持 */
  if (uploadDropzone) {
    uploadDropzone.addEventListener("dragover", (dragEvent) => {
      dragEvent.preventDefault();
      uploadDropzone.classList.add("upload-dropzone--dragover");
    });
    uploadDropzone.addEventListener("dragleave", () => {
      uploadDropzone.classList.remove("upload-dropzone--dragover");
    });
    uploadDropzone.addEventListener("drop", (dropEvent) => {
      dropEvent.preventDefault();
      uploadDropzone.classList.remove("upload-dropzone--dragover");
      if (dropEvent.dataTransfer.files.length > 0 && uploadFileInput) {
        uploadFileInput.files = dropEvent.dataTransfer.files;
        uploadFileInput.dispatchEvent(new Event("change"));
      }
    });
  }

  /* ── 本地路径表单处理 ── */

  const localPathForm = document.getElementById("local-path-form");
  if (localPathForm) {
    localPathForm.addEventListener("submit", async (submitEvent) => {
      submitEvent.preventDefault();
      const pathInput = localPathForm.querySelector('input[name="path"]');
      const nameInput = localPathForm.querySelector('input[name="name"]');
      const localPath = pathInput ? pathInput.value.trim() : "";
      if (!localPath) {
        showBanner("请输入文件路径", true);
        return;
      }
      const addResult = await postAction("/sources/add-local/", {
        path: localPath,
        name: nameInput ? nameInput.value.trim() : "",
      });
      if (addResult.success) {
        showBanner(`已添加「${addResult.source.name}」`);
        localPathForm.reset();
        refreshSources();
      } else {
        showBanner(addResult.error || "添加失败", true);
      }
    });
  }

  /* 源列表自动轮询（每 15 秒同步一次流状态） */
  setInterval(() => { refreshSources(); }, 15000);

  /* ═══════════════════════════════════════════════════════════
   * 播放控制
   * ═══════════════════════════════════════════════════════════ */

  /**
   * 发送播放控制指令（play / pause / stop）
   * @param {string} action - 控制动作
   */
  window.controlPlayback = async function controlPlayback(action) {
    const controlResult = await postAction("/playback/control/", { action });
    if (controlResult.success) {
      if (controlResult.session) {
        applySessionState(controlResult.session);
      }
    } else {
      showBanner(controlResult.error || "操作失败", true);
    }
  };

  /**
   * 关闭当前播放（停止播放并释放源）
   */
  window.closePlayback = async function closePlayback() {
    const closeResult = await postAction("/playback/close/");
    if (closeResult.success) {
      showBanner("已关闭播放");
      if (closeResult.session) {
        applySessionState(closeResult.session);
      }
    } else {
      showBanner(closeResult.error || "关闭失败", true);
    }
  };

  /**
   * 停止当前播放（toolbar 快捷操作，等价于 closePlayback）
   */
  window.stopPlayback = async function stopPlayback() {
    await closePlayback();
  };

  /* ═══════════════════════════════════════════════════════════
   * 内容导航（PPT 翻页 / 视频 Seek）
   * ═══════════════════════════════════════════════════════════ */

  /**
   * 发送内容导航指令（next / prev）
   * @param {string} action - 导航动作
   */
  window.navigateContent = async function navigateContent(action) {
    const navResult = await postAction("/playback/navigate/", { action });
    if (navResult.success) {
      if (navResult.session) {
        applySessionState(navResult.session);
      }
    } else {
      showBanner(navResult.error || "导航失败", true);
    }
  };

  /**
   * 跳转到指定页码（读取 goto-page-input 输入框）
   */
  window.gotoPage = async function gotoPage() {
    const pageInput = document.getElementById("goto-page-input");
    const targetPage = pageInput ? parseInt(pageInput.value, 10) : 0;
    if (!targetPage || targetPage < 1) {
      showBanner("请输入有效页码", true);
      return;
    }
    const gotoResult = await postAction("/playback/navigate/", {
      action: "goto",
      target_index: targetPage,
    });
    if (gotoResult.success) {
      if (gotoResult.session) {
        applySessionState(gotoResult.session);
      }
    } else {
      showBanner(gotoResult.error || "跳转失败", true);
    }
  };

  /* ── Seek 滑块处理 ── */

  const seekSlider = document.getElementById("seek-slider");
  /** Seek 操作节流锁 */
  let _seekThrottleTimer = null;

  if (seekSlider) {
    /* 用户拖拽滑块完成后发送 Seek 指令 */
    seekSlider.addEventListener("change", () => {
      clearTimeout(_seekThrottleTimer);
      _seekThrottleTimer = setTimeout(async () => {
        const sliderValue = parseInt(seekSlider.value, 10);
        const durationMs = parseInt(seekSlider.dataset.durationMs || "0", 10);
        if (durationMs <= 0) return;
        /* 将滑块百分比转换为毫秒位置 */
        const targetMs = Math.round((sliderValue / 1000) * durationMs);
        const seekResult = await postAction("/playback/navigate/", {
          action: "seek",
          position_ms: targetMs,
        });
        if (!seekResult.success) {
          showBanner(seekResult.error || "Seek 失败", true);
        }
      }, 200);
    });
  }

  /* ═══════════════════════════════════════════════════════════
   * 显示器切换
   * ═══════════════════════════════════════════════════════════ */

  /**
   * 切换显示模式或选择显示器
   * @param {string} displayMode - 显示模式
   * @param {string} targetDisplayName - 目标显示器名称
   */
  window.switchDisplay = async function switchDisplay(displayMode, targetDisplayName) {
    const switchResult = await postAction("/display/switch/", {
      display_mode: displayMode,
      target_display_name: targetDisplayName,
    });
    if (switchResult.success) {
      showBanner("已切换显示设置");
      if (switchResult.session) {
        applySessionState(switchResult.session);
      }
    } else {
      showBanner(switchResult.error || "切换失败", true);
    }
  };

  /* ═══════════════════════════════════════════════════════════
   * 状态更新（SSE 回调与手动触发）
   * ═══════════════════════════════════════════════════════════ */

  /**
   * 将会话快照应用到页面所有状态 DOM 元素
   * @param {object} sessionData - 来自 get_session_snapshot 的字典
   */
  function applySessionState(sessionData) {
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
    if (seekSlider && !seekSlider.matches(":active")) {
      seekSlider.dataset.durationMs = String(durationMs);
      if (durationMs > 0) {
        seekSlider.max = "1000";
        seekSlider.value = String(Math.round((positionMs / durationMs) * 1000));
      } else {
        seekSlider.value = "0";
      }
    }
  }

  /* ═══════════════════════════════════════════════════════════
   * SSE 实时事件流
   * ═══════════════════════════════════════════════════════════ */

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

  /** 建立 SSE 连接，处理事件和自动重连 */
  function connectSSE() {
    setSseStatus("SSE: 连接中…", "");
    const eventSource = new EventSource("/events/");

    eventSource.onopen = () => {
      setSseStatus("SSE: 已连接", "toolbar__status--connected");
    };

    /* 播放状态变更 → 更新整个面板 */
    eventSource.addEventListener("playback_state", (sseEvent) => {
      try {
        const statePayload = JSON.parse(sseEvent.data);
        applySessionState(statePayload);
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

  connectSSE();

  /** 刷新页面 */
  window.refreshPage = function refreshPage() {
    location.reload();
  };
});
