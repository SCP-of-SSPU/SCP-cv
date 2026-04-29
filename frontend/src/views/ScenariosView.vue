<script setup lang="ts">
import { reactive, ref } from 'vue';

import { api, type ScenarioItem, type ScenarioPayload } from '@/services/api';
import { useAppStore } from '@/stores/app';

type SourceState = 'unset' | 'empty' | 'set';

interface TargetForm {
  window_id: number;
  source_state: SourceState;
  source_id: number;
  autoplay: boolean;
  resume: boolean;
}

const appStore = useAppStore();
const editingId = ref<number | null>(null);
const form = reactive({
  name: '',
  description: '',
  big_screen_mode_state: 'unset' as SourceState,
  big_screen_mode: 'single' as 'single' | 'double',
  volume_state: 'unset' as SourceState,
  volume_level: 100,
  targets: [1, 2, 3, 4].map((windowId) => ({
    window_id: windowId,
    source_state: 'unset' as SourceState,
    source_id: 0,
    autoplay: true,
    resume: true,
  })) as TargetForm[],
});

async function runAction(action: () => Promise<void>): Promise<void> {
  try {
    await action();
  } catch (error) {
    appStore.notify(error instanceof Error ? error.message : '操作失败', true);
  }
}

function resetTargets(): void {
  form.targets.forEach((target) => {
    target.source_state = 'unset';
    target.source_id = 0;
    target.autoplay = true;
    target.resume = true;
  });
}

function resetForm(): void {
  editingId.value = null;
  form.name = '';
  form.description = '';
  form.big_screen_mode_state = 'unset';
  form.big_screen_mode = 'single';
  form.volume_state = 'unset';
  form.volume_level = 100;
  resetTargets();
}

function editScenario(scenario: ScenarioItem): void {
  editingId.value = scenario.id;
  form.name = scenario.name;
  form.description = scenario.description;
  form.big_screen_mode_state = scenario.big_screen_mode_state;
  form.big_screen_mode = scenario.big_screen_mode;
  form.volume_state = scenario.volume_state;
  form.volume_level = scenario.volume_level;
  resetTargets();
  scenario.targets.forEach((scenarioTarget) => {
    const target = form.targets.find((item) => item.window_id === scenarioTarget.window_id);
    if (!target) return;
    target.source_state = scenarioTarget.source_state;
    target.source_id = scenarioTarget.source_id || 0;
    target.autoplay = scenarioTarget.autoplay;
    target.resume = scenarioTarget.resume;
  });
}

function buildPayload(): ScenarioPayload {
  return {
    name: form.name.trim(),
    description: form.description,
    big_screen_mode_state: form.big_screen_mode_state,
    big_screen_mode: form.big_screen_mode,
    volume_state: form.volume_state,
    volume_level: Number(form.volume_level),
    targets: form.targets.map((target) => ({
      window_id: target.window_id,
      source_state: target.source_state,
      source_id: target.source_state === 'set' ? target.source_id : null,
      autoplay: target.autoplay,
      resume: target.resume,
    })),
  };
}

async function saveScenario(): Promise<void> {
  if (!form.name.trim()) {
    appStore.notify('请输入预案名称', true);
    return;
  }
  const payload = buildPayload();
  if (editingId.value) {
    await api.updateScenario(editingId.value, payload);
  } else {
    await api.createScenario(payload);
  }
  resetForm();
  await appStore.refreshScenarios();
  appStore.notify('预案已保存');
}

async function deleteScenario(scenarioId: number): Promise<void> {
  if (!window.confirm('确定删除该预案吗？')) return;
  await api.deleteScenario(scenarioId);
  await appStore.refreshScenarios();
  appStore.notify('预案已删除');
}

async function activateScenario(scenarioId: number): Promise<void> {
  const payload = await api.activateScenario(scenarioId);
  appStore.applySessions(payload.sessions);
  await appStore.refreshRuntime();
  appStore.notify('预案已激活');
}

async function pinScenario(scenarioId: number): Promise<void> {
  await api.pinScenario(scenarioId);
  await appStore.refreshScenarios();
  appStore.notify('预案已置顶');
}

async function captureCurrent(): Promise<void> {
  if (!form.name.trim()) {
    appStore.notify('请先填写预案名称', true);
    return;
  }
  await api.captureScenario({ name: form.name, description: form.description, scenario_id: editingId.value || 0 });
  resetForm();
  await appStore.refreshScenarios();
  appStore.notify('已保存当前状态');
}

