<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { RouterLink, useRoute } from 'vue-router';

import { api, formatDuration, type MediaSourceItem } from '@/services/api';
import { useAppStore } from '@/stores/app';

const route = useRoute();
const appStore = useAppStore();
const selectedSourceId = ref<number | ''>('');
const uploadFile = ref<File | null>(null);
const uploadName = ref('');
const uploadProgress = ref(0);
const isUploading = ref(false);
const targetPage = ref(1);
const seekPercent = ref(0);

const targetConfig = computed(() => {
  const target = String(route.params.target || 'big-left');
  const configs: Record<string, { title: string; subtitle: string; windowId: number; hiddenInSingle?: boolean }> = {
    'big-left': { title: '大屏左显示控制', subtitle: 'Single 模式下的大屏主输出', windowId: 1 },
    'big-right': { title: '大屏右显示控制', subtitle: 'Double 模式下的大屏右输出', windowId: 2, hiddenInSingle: true },
    'tv-left': { title: 'TV 左显示控制', subtitle: '电视左侧独立输出', windowId: 3 },
    'tv-right': { title: 'TV 右显示控制', subtitle: '电视右侧独立输出', windowId: 4 },
  };
  return configs[target] || configs['big-left'];
});
const session = computed(() => appStore.sessions.find((item) => item.window_id === targetConfig.value.windowId) || null);
const selectedSource = computed(() => appStore.sources.find((source) => source.id === Number(selectedSourceId.value)) || null);
const pageTitle = computed(() => (
  targetConfig.value.windowId === 1 && appStore.runtime?.big_screen_mode === 'single'
    ? '大屏显示控制'
    : targetConfig.value.hiddenInSingle && appStore.runtime?.big_screen_mode === 'single'
      ? '大屏右当前隐藏'
      : targetConfig.value.title
));
const isHiddenByMode = computed(() => targetConfig.value.hiddenInSingle && appStore.runtime?.big_screen_mode === 'single');

watch(targetConfig, (config) => {
  appStore.activeWindowId = config.windowId;
}, { immediate: true });

watch(session, (currentSession) => {
  if (!currentSession?.source_uri) return;
  const matchedSource = appStore.sources.find((source) => source.uri === currentSession.source_uri);
  if (matchedSource) selectedSourceId.value = matchedSource.id;
  if (currentSession.current_slide > 0) targetPage.value = currentSession.current_slide;
}, { immediate: true });

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

async function openSource(sourceId = Number(selectedSourceId.value)): Promise<void> {
  if (!sourceId) {
    appStore.notify('请先选择媒体源', true);
    return;
  }
  const payload = await api.openSource(targetConfig.value.windowId, sourceId, true);
  appStore.applySessions(payload.sessions);
  appStore.notify(`已打开到窗口 ${targetConfig.value.windowId}`);
}

async function uploadAndOpen(isTemporary: boolean): Promise<void> {
  if (!uploadFile.value) {
    appStore.notify('请先选择文件', true);
    return;
  }
  const formData = new FormData();
  formData.append('file', uploadFile.value);
  if (uploadName.value.trim()) formData.append('name', uploadName.value.trim());
  if (isTemporary) formData.append('is_temporary', 'true');
  isUploading.value = true;
  uploadProgress.value = 0;
  try {
    const result = await api.uploadSource(formData, {
      onProgress: (percent) => {
        uploadProgress.value = percent;
      },
    });
    uploadFile.value = null;
    uploadName.value = '';
    await appStore.refreshSources();
    selectedSourceId.value = result.source.id;
    await openSource(result.source.id);
  } finally {
    isUploading.value = false;
  }
}

async function closeDisplay(): Promise<void> {
  const payload = await api.closeSource(targetConfig.value.windowId);
  appStore.applySessions(payload.sessions);
  appStore.notify('显示已关闭');
}

async function control(action: string): Promise<void> {
  const payload = await api.controlPlayback(targetConfig.value.windowId, action);
  appStore.applySessions(payload.sessions);
}

async function navigate(action: string, targetIndex = 0, positionMs = 0): Promise<void> {
  const payload = await api.navigateContent(targetConfig.value.windowId, action, targetIndex, positionMs);
  appStore.applySessions(payload.sessions);
}

async function gotoPage(): Promise<void> {
  await navigate('goto', Number(targetPage.value), 0);
}

async function seek(): Promise<void> {
  const durationMs = session.value?.duration_ms || 0;
  if (!durationMs) return;
  await navigate('seek', 0, Math.round((seekPercent.value / 1000) * durationMs));
}

async function toggleLoop(): Promise<void> {
  const payload = await api.setLoop(targetConfig.value.windowId, !(session.value?.loop_enabled || false));
  appStore.applySessions(payload.sessions);
}

async function setVolume(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement;
  const payload = await api.setWindowVolume(targetConfig.value.windowId, Number(input.value));
  appStore.applySessions(payload.sessions);
}

