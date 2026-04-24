/**
 * SCP-cv 预案管理模块
 * 职责：预案 CRUD、激活预案、编辑器表单交互
 * 预案是窗口 1/2 播放配置的快照，支持独立双窗口和拼接两种模式。
 * 所有后端通信通过 gRPC-Web 完成。
 */

import {
  listScenarios,
  createScenario as grpcCreateScenario,
  updateScenario as grpcUpdateScenario,
  deleteScenario as grpcDeleteScenario,
  activateScenario as grpcActivateScenario,
} from "./grpc-client.bundle.js";

import { escapeHtml, showBanner, withLoading } from "./utils.js";

/* ═══════════════════════════════════════════════════════════
 * DOM 元素缓存
 * ═══════════════════════════════════════════════════════════ */

/** 预案列表容器 */
const scenarioListContainer = document.getElementById("scenario-list-container");
/** 预案数量徽章 */
const scenarioCountBadge = document.getElementById("scenario-count-badge");
/** 编辑器面板标题 */
const editorTitle = document.getElementById("scenario-editor-title");
/** 隐藏的编辑 ID（为空表示新建模式） */
const editIdInput = document.getElementById("scenario-edit-id");
/** 保存按钮 */
const saveBtn = document.getElementById("scenario-save-btn");

/* ═══════════════════════════════════════════════════════════
 * 拼接模式联动
 * ═══════════════════════════════════════════════════════════ */

/**
 * 拼接模式开关变化时显示/隐藏窗口 2 配置区
 */
export function onSpliceModeToggle() {
  const spliceCheckbox = document.getElementById("scenario-splice");
  const w2Fieldset = document.getElementById("scenario-w2-fieldset");
  if (spliceCheckbox && w2Fieldset) {
    w2Fieldset.style.display = spliceCheckbox.checked ? "none" : "";
  }
}

/* ═══════════════════════════════════════════════════════════
 * 预案 CRUD
 * ═══════════════════════════════════════════════════════════ */

/**
 * 保存预案（新建或更新）
 * 根据编辑器中的隐藏 ID 字段判断是创建还是更新。
 * @param {Event} triggerEvent - 点击事件
 */
export async function saveScenario(triggerEvent) {
  const scenarioName = document.getElementById("scenario-name").value.trim();
  if (!scenarioName) {
    showBanner("请输入预案名称", true);
    return;
  }

  const editId = editIdInput ? editIdInput.value : "";
  const isUpdate = editId !== "";

  /* 收集窗口配置 */
  const window1Config = {
    sourceId: parseInt(document.getElementById("scenario-w1-source").value || "0", 10),
    autoplay: document.getElementById("scenario-w1-autoplay").checked,
    resume: document.getElementById("scenario-w1-resume").checked,
  };
  const window2Config = {
    sourceId: parseInt(document.getElementById("scenario-w2-source").value || "0", 10),
    autoplay: document.getElementById("scenario-w2-autoplay").checked,
    resume: document.getElementById("scenario-w2-resume").checked,
  };

  const description = document.getElementById("scenario-desc").value.trim();
  const isSpliceMode = document.getElementById("scenario-splice").checked;

  await withLoading(triggerEvent, async () => {
    let reply;
    if (isUpdate) {
      reply = await grpcUpdateScenario(
        parseInt(editId, 10), scenarioName, description, isSpliceMode, window1Config, window2Config,
      );
    } else {
      reply = await grpcCreateScenario(
        scenarioName, description, isSpliceMode, window1Config, window2Config,
      );
    }
    const result = reply.toObject();
    if (result.success) {
      showBanner(`${isUpdate ? "更新" : "创建"}预案「${scenarioName}」成功`);
      resetScenarioForm();
      await refreshScenarioList();
    } else {
      showBanner(result.message || "保存失败", true);
    }
  });
}

/**
 * 删除指定预案
 * @param {number} scenarioId - 预案 ID
 * @param {Event} triggerEvent - 点击事件
 */
export async function deleteScenario(scenarioId, triggerEvent) {
  const { confirmAction } = await import("./utils.js");
  const confirmed = await confirmAction("确认删除", "确定要删除此预案吗？");
  if (!confirmed) return;

  await withLoading(triggerEvent, async () => {
    const reply = await grpcDeleteScenario(scenarioId);
    const result = reply.toObject();
    if (result.success) {
      showBanner("预案已删除");
      await refreshScenarioList();
    } else {
      showBanner(result.message || "删除失败", true);
    }
  });
}

/**
 * 激活指定预案：一键应用窗口配置
 * @param {number} scenarioId - 预案 ID
 * @param {Event} triggerEvent - 点击事件
 */
export async function activateScenario(scenarioId, triggerEvent) {
  await withLoading(triggerEvent, async () => {
    const reply = await grpcActivateScenario(scenarioId);
    const result = reply.toObject();
    if (result.success) {
      showBanner("预案已激活");
      /* 窗口状态更新通过 gRPC 流推送 */
    } else {
      showBanner(result.message || "激活失败", true);
    }
  });
}

/**
 * 进入编辑模式：通过 gRPC 获取预案详情并填充到编辑器表单
 * @param {number} scenarioId - 预案 ID
 */
