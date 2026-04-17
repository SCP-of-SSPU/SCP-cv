/**
 * SCP-cv 预案管理模块
 * 职责：预案 CRUD、激活预案、编辑器表单交互
 * 预案是窗口 1/2 播放配置的快照，支持独立双窗口和拼接两种模式。
 */

import { postAction, showBanner, withLoading } from "./utils.js";

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
 * 从编辑器表单中收集预案配置参数
 * @returns {FormData} 包含所有预案字段的表单数据
 */
function collectFormData() {
  const formData = new FormData();
  formData.append("name", document.getElementById("scenario-name").value.trim());
  formData.append("description", document.getElementById("scenario-desc").value.trim());
  formData.append("is_splice_mode", document.getElementById("scenario-splice").checked ? "true" : "false");

  /* 窗口 1 配置 */
  formData.append("window1_source_id", document.getElementById("scenario-w1-source").value || "0");
  formData.append("window1_autoplay", document.getElementById("scenario-w1-autoplay").checked ? "true" : "false");
  formData.append("window1_resume", document.getElementById("scenario-w1-resume").checked ? "true" : "false");

  /* 窗口 2 配置 */
  formData.append("window2_source_id", document.getElementById("scenario-w2-source").value || "0");
  formData.append("window2_autoplay", document.getElementById("scenario-w2-autoplay").checked ? "true" : "false");
  formData.append("window2_resume", document.getElementById("scenario-w2-resume").checked ? "true" : "false");

  return formData;
}

/**
 * 保存预案（新建或更新）
 * 根据编辑器中的隐藏 ID 字段判断是创建还是更新。
 * @param {Event} event - 点击事件
 */
export async function saveScenario(event) {
  const scenarioName = document.getElementById("scenario-name").value.trim();
  if (!scenarioName) {
    showBanner("请输入预案名称", "warning");
    return;
  }

  const editId = editIdInput ? editIdInput.value : "";
  const isUpdate = editId !== "";
  const actionUrl = isUpdate
    ? `/scenarios/${editId}/update/`
    : "/scenarios/create/";

  const formData = collectFormData();
  const actionLabel = isUpdate ? "更新预案" : "创建预案";

  await withLoading(event?.currentTarget, async () => {
    const result = await postAction(actionUrl, formData);
    if (result?.success) {
      showBanner(`${actionLabel}「${scenarioName}」成功`, "success");
      resetScenarioForm();
      /* 刷新预案列表 */
      await refreshScenarioList();
    }
  });
}

/**
 * 删除指定预案
 * @param {number} scenarioId - 预案 ID
 * @param {Event} event - 点击事件
 */
export async function deleteScenario(scenarioId, event) {
  if (!confirm("确定要删除此预案吗？")) return;

  await withLoading(event?.currentTarget, async () => {
    const result = await postAction(`/scenarios/${scenarioId}/delete/`);
    if (result?.success) {
      showBanner("预案已删除", "success");
      await refreshScenarioList();
    }
  });
}

/**
 * 激活指定预案：一键应用窗口配置
 * @param {number} scenarioId - 预案 ID
 * @param {Event} event - 点击事件
 */
export async function activateScenario(scenarioId, event) {
  await withLoading(event?.currentTarget, async () => {
    const result = await postAction(`/scenarios/${scenarioId}/activate/`);
    if (result?.success) {
      showBanner("预案已激活", "success");
    }
  });
}

/**
 * 进入编辑模式：从服务器获取预案详情并填充到编辑器表单
 * @param {number} scenarioId - 预案 ID
 */