function targetSummary(scenario: ScenarioItem, windowId: number): string {
  const target = scenario.targets.find((item) => item.window_id === windowId);
  if (!target || target.source_state === 'unset') return '保持';
  if (target.source_state === 'empty') return '黑屏';
  return target.source_name || '未命名源';
}
</script>

<template>
  <section class="scenario-shell">
    <article class="panel scenario-editor">
      <span class="eyebrow">Scenario Matrix</span>
      <h2>{{ editingId ? '编辑预案' : '创建预案' }}</h2>
      <input v-model="form.name" placeholder="预案名称" />
      <textarea v-model="form.description" placeholder="描述"></textarea>

      <div class="grid two scenario-rules">
        <label>大屏模式
          <select v-model="form.big_screen_mode_state">
            <option value="unset">保持不变</option>
            <option value="set">设置模式</option>
          </select>
        </label>
        <label>模式值
          <select v-model="form.big_screen_mode" :disabled="form.big_screen_mode_state !== 'set'">
            <option value="single">Single</option>
            <option value="double">Double</option>
          </select>
        </label>
        <label>音量策略
          <select v-model="form.volume_state">
            <option value="unset">保持不变</option>
            <option value="set">设置音量</option>
          </select>
        </label>
        <label>系统音量 {{ form.volume_level }}
          <input v-model.number="form.volume_level" type="range" min="0" max="100" :disabled="form.volume_state !== 'set'" />
        </label>
      </div>

      <div class="target-matrix">
        <article v-for="target in form.targets" :key="target.window_id" class="target-card">
          <strong>窗口 {{ target.window_id }}</strong>
          <select v-model="target.source_state">
            <option value="unset">保持</option>
            <option value="empty">黑屏</option>
            <option value="set">打开源</option>
          </select>
          <select v-model.number="target.source_id" :disabled="target.source_state !== 'set'">
            <option :value="0">选择源</option>
            <option v-for="source in appStore.availableSources" :key="source.id" :value="source.id">{{ source.name }}</option>
          </select>
          <label class="checkbox-line"><input v-model="target.autoplay" type="checkbox" :disabled="target.source_state !== 'set'" /> 自动播放</label>
          <label class="checkbox-line"><input v-model="target.resume" type="checkbox" :disabled="target.source_state !== 'set'" /> 保留进度</label>
        </article>
      </div>

      <div class="button-grid">
        <button type="button" @click="runAction(saveScenario)">保存预案</button>
        <button type="button" @click="runAction(captureCurrent)">保存当前状态</button>
        <button type="button" @click="resetForm">重置</button>
      </div>
    </article>

    <article class="panel">
      <div class="panel__header">
        <h2>预案列表</h2>
        <button type="button" @click="runAction(appStore.refreshScenarios)">刷新</button>
      </div>
      <ul class="scenario-list">
        <li v-for="scenario in appStore.scenarios" :key="scenario.id" class="source-card source-card--rich">
          <div>
            <span class="chip" :class="{ 'chip--accent': scenario.sort_order > 0 }">{{ scenario.sort_order > 0 ? '置顶' : '预案' }}</span>
            <strong>{{ scenario.name }}</strong>
            <small>{{ scenario.description || '无描述' }}</small>
            <small>W1 {{ targetSummary(scenario, 1) }} · W2 {{ targetSummary(scenario, 2) }} · W3 {{ targetSummary(scenario, 3) }} · W4 {{ targetSummary(scenario, 4) }}</small>
            <small>大屏 {{ scenario.big_screen_mode_state === 'set' ? scenario.big_screen_mode : '保持' }} · 音量 {{ scenario.volume_state === 'set' ? scenario.volume_level : '保持' }}</small>
          </div>
          <div class="row-actions">
            <button type="button" @click="runAction(() => activateScenario(scenario.id))">激活</button>
            <button type="button" @click="editScenario(scenario)">编辑</button>
            <button type="button" @click="runAction(() => pinScenario(scenario.id))">置顶</button>
            <button type="button" class="danger" @click="runAction(() => deleteScenario(scenario.id))">删除</button>
          </div>
        </li>
      </ul>
    </article>
  </section>
</template>
