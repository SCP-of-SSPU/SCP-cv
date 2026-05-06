<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { RouterLink, useRoute } from 'vue-router';

import { api, buildBackendUrl, type PptMediaItem, type PptResourceItem } from '@/services/api';
import { useAppStore } from '@/stores/app';

const route = useRoute();
const appStore = useAppStore();
const resources = ref<PptResourceItem[]>([]);
const isLoadingResources = ref(false);
const displayRouteByWindowId: Record<number, string> = {
  1: '/display/big-left',
  2: '/display/big-right',
  3: '/display/tv-left',
  4: '/display/tv-right',
};
const windowId = computed(() => Number(route.params.windowId || appStore.activeWindowId || 1));
const returnRoute = computed(() => displayRouteByWindowId[windowId.value] || '/display/big-left');
const session = computed(() => appStore.sessions.find((item) => item.window_id === windowId.value) || null);
const isPptSession = computed(() => session.value?.source_type === 'ppt');
const focusTitle = computed(() => (isPptSession.value ? session.value?.source_name || '未命名 PPT' : '未打开 PPT'));
const sourceId = computed(() => session.value?.source_id || 0);
const currentPage = computed(() => Math.max(1, session.value?.current_slide || 1));
const totalPages = computed(() => Math.max(session.value?.total_slides || 0, resources.value.length));
const currentResource = computed(() => resources.value.find((item) => item.page_index === currentPage.value) || null);
const nextResource = computed(() => resources.value.find((item) => item.page_index === currentPage.value + 1) || null);
const currentMediaItems = computed(() => currentResource.value?.media_items || []);
const primaryMediaItem = computed(() => currentMediaItems.value[0] || null);
const hasCurrentMedia = computed(() => currentMediaItems.value.length > 0);
const canGoPrev = computed(() => isPptSession.value && currentPage.value > 1);
const canGoNext = computed(() => isPptSession.value && (totalPages.value <= 0 || currentPage.value < totalPages.value));
const currentPreviewUrl = computed(() => (currentResource.value?.slide_image ? resourceUrl(currentResource.value.slide_image) : ''));
const nextPreviewPath = computed(() => nextResource.value?.slide_image || currentResource.value?.next_slide_image || '');
const nextPreviewUrl = computed(() => (nextPreviewPath.value ? resourceUrl(nextPreviewPath.value) : ''));
const nextPageLabel = computed(() => (isPptSession.value && (totalPages.value <= 0 || currentPage.value < totalPages.value) ? String(currentPage.value + 1) : '-'));
const notesText = computed(() => currentResource.value?.speaker_notes || '当前 PPT 尚未保存提词器文本。');
const slideProgress = computed(() => {
  if (!isPptSession.value || totalPages.value <= 0) return 0;
  return Math.min(100, Math.max(0, (currentPage.value / totalPages.value) * 100));
});
const slideProgressStyle = computed(() => ({ width: `${slideProgress.value}%` }));
const statusToneClass = computed(() => ({
  'chip--accent': session.value?.playback_state === 'playing',
  'chip--warn': session.value?.playback_state === 'paused' || session.value?.playback_state === 'stopped',
}));

function resourceUrl(path: string): string {
  return buildBackendUrl(path);
}

async function runAction(action: () => Promise<void>): Promise<void> {
  try {
    await action();
  } catch (error) {
    appStore.notify(error instanceof Error ? error.message : '操作失败', true);
  }
}

async function refreshResources(): Promise<void> {
  if (!isPptSession.value || sourceId.value <= 0) {
    resources.value = [];
    return;
  }
  isLoadingResources.value = true;
  try {
    const payload = await api.listPptResources(sourceId.value);
    resources.value = payload.resources;
  } catch (error) {
    resources.value = [];
    appStore.notify(error instanceof Error ? error.message : 'PPT 资源读取失败', true);
  } finally {
    isLoadingResources.value = false;
  }
}

