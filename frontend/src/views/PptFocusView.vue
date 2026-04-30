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
const source = computed(() => appStore.sources.find((item) => item.uri === session.value?.source_uri) || null);
const currentPage = computed(() => Math.max(1, session.value?.current_slide || 1));
const totalPages = computed(() => session.value?.total_slides || resources.value.length || 0);
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
  if (!source.value || source.value.source_type !== 'ppt') {
    resources.value = [];
    return;
  }
  isLoadingResources.value = true;
  try {
    const payload = await api.listPptResources(source.value.id);
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

watch(() => source.value?.id, () => {
  void refreshResources();
}, { immediate: true });
</script>

<template>
  <main class="ppt-focus">
    <header class="ppt-focus__top">
      <RouterLink class="button-link" :to="returnRoute">返回屏幕控制</RouterLink>
      <div>
        <span class="eyebrow">PPT Focus · Window {{ windowId }}</span>
        <h1>{{ focusTitle }}</h1>
      </div>
      <span class="chip" :class="{ 'chip--accent': session?.playback_state === 'playing' }">{{ session?.playback_state_label || '待机' }}</span>
    </header>

    <section class="ppt-focus__stage">
      <article class="slide-preview slide-preview--current">
        <span>当前页</span>
        <img v-if="currentPreviewUrl" :src="currentPreviewUrl" alt="当前页预览" />
        <strong v-else>{{ currentPage }}</strong>
      </article>
      <aside class="slide-preview slide-preview--next">
        <span>下一页</span>
        <img v-if="nextPreviewUrl" :src="nextPreviewUrl" alt="下一页预览" />
        <strong v-else>{{ nextPageLabel }}</strong>
      </aside>
    </section>

    <section class="ppt-focus__controls">
      <button type="button" :disabled="!canGoPrev" @click="runAction(() => navigate('prev'))">上一页</button>
      <button type="button" class="primary" :disabled="!canGoNext" @click="runAction(() => navigate('next'))">下一页</button>
      <button type="button" :disabled="!hasCurrentMedia" @click="runAction(() => controlCurrentMedia('play'))">播放媒体</button>
      <button type="button" :disabled="!hasCurrentMedia" @click="runAction(() => controlCurrentMedia('pause'))">暂停媒体</button>
    </section>

    <section class="ppt-focus__notes">
      <div>
        <span class="eyebrow">页码状态</span>
        <h2>{{ currentPage }} / {{ totalPages || '-' }}</h2>
        <small>{{ isLoadingResources ? '正在读取 PPT 资源' : `资源页数 ${resources.length} · 当前页媒体 ${currentMediaItems.length}` }}</small>
      </div>
      <article>
        <span class="eyebrow">提词器</span>
        <p>{{ currentResource?.speaker_notes || '当前 PPT 尚未保存提词器文本。' }}</p>
      </article>
      <article>
        <span class="eyebrow">当前页媒体</span>
        <div v-if="currentMediaItems.length" class="media-control-list">
          <div v-for="mediaItem in currentMediaItems" :key="mediaItem.id" class="media-control-row">
            <strong>{{ mediaItem.name }}</strong>
            <small>{{ mediaItem.media_type }} · #{{ mediaItem.media_index }}{{ mediaItem.shape_id ? ` · shape ${mediaItem.shape_id}` : '' }}</small>
            <div class="button-grid">
              <button type="button" @click="runAction(() => controlMedia(mediaItem, 'play'))">播放</button>
              <button type="button" @click="runAction(() => controlMedia(mediaItem, 'pause'))">暂停</button>
              <button type="button" @click="runAction(() => controlMedia(mediaItem, 'stop'))">停止</button>
            </div>
          </div>
        </div>
        <p v-else>当前页未检测到可逐项控制的音视频媒体。</p>
      </article>
    </section>
  </main>
</template>
