<script setup lang="ts">
import { computed, ref } from 'vue';

import { api, formatBytes } from '@/services/api';
import { useAppStore } from '@/stores/app';

const appStore = useAppStore();
const uploadFile = ref<File | null>(null);
const uploadName = ref('');
const uploadProgress = ref(0);
const isUploading = ref(false);

const onlineSources = computed(() => appStore.sources.filter((source) => source.is_available).length);
const activeWindows = computed(() => appStore.sessions.filter((session) => session.source_type).length);
const totalSourceSize = computed(() => appStore.sources.reduce((sum, source) => sum + (source.file_size || 0), 0));
const pinnedScenarios = computed(() => appStore.scenarios.slice(0, 6));

async function runAction(action: () => Promise<void>): Promise<void> {
  try {
    await action();
  } catch (error) {
    appStore.notify(error instanceof Error ? error.message : '操作失败', true);
  }
}

function onFileSelected(event: Event): void {
  const input = event.target as HTMLInputElement;
  uploadFile.value = input.files?.[0] || null;
}

async function uploadAndSave(): Promise<void> {
  if (!uploadFile.value) {
    appStore.notify('请先选择文件', true);
    return;
  }
  const formData = new FormData();
  formData.append('file', uploadFile.value);
  if (uploadName.value.trim()) formData.append('name', uploadName.value.trim());
  isUploading.value = true;
  uploadProgress.value = 0;
  try {
    await api.uploadSource(formData, {
      onProgress: (percent) => {
        uploadProgress.value = percent;
      },
    });
    uploadFile.value = null;
    uploadName.value = '';
    await appStore.refreshSources();
    appStore.notify('文件已上传并保存');
  } finally {
    isUploading.value = false;
  }
}

async function activateScenario(scenarioId: number): Promise<void> {
  const payload = await api.activateScenario(scenarioId);
  appStore.applySessions(payload.sessions);
  await appStore.refreshRuntime();
  appStore.notify('预案已调用');
}

async function setSystemVolumeFromInput(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement;
  await appStore.setSystemVolume(Number(input.value));
}

async function toggleSystemMute(): Promise<void> {
  await appStore.setSystemVolume(appStore.systemVolumeLevel, !appStore.systemMuted);
}
</script>