function sourceTypeLabel(source: MediaSourceItem | null): string {
  if (!source) return '未选择';
  const labels: Record<string, string> = {
    ppt: 'PPT', video: '视频', audio: '音频', image: '图片', web: '网页', srt_stream: '直播', rtsp_stream: '直播', custom_stream: '直播',
  };
  return labels[source.source_type] || source.source_type;
}
</script>

<template>
  <section class="panel display-hero" :class="{ 'display-hero--hidden': isHiddenByMode }">
    <div>
      <span class="eyebrow">Window {{ targetConfig.windowId }}</span>
      <h2>{{ pageTitle }}</h2>
      <p>{{ targetConfig.subtitle }} · 当前：{{ session?.source_name || '黑屏' }}</p>
    </div>
    <RouterLink v-if="session?.source_type === 'ppt'" class="button-link primary" :to="`/ppt-focus/${targetConfig.windowId}`">PPT 专注模式</RouterLink>
  </section>

  <section v-if="isHiddenByMode" class="panel">
    <h2>Single 模式下隐藏</h2>
    <p>大屏右显示在 Single 模式中保持静音并隐藏切换入口。切换到 Double 后可独立控制窗口 2。</p>
    <button type="button" @click="runAction(() => appStore.setBigScreenMode('double'))">切换到 Double</button>
  </section>

  <section v-else class="display-layout">
    <article class="panel">
      <h2>切换源</h2>
      <select v-model="selectedSourceId">
        <option value="">选择媒体源</option>
        <option v-for="source in appStore.availableSources" :key="source.id" :value="source.id">{{ source.name }}（{{ sourceTypeLabel(source) }}）</option>
      </select>
      <div class="button-grid button-grid--four">
        <button type="button" @click="runAction(() => openSource())">切换源</button>
        <button type="button" :disabled="!uploadFile || isUploading" @click="runAction(() => uploadAndOpen(true))">上传临时源</button>
        <button type="button" :disabled="!uploadFile || isUploading" @click="runAction(() => uploadAndOpen(false))">上传源并保存</button>
        <button type="button" class="danger" @click="runAction(closeDisplay)">关闭显示</button>
      </div>

      <h2>上传并打开</h2>
      <input type="file" :disabled="isUploading" @change="onFileSelected" />
      <input v-model="uploadName" placeholder="显示名称（可选）" :disabled="isUploading" />
      <div v-if="isUploading" class="upload-progress"><span :style="{ width: `${uploadProgress}%` }"></span><strong>{{ uploadProgress }}%</strong></div>
      <small>选择文件后，可通过上方“上传临时源”或“上传源并保存”执行。</small>
    </article>

    <article class="panel source-control-card">
      <span class="eyebrow">{{ sourceTypeLabel(selectedSource) }}</span>
      <h2>{{ session?.source_name || selectedSource?.name || '未打开媒体源' }}</h2>
      <p>{{ session?.playback_state_label || '待机' }} · {{ session?.is_muted ? '静音' : `音量 ${session?.volume ?? 100}` }}</p>

      <div v-if="session?.source_type === 'ppt'" class="type-controls">
        <div class="button-grid">
          <button type="button" @click="runAction(() => navigate('prev'))">上一页</button>
          <button type="button" class="primary" @click="runAction(() => navigate('next'))">下一页</button>
        </div>
        <div class="inline-form">
          <input v-model.number="targetPage" type="number" min="1" />
          <button type="button" @click="runAction(gotoPage)">跳页</button>
        </div>
      </div>

      <div v-else-if="session?.source_type === 'video' || session?.source_type === 'audio'" class="type-controls">
        <div class="button-grid">
          <button type="button" @click="runAction(() => control('play'))">播放</button>
          <button type="button" @click="runAction(() => control('pause'))">暂停</button>
          <button type="button" @click="runAction(toggleLoop)">{{ session?.loop_enabled ? '关闭循环' : '开启循环' }}</button>
        </div>
        <p>{{ formatDuration(session?.position_ms || 0) }} / {{ formatDuration(session?.duration_ms || 0) }}</p>
        <input v-model.number="seekPercent" type="range" min="0" max="1000" :disabled="!session?.duration_ms" @change="runAction(seek)" />
      </div>

      <div v-else-if="session?.source_type === 'image' || session?.source_type === 'web'" class="preview-card">
        <strong>{{ session.source_type === 'web' ? '网页预览地址' : '图片资源路径' }}</strong>
        <small>{{ session.source_uri }}</small>
      </div>

      <div v-else-if="session?.source_type.includes('stream')" class="preview-card live">
        <strong>直播状态</strong>
        <small>{{ session.source_uri }}</small>
      </div>

      <label>窗口音量 {{ session?.volume ?? 100 }}
        <input type="range" min="0" max="100" :value="session?.volume ?? 100" @change="runAction(() => setVolume($event))" />
      </label>
    </article>
  </section>
</template>