export async function editScenario(scenarioId) {
  try {
    const reply = await listScenarios();
    const result = reply.toObject();
    if (!result.success) {
      showBanner("获取预案列表失败", true);
      return;
    }

    const scenario = (result.scenariosList || []).find((sc) => sc.id === scenarioId);
    if (!scenario) {
      showBanner("未找到该预案", true);
      return;
    }

    /* 填充表单 */
    if (editIdInput) editIdInput.value = String(scenario.id);
    document.getElementById("scenario-name").value = scenario.name || "";
    document.getElementById("scenario-desc").value = scenario.description || "";
    document.getElementById("scenario-splice").checked = !!scenario.isSpliceMode;

    /* 窗口配置 — gRPC 返回嵌套对象 window1/window2 */
    const w1 = scenario.window1 || {};
    document.getElementById("scenario-w1-source").value = String(w1.sourceId || "");
    document.getElementById("scenario-w1-autoplay").checked = w1.autoplay !== false;
    document.getElementById("scenario-w1-resume").checked = w1.resume !== false;

    const w2 = scenario.window2 || {};
    document.getElementById("scenario-w2-source").value = String(w2.sourceId || "");
    document.getElementById("scenario-w2-autoplay").checked = w2.autoplay !== false;
    document.getElementById("scenario-w2-resume").checked = w2.resume !== false;

    onSpliceModeToggle();

    /* 切换编辑器标题 */
    if (editorTitle) {
      editorTitle.innerHTML =
        '<svg viewBox="0 0 24 24" width="18" height="18" style="vertical-align:-3px;margin-right:6px;" aria-hidden="true"><path fill="currentColor" d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04a1.003 1.003 0 000-1.42l-2.34-2.34a1.003 1.003 0 00-1.42 0l-1.83 1.83 3.75 3.75 1.84-1.82z"/></svg>' +
        `编辑预案「${escapeHtml(scenario.name)}」`;
    }
    if (saveBtn) saveBtn.textContent = "更新预案";

    document.getElementById("scenario-editor-panel")?.scrollIntoView({ behavior: "smooth" });
  } catch (fetchErr) {
    showBanner("加载预案详情失败", true);
  }
}

/**
 * 重置编辑器表单到新建模式
 */
export function resetScenarioForm() {
  if (editIdInput) editIdInput.value = "";
  document.getElementById("scenario-name").value = "";
  document.getElementById("scenario-desc").value = "";
  document.getElementById("scenario-splice").checked = false;

  document.getElementById("scenario-w1-source").value = "";
  document.getElementById("scenario-w1-autoplay").checked = true;
  document.getElementById("scenario-w1-resume").checked = true;

  document.getElementById("scenario-w2-source").value = "";
  document.getElementById("scenario-w2-autoplay").checked = true;
  document.getElementById("scenario-w2-resume").checked = true;

  /* 恢复窗口 2 可见 */
  onSpliceModeToggle();

  /* 恢复编辑器标题和按钮文本 */
  if (editorTitle) {
    editorTitle.innerHTML =
      '<svg viewBox="0 0 24 24" width="18" height="18" style="vertical-align:-3px;margin-right:6px;" aria-hidden="true"><path fill="currentColor" d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04a1.003 1.003 0 000-1.42l-2.34-2.34a1.003 1.003 0 00-1.42 0l-1.83 1.83 3.75 3.75 1.84-1.82z"/></svg>' +
      "新建预案";
  }
  if (saveBtn) saveBtn.textContent = "保存预案";
}

/* ═══════════════════════════════════════════════════════════
 * 列表刷新
 * ═══════════════════════════════════════════════════════════ */

/**
 * 通过 gRPC 拉取最新预案列表并刷新 DOM
 */
export async function refreshScenarioList() {
  try {
    const reply = await listScenarios();
    const result = reply.toObject();
    if (!result.success || !scenarioListContainer) return;

    const scenarios = result.scenariosList || [];

    /* 更新徽章计数 */
    if (scenarioCountBadge) {
      scenarioCountBadge.textContent = `${scenarios.length} 个`;
    }

    /* 渲染列表 */
    if (scenarios.length === 0) {
      scenarioListContainer.innerHTML = '<p class="empty-hint">暂无预案，点击下方按钮创建</p>';
      return;
    }

    scenarioListContainer.innerHTML = scenarios.map((sc) => {
      const modeLabel = sc.isSpliceMode ? "拼接" : "独立";
      const modeClass = sc.isSpliceMode ? "chip--accent" : "chip--neutral";
      /* gRPC 不返回 source_name，只返回 sourceId；显示 ID */
      const w1 = sc.window1 || {};
      const w2 = sc.window2 || {};
      const w1Label = w1.sourceId ? `源 #${w1.sourceId}` : "无";
      const w2Section = sc.isSpliceMode ? "" : ` · W2: ${w2.sourceId ? `源 #${w2.sourceId}` : "无"}`;
      const descHtml = sc.description
        ? `<small class="source-row__description">${escapeHtml(sc.description)}</small>`
        : "";

      return `
        <div class="source-row" data-scenario-id="${sc.id}">
          <div class="source-row__info">
            <strong>${escapeHtml(sc.name)}</strong>
            <span class="chip ${modeClass}">${modeLabel}</span>
            ${descHtml}
            <small class="source-row__meta">W1: ${w1Label}${w2Section}</small>
          </div>
          <div class="source-row__actions">
            <button class="action-button action-button--small action-button--primary"
                    data-action="activate-scenario" data-scenario-id="${sc.id}" title="激活预案">▶ 激活</button>
            <button class="action-button action-button--small"
                    data-action="edit-scenario" data-scenario-id="${sc.id}" title="编辑预案">✎ 编辑</button>
            <button class="action-button action-button--small action-button--danger"
                    data-action="delete-scenario" data-scenario-id="${sc.id}" title="删除预案">✕</button>
          </div>
        </div>`;
    }).join("");
  } catch (fetchErr) {
    showBanner("刷新预案列表失败", true);
  }
}
