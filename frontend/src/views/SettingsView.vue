<script setup lang="ts">
import { ref } from 'vue';

import { api, formatDuration } from '@/services/api';
import { useAppStore } from '@/stores/app';

const appStore = useAppStore();
const selectedDisplay = ref('');

async function runAction(action: () => Promise<void>): Promise<void> {
  try {
    await action();
  } catch (error) {
    appStore.notify(error instanceof Error ? error.message : '操作失败', true);
  }
}

async function selectDisplay(): Promise<void> {
  const payload = {
    window_id: appStore.activeWindowId,
    display_mode: 'single',
    target_label: selectedDisplay.value,
  };
  const state = await api.selectDisplay(payload);
  appStore.applySessions(state.sessions);
  appStore.notify('显示目标已切换');
}
</script>

<template>
  <section class="grid two">
    <article class="panel">
      <h2>显示器目标</h2>
      <select v-model="selectedDisplay">
        <option value="">选择显示器</option>
        <option v-for="display in appStore.displays" :key="display.index" :value="display.name">
          {{ display.name }} · {{ display.width }}×{{ display.height }} · ({{ display.x }}, {{ display.y }})
        </option>
      </select>
      <button type="button" @click="runAction(selectDisplay)">应用到窗口 {{ appStore.activeWindowId }}</button>
      <button type="button" @click="runAction(appStore.refreshDisplays)">刷新显示器</button>
    </article>

    <article class="panel">
      <h2>运行状态</h2>
      <p>前端通信：REST API</p>
      <p>状态通道：{{ appStore.connectionStatus }}</p>
    </article>
  </section>

  <section class="panel">
    <div class="panel__header">
      <h2>窗口状态</h2>
      <button type="button" @click="runAction(appStore.refreshSessions)">刷新</button>
    </div>
    <div class="status-grid">
      <article v-for="session in appStore.sessions" :key="session.window_id" class="status-card">
        <strong>窗口 {{ session.window_id }}</strong>
        <span class="chip">{{ session.playback_state_label }}</span>
        <p>{{ session.source_name }}</p>
        <small v-if="session.total_slides">第 {{ session.current_slide }} / {{ session.total_slides }} 页</small>
        <small v-else>{{ formatDuration(session.position_ms) }} / {{ formatDuration(session.duration_ms) }}</small>
      </article>
    </div>
  </section>
</template>