export async function editScenario(scenarioId) {
  try {
    const response = await fetch(`/api/scenarios/`);
    const data = await response.json();
    if (!data.success) {
      showBanner("获取预案列表失败", "danger");
      return;
    }

    /* 从列表中找到目标预案 */
    const scenario = data.scenarios.find(
      (sc) => sc.id === scenarioId
    );
    if (!scenario) {
      showBanner("未找到该预案", "danger");
      return;
    }

    /* 填充表单 */
    if (editIdInput) editIdInput.value = String(scenario.id);
    document.getElementById("scenario-name").value = scenario.name || "";
    document.getElementById("scenario-desc").value = scenario.description || "";
    document.getElementById("scenario-splice").checked = !!scenario.is_splice_mode;

    document.getElementById("scenario-w1-source").value = String(scenario.window1_source_id || "");
    document.getElementById("scenario-w1-autoplay").checked = scenario.window1_autoplay !== false;
    document.getElementById("scenario-w1-resume").checked = scenario.window1_resume !== false;

    document.getElementById("scenario-w2-source").value = String(scenario.window2_source_id || "");
    document.getElementById("scenario-w2-autoplay").checked = scenario.window2_autoplay !== false;
    document.getElementById("scenario-w2-resume").checked = scenario.window2_resume !== false;

    /* 联动拼接模式显示/隐藏窗口 2 */
    onSpliceModeToggle();

    /* 切换编辑器标题和按钮文本 */
    if (editorTitle) {
      editorTitle.innerHTML =
        '<svg viewBox="0 0 24 24" width="18" height="18" style="vertical-align:-3px;margin-right:6px;" aria-hidden="true"><path fill="currentColor" d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04a1.003 1.003 0 000-1.42l-2.34-2.34a1.003 1.003 0 00-1.42 0l-1.83 1.83 3.75 3.75 1.84-1.82z"/></svg>' +
        `编辑预案「${scenario.name}」`;
    }
    if (saveBtn) saveBtn.textContent = "更新预案";

    /* 滚动到编辑器 */
    document.getElementById("scenario-editor-panel")?.scrollIntoView({ behavior: "smooth" });
  } catch (fetchErr) {
    showBanner("加载预案详情失败", "danger");
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
 * 从服务器拉取最新预案列表并刷新 DOM
 */
export async function refreshScenarioList() {
  try {
    const response = await fetch("/api/scenarios/");
    const data = await response.json();
    if (!data.success || !scenarioListContainer) return;

    const scenarios = data.scenarios || [];

    /* 更新徽章计数 */
    if (scenarioCountBadge) {
      scenarioCountBadge.textContent = `${scenarios.length} 个`;
    }

    /* 渲染列表 */
    if (scenarios.length === 0) {
      scenarioListContainer.innerHTML =
        '<p class="empty-hint">暂无预案，点击下方按钮创建</p>';
      return;
    }

    scenarioListContainer.innerHTML = scenarios
      .map((sc) => {
        const modeLabel = sc.is_splice_mode ? "拼接" : "独立";
        const modeClass = sc.is_splice_mode ? "chip--accent" : "chip--neutral";
        const w1Label = sc.window1_source_name || "无";
        const w2Section = sc.is_splice_mode
          ? ""
          : ` · W2: ${sc.window2_source_name || "无"}`;
        const descHtml = sc.description
          ? `<small style="display:block;opacity:.7;margin-top:2px;">${sc.description}</small>`
          : "";

        return `
          <div class="source-row" data-scenario-id="${sc.id}">
            <div class="source-row__info">
              <strong>${sc.name}</strong>
              <span class="chip ${modeClass}">${modeLabel}</span>
              ${descHtml}
              <small style="display:block;opacity:.5;margin-top:2px;">W1: ${w1Label}${w2Section}</small>
            </div>
            <div class="source-row__actions">
              <button class="action-button action-button--small action-button--primary"
                      onclick="activateScenario(${sc.id}, event)" title="激活预案">▶ 激活</button>
              <button class="action-button action-button--small"
                      onclick="editScenario(${sc.id})" title="编辑预案">✎ 编辑</button>
              <button class="action-button action-button--small action-button--danger"
                      onclick="deleteScenario(${sc.id}, event)" title="删除预案">✕</button>
            </div>
          </div>`;
      })
      .join("");
  } catch (fetchErr) {
    showBanner("刷新预案列表失败", "danger");
  }
}
