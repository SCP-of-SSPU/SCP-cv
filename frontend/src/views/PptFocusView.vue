<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { RouterLink, useRoute } from 'vue-router';

import { api, type PptResourceItem } from '@/services/api';
import { useAppStore } from '@/stores/app';

const route = useRoute();
const appStore = useAppStore();
const resources = ref<PptResourceItem[]>([]);
const isLoadingResources = ref(false);
const windowId = computed(() => Number(route.params.windowId || appStore.activeWindowId || 1));
const session = computed(() => appStore.sessions.find((item) => item.window_id === windowId.value) || null);
const currentPage = computed(() => Math.max(1, session.value?.current_slide || 1));
const totalPages = computed(() => session.value?.total_slides || resources.value.length || 0);
const currentResource = computed(() => resources.value.find((item) => item.page_index === currentPage.value) || null);
const nextResource = computed(() => resources.value.find((item) => item.page_index === currentPage.value + 1) || null);

async function runAction(action: () => Promise<void>): Promise<void> {
  try {
    await action();
  } catch (error) {
    appStore.notify(error instanceof Error ? error.message : '操作失败', true);
  }
}

async function refreshResources(): Promise<void> {
  const source = appStore.sources.find((item) => item.uri === session.value?.source_uri);
  if (!source || source.source_type !== 'ppt') {
    resources.value = [];
    return;
  }
  isLoadingResources.value = true;
  try {
    const payload = await api.listPptResources(source.id);
    resources.value = payload.resources;
  } finally {
    isLoadingResources.value = false;
  }
}

async function navigate(action: string, targetIndex = 0): Promise<void> {
  const payload = await api.navigateContent(windowId.value, action, targetIndex, 0);
  appStore.applySessions(payload.sessions);
}

async function control(action: string): Promise<void> {
  const payload = await api.controlPlayback(windowId.value, action);
  appStore.applySessions(payload.sessions);
}

watch(() => session.value?.source_uri, () => {
  void refreshResources();
});

onMounted(async () => {
  appStore.activeWindowId = windowId.value;
  await refreshResources();
});
</script>

<template>
  <main class="ppt-focus">
    <header class="ppt-focus__top">
      <RouterLink class="button-link" to="/playback">返回控制台</RouterLink>
      <div>
        <span class="eyebrow">PPT Focus · Window {{ windowId }}</span>
        <h1>{{ session?.source_name || '未打开 PPT' }}</h1>
      </div>
      <span class="chip" :class="{ 'chip--accent': session?.playback_state === 'playing' }">{{ session?.playback_state_label || '待机' }}</span>
    </header>

    <section class="ppt-focus__stage">
      <article class="slide-preview slide-preview--current">
        <span>当前页</span>
        <img v-if="currentResource?.slide_image" :src="currentResource.slide_image" alt="当前页预览" />
        <strong v-else>{{ currentPage }}</strong>
      </article>
      <aside class="slide-preview slide-preview--next">
        <span>下一页</span>
        <img v-if="nextResource?.slide_image || currentResource?.next_slide_image" :src="nextResource?.slide_image || currentResource?.next_slide_image" alt="下一页预览" />
        <strong v-else>{{ currentPage + 1 <= totalPages ? currentPage + 1 : '-' }}</strong>
      </aside>
    </section>

    <section class="ppt-focus__controls">
      <button type="button" @click="runAction(() => navigate('prev'))">上一页</button>
      <button type="button" class="primary" @click="runAction(() => navigate('next'))">下一页</button>
      <button type="button" @click="runAction(() => control('play'))">播放媒体</button>
      <button type="button" @click="runAction(() => control('pause'))">暂停媒体</button>
    </section>

    <section class="ppt-focus__notes">
      <div>
        <span class="eyebrow">页码状态</span>
        <h2>{{ currentPage }} / {{ totalPages || '-' }}</h2>
        <small>{{ isLoadingResources ? '正在读取 PPT 资源' : `资源页数 ${resources.length}` }}</small>
      </div>
      <article>
        <span class="eyebrow">提词器</span>
        <p>{{ currentResource?.speaker_notes || '当前 PPT 尚未保存提词器文本。' }}</p>
      </article>
    </section>
  </main>
</template>
