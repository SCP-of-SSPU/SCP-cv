<script setup lang="ts">
import { computed, ref } from 'vue';

import { formatDuration } from '@/services/api';
import { useAppStore } from '@/stores/app';

const appStore = useAppStore();
const selectedSourceId = ref<number | ''>('');
const targetPage = ref(1);
const seekPercent = ref(0);
const activeSession = computed(() => appStore.activeSession);

async function runAction(action: () => Promise<void>): Promise<void> {
  try {
    await action();
  } catch (error) {
    appStore.notify(error instanceof Error ? error.message : '操作失败', true);
  }
}

async function openSelected(): Promise<void> {
  if (!selectedSourceId.value) {
    appStore.notify('请先选择媒体源', true);
    return;
  }
  await appStore.openSource(Number(selectedSourceId.value));
}

async function gotoPage(): Promise<void> {
  await appStore.navigate('goto', targetPage.value, 0);
}

async function seek(): Promise<void> {
  const durationMs = activeSession.value?.duration_ms || 0;
  if (!durationMs) return;
  await appStore.navigate('seek', 0, Math.round((seekPercent.value / 1000) * durationMs));
}
</script>

<template>
  <nav class="window-tabs">
    <button
      v-for="windowId in [1, 2, 3, 4]"
      :key="windowId"
      type="button"
      :class="{ active: appStore.activeWindowId === windowId }"
      @click="appStore.activeWindowId = windowId"
    >
      窗口 {{ windowId }}
    </button>
    <button type="button" :class="{ active: appStore.spliceActive }" @click="runAction(appStore.toggleSplice)">拼接 1+2</button>
    <button type="button" @click="runAction(appStore.showWindowIds)">显示窗口 ID</button>
  </nav>

  <section class="panel hero">
    <p>窗口 {{ appStore.activeWindowId }} · {{ activeSession?.playback_state_label || '待机' }}</p>
    <h2>{{ activeSession?.source_name || '未打开媒体源' }}</h2>
    <div class="stats">
      <span>类型：{{ activeSession?.source_type_label || '无' }}</span>
      <span>显示：{{ activeSession?.display_mode_label || '无' }}</span>
      <span>循环：{{ activeSession?.loop_enabled ? '开启' : '关闭' }}</span>
    </div>
  </section>

  <section class="panel remote">
    <p>手机 PPT 遥控 · {{ activeSession?.current_slide || 0 }} / {{ activeSession?.total_slides || 0 }} 页</p>
    <div class="remote__buttons">
      <button type="button" @click="runAction(() => appStore.navigate('prev'))">上一页</button>
      <button type="button" class="primary" @click="runAction(() => appStore.navigate('next'))">下一页</button>
    </div>
    <div class="inline-form">
      <input v-model.number="targetPage" type="number" min="1" />
      <button type="button" @click="runAction(gotoPage)">跳转</button>
    </div>
  </section>

  <section class="grid two">
    <article class="panel">
      <h2>打开媒体源</h2>
      <select v-model="selectedSourceId">
        <option value="">选择媒体源</option>
        <option v-for="source in appStore.availableSources" :key="source.id" :value="source.id">
          {{ source.name }}（{{ source.source_type }}）
        </option>
      </select>
      <button type="button" @click="runAction(openSelected)">打开到窗口 {{ appStore.activeWindowId }}</button>
    </article>

    <article class="panel">
      <h2>基本控制</h2>
      <div class="button-grid">
        <button type="button" @click="runAction(() => appStore.control('play'))">播放</button>
        <button type="button" @click="runAction(() => appStore.control('pause'))">暂停</button>
        <button type="button" @click="runAction(() => appStore.control('stop'))">停止</button>
        <button type="button" class="danger" @click="runAction(appStore.closeActive)">关闭</button>
        <button type="button" @click="runAction(appStore.toggleLoop)">切换循环</button>
      </div>
    </article>

    <article class="panel">
      <h2>内容导航</h2>
      <div class="button-grid">
        <button type="button" @click="runAction(() => appStore.navigate('prev'))">上一页</button>
        <button type="button" @click="runAction(() => appStore.navigate('next'))">下一页</button>
      </div>
      <div class="inline-form">
        <input v-model.number="targetPage" type="number" min="1" />
        <button type="button" @click="runAction(gotoPage)">跳页</button>
      </div>
    </article>

    <article class="panel">
      <h2>视频进度</h2>
      <p>{{ formatDuration(activeSession?.position_ms || 0) }} / {{ formatDuration(activeSession?.duration_ms || 0) }}</p>
      <input v-model.number="seekPercent" type="range" min="0" max="1000" @change="runAction(seek)" />
    </article>
  </section>
</template>
