<script setup lang="ts">
import { reactive, ref } from 'vue';

import { api, type ScenarioItem } from '@/services/api';
import { useAppStore } from '@/stores/app';

const appStore = useAppStore();
const editingId = ref<number | null>(null);
const form = reactive({
  name: '',
  description: '',
  window1_source_id: 0,
  window1_autoplay: true,
  window1_resume: true,
  window2_source_id: 0,
  window2_autoplay: true,
  window2_resume: true,
});

async function runAction(action: () => Promise<void>): Promise<void> {
  try {
    await action();
  } catch (error) {
    appStore.notify(error instanceof Error ? error.message : '操作失败', true);
  }
}

function resetForm(): void {
  editingId.value = null;
  form.name = '';
  form.description = '';
  form.window1_source_id = 0;
  form.window1_autoplay = true;
  form.window1_resume = true;
  form.window2_source_id = 0;
  form.window2_autoplay = true;
  form.window2_resume = true;
}

function editScenario(scenario: ScenarioItem): void {
  editingId.value = scenario.id;
  form.name = scenario.name;
  form.description = scenario.description;
  form.window1_source_id = scenario.window1_source_id || 0;
  form.window1_autoplay = scenario.window1_autoplay;
  form.window1_resume = scenario.window1_resume;
  form.window2_source_id = scenario.window2_source_id || 0;
  form.window2_autoplay = scenario.window2_autoplay;
  form.window2_resume = scenario.window2_resume;
}

async function saveScenario(): Promise<void> {
  if (!form.name.trim()) {
    appStore.notify('请输入预案名称', true);
    return;
  }
  const payload = { ...form };
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
  appStore.notify('预案已激活');
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
</script>

<template>
  <section class="grid two">
    <article class="panel">
      <h2>{{ editingId ? '编辑预案' : '创建预案' }}</h2>
      <input v-model="form.name" placeholder="预案名称" />
      <textarea v-model="form.description" placeholder="描述"></textarea>
      <label>窗口 1 源
        <select v-model.number="form.window1_source_id">
          <option :value="0">无</option>
          <option v-for="source in appStore.availableSources" :key="source.id" :value="source.id">{{ source.name }}</option>
        </select>
      </label>
      <label>窗口 2 源
        <select v-model.number="form.window2_source_id">
          <option :value="0">无</option>
          <option v-for="source in appStore.availableSources" :key="source.id" :value="source.id">{{ source.name }}</option>
        </select>
      </label>
      <div class="button-grid">
        <button type="button" @click="runAction(saveScenario)">保存</button>
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
        <li v-for="scenario in appStore.scenarios" :key="scenario.id" class="source-card">
          <div>
            <strong>{{ scenario.name }}</strong>
            <small>{{ scenario.description || '无描述' }}</small>
            <small>窗口1：{{ scenario.window1_source_name || '无' }} · 窗口2：{{ scenario.window2_source_name || '无' }}</small>
          </div>
          <div class="row-actions">
            <button type="button" @click="runAction(() => activateScenario(scenario.id))">激活</button>
            <button type="button" @click="editScenario(scenario)">编辑</button>
            <button type="button" class="danger" @click="runAction(() => deleteScenario(scenario.id))">删除</button>
          </div>
        </li>
      </ul>
    </article>
  </section>
</template>
