<script setup lang="ts">
import { computed, ref } from 'vue';

import { api, formatDuration } from '@/services/api';
import { useAppStore } from '@/stores/app';

const appStore = useAppStore();
const selectedDisplay = ref('');
const systemVolume = computed(() => appStore.systemVolumeLevel);

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

async function setSystemVolume(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement;
  await appStore.setSystemVolume(Number(input.value));
}
</script>

<template>
  <section class="grid two">
    <article class="panel">
      <span class="eyebrow">Runtime</span>
      <h2>运行状态</h2>
      <p>前端通信：REST API</p>
      <p>状态通道：{{ appStore.connectionStatus }}</p>
      <p>大屏模式：{{ appStore.bigScreenModeLabel }}</p>
      <div class="mode-switch">
        <button type="button" :class="{ active: appStore.runtime?.big_screen_mode === 'single' }" @click="runAction(() => appStore.setBigScreenMode('single'))">Single</button>
        <button type="button" :class="{ active: appStore.runtime?.big_screen_mode === 'double' }" @click="runAction(() => appStore.setBigScreenMode('double'))">Double</button>
      </div>
      <label>系统音量 {{ systemVolume }}
        <input type="range" min="0" max="100" :value="systemVolume" @change="runAction(() => setSystemVolume($event))" />
      </label>
    </article>

    <article class="panel">
      <span class="eyebrow">Displays</span>
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
  </section>

  <section class="panel">
    <div class="panel__header">
      <h2>设备电源</h2>
      <button type="button" @click="runAction(appStore.refreshDevices)">刷新</button>
    </div>
    <div class="device-grid device-grid--wide">
      <article v-for="device in appStore.devices" :key="device.device_type" class="device-card" :class="{ active: device.is_powered_on }">
        <span>{{ device.device_type_label || device.name }}</span>
        <strong>{{ device.is_powered_on ? 'ON' : 'OFF' }}</strong>
        <div class="row-actions">
          <button v-if="device.device_type === 'splice_screen'" type="button" @click="runAction(() => appStore.powerDevice(device.device_type, 'on'))">开机</button>
          <button v-if="device.device_type === 'splice_screen'" type="button" class="danger" @click="runAction(() => appStore.powerDevice(device.device_type, 'off'))">关机</button>
          <button v-else type="button" @click="runAction(() => appStore.toggleDevice(device.device_type))">切换</button>
        </div>
      </article>
    </div>
  </section>

  <section class="panel">
    <div class="panel__header">
      <h2>窗口状态</h2>
      <button type="button" @click="runAction(appStore.refreshSessions)">刷新</button>
    </div>
    <div class="status-grid">
      <article v-for="session in appStore.sessions" :key="session.window_id" class="status-card">
        <strong>窗口 {{ session.window_id }}</strong>
        <span class="chip" :class="{ 'chip--accent': session.playback_state === 'playing' }">{{ session.playback_state_label }}</span>
        <p>{{ session.source_name }}</p>
        <small v-if="session.total_slides">第 {{ session.current_slide }} / {{ session.total_slides }} 页</small>
        <small v-else>{{ formatDuration(session.position_ms) }} / {{ formatDuration(session.duration_ms) }}</small>
        <small>{{ session.is_muted ? '静音' : `音量 ${session.volume}` }}</small>
      </article>
    </div>
  </section>
</template>