<template>
  <section class="command-hero panel">
    <div>
      <span class="eyebrow">Fluent Command Center</span>
      <h2>{{ appStore.bigScreenModeLabel }} · {{ appStore.connectionStatus }}</h2>
      <p>首页只做运行态显示、预案调用、快捷上传、电源指令、音量和大屏模式切换。</p>
    </div>
    <div class="mode-switch" aria-label="大屏模式">
      <button type="button" :class="{ active: appStore.runtime?.big_screen_mode === 'single' }" @click="runAction(() => appStore.setBigScreenMode('single'))">单屏</button>
      <button type="button" :class="{ active: appStore.runtime?.big_screen_mode === 'double' }" @click="runAction(() => appStore.setBigScreenMode('double'))">双屏</button>
    </div>
  </section>

  <section class="metric-grid">
    <article class="metric-card">
      <span>在线源</span>
      <strong>{{ onlineSources }}</strong>
      <small>总计 {{ appStore.sources.length }} 个源 · {{ formatBytes(totalSourceSize) }}</small>
    </article>
    <article class="metric-card">
      <span>活跃窗口</span>
      <strong>{{ activeWindows }}</strong>
      <small>窗口 3/4 始终静音</small>
    </article>
    <article class="metric-card">
      <span>预案数量</span>
      <strong>{{ appStore.scenarios.length }}</strong>
      <small>首页仅调用，不编辑</small>
    </article>
    <article class="metric-card">
      <span>系统音量</span>
      <strong>{{ appStore.systemVolumeLevel }}</strong>
        <small>{{ appStore.systemMuted ? '静音' : appStore.systemVolumeBackend }}</small>
    </article>
  </section>

  <section class="grid two">
    <article class="panel">
      <div class="panel__header">
        <h2>预案调用</h2>
        <button type="button" @click="runAction(appStore.refreshScenarios)">刷新</button>
      </div>
      <div class="scenario-call-grid">
        <button v-for="scenario in pinnedScenarios" :key="scenario.id" type="button" @click="runAction(() => activateScenario(scenario.id))">
          <strong>{{ scenario.name }}</strong>
          <small>{{ scenario.big_screen_mode_state === 'set' ? scenario.big_screen_mode_label : '保持大屏模式' }}</small>
        </button>
        <p v-if="!appStore.scenarios.length" class="empty-note">暂无预案，请到“预案管理”添加。</p>
      </div>
    </article>

    <article class="panel">
      <div class="panel__header">
        <h2>文件上传</h2>
        <small>保存到源管理</small>
      </div>
      <input type="file" :disabled="isUploading" @change="onFileSelected" />
      <input v-model="uploadName" placeholder="显示名称（可选）" :disabled="isUploading" />
      <div v-if="isUploading" class="upload-progress"><span :style="{ width: `${uploadProgress}%` }"></span><strong>{{ uploadProgress }}%</strong></div>
      <button type="button" class="primary" :disabled="!uploadFile || isUploading" @click="runAction(uploadAndSave)">上传并保存</button>
    </article>
  </section>

  <section class="grid three">
    <article class="panel">
      <div class="panel__header">
        <h2>电源控制</h2>
      </div>
      <div class="button-grid">
        <button type="button" @click="runAction(() => appStore.powerDevice('splice_screen', 'on'))">拼接屏开机</button>
        <button type="button" class="danger" @click="runAction(() => appStore.powerDevice('splice_screen', 'off'))">拼接屏关机</button>
        <button type="button" @click="runAction(() => appStore.toggleDevice('tv_left'))">电视左开关切换</button>
        <button type="button" @click="runAction(() => appStore.toggleDevice('tv_right'))">电视右开关切换</button>
      </div>
    </article>

    <article class="panel">
      <div class="panel__header">
        <h2>音量管理</h2>
        <span class="chip">{{ appStore.systemVolumeBackend }}</span>
      </div>
      <label>系统音量 {{ appStore.systemVolumeLevel }}
        <input type="range" min="0" max="100" :value="appStore.systemVolumeLevel" @change="runAction(() => setSystemVolumeFromInput($event))" />
      </label>
      <button type="button" :class="{ active: appStore.systemMuted }" @click="runAction(toggleSystemMute)">{{ appStore.systemMuted ? '取消系统静音' : '系统静音' }}</button>
    </article>

    <article class="panel">
      <div class="panel__header">
        <h2>大屏显示状态</h2>
        <span class="chip chip--accent">{{ appStore.bigScreenModeLabel }}</span>
      </div>
      <p>单屏：窗口 1 作为主输出，窗口 2 自动静音。双屏：窗口 1/2 分别输出且保持可听。</p>
      <div class="button-grid">
        <button type="button" :class="{ active: appStore.runtime?.big_screen_mode === 'single' }" @click="runAction(() => appStore.setBigScreenMode('single'))">单屏</button>
        <button type="button" :class="{ active: appStore.runtime?.big_screen_mode === 'double' }" @click="runAction(() => appStore.setBigScreenMode('double'))">双屏</button>
      </div>
    </article>
  </section>

  <section class="panel">
    <div class="panel__header">
      <h2>当前窗口状态</h2>
      <button type="button" @click="runAction(appStore.refreshSessions)">刷新</button>
    </div>
    <div class="status-grid">
      <article v-for="session in appStore.sessions" :key="session.window_id" class="status-card">
        <strong>窗口 {{ session.window_id }}</strong>
        <span class="chip" :class="{ 'chip--accent': session.playback_state === 'playing' }">{{ session.playback_state_label }}</span>
        <small>{{ session.source_name }}</small>
        <small>{{ session.is_muted ? '静音' : `音量 ${session.volume}` }}</small>
      </article>
    </div>
  </section>
</template>