async function navigate(action: string, targetIndex = 0): Promise<void> {
  const payload = await api.navigateContent(windowId.value, action, targetIndex, 0);
  appStore.applySessions(payload.sessions);
}

async function controlMedia(mediaItem: PptMediaItem, action: string): Promise<void> {
  const mediaIdentifier = String(mediaItem.shape_id || mediaItem.id);
  const payload = await api.controlPptMedia(windowId.value, action, mediaIdentifier, mediaItem.media_index);
  appStore.applySessions(payload.sessions);
}

async function controlCurrentMedia(action: string): Promise<void> {
  if (!primaryMediaItem.value) {
    appStore.notify('当前页未检测到可播放媒体', true);
    return;
  }
  await controlMedia(primaryMediaItem.value, action);
}

watch(windowId, (nextWindowId) => {
  appStore.activeWindowId = nextWindowId;
}, { immediate: true });

watch(sourceId, () => {
  void refreshResources();
}, { immediate: true });
</script>

<template>
  <main class="ppt-focus">
    <header class="ppt-focus__top">
      <RouterLink class="button-link" :to="returnRoute">返回屏幕控制</RouterLink>
      <div class="ppt-focus__title">
        <span class="eyebrow">PPT Focus · Window {{ windowId }}</span>
        <h1>{{ focusTitle }}</h1>
      </div>
      <div class="ppt-focus__status">
        <span class="chip" :class="statusToneClass">{{ session?.playback_state_label || '待机' }}</span>
        <strong>{{ currentPage }} / {{ totalPages || '-' }}</strong>
      </div>
    </header>

    <section class="ppt-focus__stage">
      <article class="slide-preview slide-preview--current">
        <div class="slide-preview__label">
          <span>当前页</span>
          <strong>{{ currentPage }}</strong>
        </div>
        <img v-if="currentPreviewUrl" :src="currentPreviewUrl" alt="当前页预览" />
        <strong v-else class="slide-preview__fallback">{{ currentPage }}</strong>
      </article>
      <aside class="ppt-focus__sidecar">
        <article class="slide-preview slide-preview--next">
          <div class="slide-preview__label">
            <span>下一页</span>
            <strong>{{ nextPageLabel }}</strong>
          </div>
          <img v-if="nextPreviewUrl" :src="nextPreviewUrl" alt="下一页预览" />
          <strong v-else class="slide-preview__fallback">{{ nextPageLabel }}</strong>
        </article>
        <article class="ppt-focus__cue-card">
          <span class="eyebrow">进度</span>
          <div class="slide-progress slide-progress--focus" aria-hidden="true">
            <span :style="slideProgressStyle"></span>
          </div>
          <p>{{ isLoadingResources ? '正在读取 PPT 资源' : `资源页数 ${resources.length} · 当前页媒体 ${currentMediaItems.length}` }}</p>
        </article>
      </aside>
    </section>

    <section class="ppt-focus__controls">
      <button type="button" :disabled="!canGoPrev" @click="runAction(() => navigate('prev'))">上一页</button>
      <button type="button" class="primary" :disabled="!canGoNext" @click="runAction(() => navigate('next'))">下一页</button>
      <button type="button" :disabled="!hasCurrentMedia" @click="runAction(() => controlCurrentMedia('play'))">播放媒体</button>
      <button type="button" :disabled="!hasCurrentMedia" @click="runAction(() => controlCurrentMedia('pause'))">暂停媒体</button>
    </section>

    <section class="ppt-focus__notes">
      <div class="ppt-focus__page-status">
        <span class="eyebrow">页码状态</span>
        <h2>{{ currentPage }} / {{ totalPages || '-' }}</h2>
        <small>{{ isLoadingResources ? '正在读取 PPT 资源' : `资源页数 ${resources.length} · 当前页媒体 ${currentMediaItems.length}` }}</small>
      </div>
      <article class="ppt-focus__teleprompter">
        <span class="eyebrow">提词器</span>
        <p>{{ notesText }}</p>
      </article>
    </section>
  </main>
</template>
