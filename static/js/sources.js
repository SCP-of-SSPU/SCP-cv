/**
 * SCP-cv 媒体源管理模块
 * 职责：源列表刷新与渲染、打开/删除源、文件上传、本地路径添加、网页 URL 添加
 */

import { postAction, postFormData, showBanner, escapeHtml, withLoading } from "./utils.js";
import { getActiveWindowId, applyWindowSession } from "./windows.js";

/* ═══════════════════════════════════════════════════════════
 * 源列表
 * ═══════════════════════════════════════════════════════════ */

/** 防止并发的源列表刷新锁 */
let _sourceSyncInFlight = false;

/**
 * 刷新媒体源列表，从 API 拉取最新数据并重新渲染
 */
export async function refreshSources() {
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
    /* 网络异常静默处理，避免轮询时大量报错 */
  } finally {
    _sourceSyncInFlight = false;
  }
}

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

  /* 空状态：友好提示 + 图标 */
  if (!sourceList || sourceList.length === 0) {
    sourceContainer.innerHTML = `
      <div class="empty-state">
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M13 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V9l-7-7zm-1 2.5L17.5 10H13V4.5zM6 20V4h5v7h7v9H6z"/></svg>
        <span>暂无媒体源，请上传文件或添加本地路径。</span>
      </div>`;
    return;
  }

  const listHtml = sourceList.map((source) => {
    /* 可用的源显示播放按钮，不可用的显示灰色徽标 */
    const availableButton = source.is_available
      ? `<button class="action-button action-button--primary action-button--small"
                 type="button" onclick="openSource(${source.id}, event)"
                 aria-label="播放 ${escapeHtml(source.name)}">
           <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 5v14l11-7z"/></svg>
           播放
         </button>`
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
                type="button" onclick="removeSource(${source.id}, event)"
                aria-label="删除 ${escapeHtml(source.name)}">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/></svg>
          删除
        </button>
      </div>
    </li>`;
  }).join("");

  sourceContainer.innerHTML = `<ul class="source-list">${listHtml}</ul>`;
}

/* ═══════════════════════════════════════════════════════════
 * 打开 / 删除媒体源
 * ═══════════════════════════════════════════════════════════ */

/**
 * 打开指定媒体源到当前活跃窗口
 * @param {number} sourceId - MediaSource 主键
 * @param {Event} triggerEvent - 触发事件
 */
export async function openSource(sourceId, triggerEvent) {
  await withLoading(triggerEvent, async () => {
    const openResult = await postAction(
      `/playback/${getActiveWindowId()}/open/`,
      { source_id: sourceId },
    );
    if (openResult.success) {
      showBanner("已打开媒体源");
      if (openResult.session) {
        applyWindowSession(getActiveWindowId(), openResult.session);
      }
    } else {
      showBanner(openResult.error || "打开失败", true);
    }
  });
}

/**
 * 删除指定媒体源（带确认弹窗）
 * @param {number} sourceId - MediaSource 主键
 * @param {Event} triggerEvent - 触发事件
 */
export async function removeSource(sourceId, triggerEvent) {
  /* 延迟导入避免循环依赖 */
  const { confirmAction } = await import("./utils.js");
  const confirmed = await confirmAction(
    "确认删除",
    "删除后无法恢复，确定要删除该媒体源吗？",
  );
  if (!confirmed) return;

  await withLoading(triggerEvent, async () => {
    const removeResult = await postAction("/sources/remove/", { source_id: sourceId });
    if (removeResult.success) {
      showBanner("已删除媒体源");
      refreshSources();
    } else {
      showBanner(removeResult.error || "删除失败", true);
    }
  });
}

/* ═══════════════════════════════════════════════════════════
 * 表单初始化（上传、本地路径、网页 URL）
 * ═══════════════════════════════════════════════════════════ */

/**
 * 初始化媒体源相关的所有表单事件绑定
 */
export function initSourceForms() {
  /* ── 上传表单 ── */
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

      const submitButton = uploadForm.querySelector('button[type="submit"]');
      await withLoading(submitButton, async () => {
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

  /* ── 本地路径表单 ── */
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

      const submitButton = localPathForm.querySelector('button[type="submit"]');
      await withLoading(submitButton, async () => {
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
    });
  }

  /* ── 网页 URL 添加表单 ── */
  const webUrlForm = document.getElementById("web-url-form");
  if (webUrlForm) {
    webUrlForm.addEventListener("submit", async (submitEvent) => {
      submitEvent.preventDefault();
      const urlInput = webUrlForm.querySelector('input[name="url"]');
      const nameInput = webUrlForm.querySelector('input[name="name"]');
      const webUrl = urlInput ? urlInput.value.trim() : "";
      if (!webUrl) {
        showBanner("请输入网页 URL", true);
        return;
      }

      const submitButton = webUrlForm.querySelector('button[type="submit"]');
      await withLoading(submitButton, async () => {
        const addResult = await postAction("/sources/add-web/", {
          url: webUrl,
          name: nameInput ? nameInput.value.trim() : "",
        });
        if (addResult.success) {
          showBanner(`已添加「${addResult.source.name}」`);
          webUrlForm.reset();
          refreshSources();
        } else {
          showBanner(addResult.error || "添加失败", true);
        }
      });
    });
  }
}
