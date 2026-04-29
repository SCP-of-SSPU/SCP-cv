<script setup lang="ts">
import { computed } from 'vue';

import { formatBytes, formatDuration } from '@/services/api';
import { useAppStore } from '@/stores/app';

const appStore = useAppStore();
const onlineSources = computed(() => appStore.sources.filter((source) => source.is_available).length);
const activeWindows = computed(() => appStore.sessions.filter((session) => session.source_type).length);
const totalSourceSize = computed(() => appStore.sources.reduce((sum, source) => sum + (source.file_size || 0), 0));

async function runAction(action: () => Promise<void>): Promise<void> {
  try {
    await action();
  } catch (error) {
    appStore.notify(error instanceof Error ? error.message : '操作失败', true);
  }
}
</script>

<template>
  <section class="command-hero panel">
    <div>
      <span class="eyebrow">SCP-cv Command Deck</span>
      <h2>{{ appStore.bigScreenModeLabel }}运行 · {{ appStore.connectionStatus }}</h2>
      <p>媒体源、预案、四窗口播放和设备占位状态集中在此处。桌面端用于总控巡检，手机端保留 PPT 遥控优先路径。</p>
    </div>
    <div class="mode-switch" aria-label="大屏模式">
      <button type="button" :class="{ active: appStore.runtime?.big_screen_mode === 'single' }" @click="runAction(() => appStore.setBigScreenMode('single'))">Single</button>
      <button type="button" :class="{ active: appStore.runtime?.big_screen_mode === 'double' }" @click="runAction(() => appStore.setBigScreenMode('double'))">Double</button>
    </div>
  </section>

  <section class="metric-grid">
    <article class="metric-card">
      <span>在线源</span>
      <strong>{{ onlineSources }}</strong>
      <small>总计 {{ appStore.sources.length }} 个源</small>
    </article>
    <article class="metric-card">
      <span>活跃窗口</span>
      <strong>{{ activeWindows }}</strong>
      <small>窗口 3/4 固定静音</small>
    </article>
    <article class="metric-card">
      <span>预案</span>
      <strong>{{ appStore.scenarios.length }}</strong>
      <small>支持置顶与三态目标</small>
    </article>
    <article class="metric-card">
      <span>源文件体量</span>
      <strong>{{ formatBytes(totalSourceSize) }}</strong>
      <small>上传与本地文件合计</small>
    </article>
  </section>

  <section class="grid two">
    <article class="panel">
      <div class="panel__header">
        <h2>四窗口态势</h2>
        <button type="button" @click="runAction(appStore.refreshSessions)">刷新</button>
      </div>
      <div class="status-grid status-grid--compact">
        <button
          v-for="session in appStore.sessions"
          :key="session.window_id"
          type="button"
          class="status-card status-card--button"
          :class="{ active: appStore.activeWindowId === session.window_id }"
          @click="appStore.activeWindowId = session.window_id"
        >
          <strong>窗口 {{ session.window_id }}</strong>
          <span class="chip" :class="{ 'chip--accent': session.playback_state === 'playing' }">{{ session.playback_state_label }}</span>
          <small>{{ session.source_name }}</small>
          <small>{{ session.is_muted ? '静音' : `音量 ${session.volume}` }}</small>
        </button>
      </div>
    </article>

    <article class="panel">
      <div class="panel__header">
        <h2>设备占位</h2>
        <button type="button" @click="runAction(appStore.refreshDevices)">刷新</button>
      </div>
      <div class="device-grid">
        <article v-for="device in appStore.devices" :key="device.device_type" class="device-card" :class="{ active: device.is_powered_on }">
          <span>{{ device.device_type_label || device.name }}</span>
          <strong>{{ device.is_powered_on ? 'ON' : 'OFF' }}</strong>
          <button type="button" @click="runAction(() => appStore.toggleDevice(device.device_type))">切换</button>
        </article>
      </div>
    </article>
  </section>

  <section class="panel">
    <div class="panel__header">
      <h2>最近播放状态</h2>
      <small>当前窗口 {{ appStore.activeWindowId }}</small>
    </div>
    <div class="timeline-strip">
      <article v-for="session in appStore.sessions" :key="session.window_id">
        <span>W{{ session.window_id }}</span>
        <strong>{{ session.source_name }}</strong>
        <small v-if="session.total_slides">第 {{ session.current_slide }} / {{ session.total_slides }} 页</small>
        <small v-else>{{ formatDuration(session.position_ms) }} / {{ formatDuration(session.duration_ms) }}</small>
      </article>
    </div>
  </section>
</template>
