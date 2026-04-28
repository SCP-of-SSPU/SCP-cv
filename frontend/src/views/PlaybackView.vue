<script setup lang="ts">
import { computed, ref, watch } from 'vue';

import { formatDuration } from '@/services/api';
import { useAppStore } from '@/stores/app';

const appStore = useAppStore();
const selectedSourceId = ref<number | ''>('');
const targetPage = ref(1);
const seekPercent = ref(0);
const pendingAction = ref('');
const remoteHint = ref('');
const touchStartX = ref(0);
const touchStartY = ref(0);
let remoteHintTimer: number | undefined;
const activeSession = computed(() => appStore.activeSession);
const isPresentation = computed(() => activeSession.value?.source_type === 'ppt');
const currentSlide = computed(() => activeSession.value?.current_slide || 0);
const totalSlides = computed(() => activeSession.value?.total_slides || 0);
const canNavigateSlides = computed(() => isPresentation.value && Boolean(activeSession.value?.source_name));
const hasAnyPendingAction = computed(() => pendingAction.value.length > 0);
const blocksActiveWindowAction = computed(() => hasAnyPendingAction.value);
const pptSources = computed(() => appStore.availableSources.filter((source) => source.source_type === 'ppt'));
const canGoPrev = computed(() => canNavigateSlides.value && !blocksActiveWindowAction.value && (totalSlides.value <= 0 || currentSlide.value > 1));
const canGoNext = computed(() => canNavigateSlides.value && !blocksActiveWindowAction.value && (totalSlides.value <= 0 || currentSlide.value < totalSlides.value));
const remoteActionLabel = computed(() => pendingAction.value || '待命');
const slideProgress = computed(() => {
  if (!canNavigateSlides.value || totalSlides.value <= 0) return 0;
  return Math.min(100, Math.max(0, (currentSlide.value / totalSlides.value) * 100));
});
const slideProgressStyle = computed(() => ({ width: `${slideProgress.value}%` }));
const remoteStatusText = computed(() => {
  if (remoteHint.value) return remoteHint.value;
  if (canNavigateSlides.value) return '左右滑动遥控卡片也可翻页，适合单手巡场操作';
  return '请先为当前窗口打开 PPT 源，再使用翻页和跳页操作';
});

watch(currentSlide, (slide) => {
  if (slide > 0) targetPage.value = slide;
});

watch(activeSession, (session) => {
  if (session?.source_type !== 'ppt') return;
  const matchedSource = pptSources.value.find((source) => source.uri === session.source_uri);
  if (matchedSource) selectedSourceId.value = matchedSource.id;
}, { immediate: true });

function setRemoteHint(message: string): void {
  remoteHint.value = message;
  if (remoteHintTimer) window.clearTimeout(remoteHintTimer);
  remoteHintTimer = window.setTimeout(() => {
    if (remoteHint.value === message) remoteHint.value = '';
  }, 1800);
}

async function runAction(action: () => Promise<void>, actionLabel = '操作'): Promise<void> {
  if (pendingAction.value) return;
  pendingAction.value = actionLabel;
  try {
    await action();
    setRemoteHint(`${actionLabel}已发送`);
  } catch (error) {
    appStore.notify(error instanceof Error ? error.message : '操作失败', true);
  } finally {
    pendingAction.value = '';
  }
}

async function openSelected(): Promise<void> {
  if (!selectedSourceId.value) {
    appStore.notify('请先选择媒体源', true);
    return;
  }
  await appStore.openSource(Number(selectedSourceId.value));
}

function clampPage(page: number): number {
  const normalizedPage = Number.isFinite(page) ? Math.trunc(page) : 1;
  const pageAtLeastOne = Math.max(1, normalizedPage);
  return totalSlides.value > 0 ? Math.min(pageAtLeastOne, totalSlides.value) : pageAtLeastOne;
}

function normalizeTargetPage(): void {
  targetPage.value = clampPage(Number(targetPage.value));
}

function adjustTargetPage(delta: number): void {
  targetPage.value = clampPage(Number(targetPage.value) + delta);
}

async function gotoPage(page = targetPage.value): Promise<void> {
  if (!canNavigateSlides.value) {
    appStore.notify('请先打开 PPT 源', true);
    return;
  }
  const pageToOpen = clampPage(Number(page));
  targetPage.value = pageToOpen;
  await appStore.navigate('goto', pageToOpen, 0);
}

async function jumpRelative(delta: number): Promise<void> {
  const pageBase = currentSlide.value || targetPage.value;
  await gotoPage(pageBase + delta);
}

async function goPrevSlide(): Promise<void> {
  if (!canGoPrev.value) return;
  await appStore.navigate('prev');
}

async function goNextSlide(): Promise<void> {
  if (!canGoNext.value) return;
  await appStore.navigate('next');
}

function rememberTouchStart(event: TouchEvent): void {
  const touch = event.changedTouches[0];
  if (!touch) return;
  touchStartX.value = touch.clientX;
  touchStartY.value = touch.clientY;
}

async function handleRemoteSwipe(event: TouchEvent): Promise<void> {
  const touch = event.changedTouches[0];
  if (!touch || !canNavigateSlides.value || hasAnyPendingAction.value) return;
  const deltaX = touch.clientX - touchStartX.value;
  const deltaY = touch.clientY - touchStartY.value;
  if (Math.abs(deltaX) < 54 || Math.abs(deltaX) < Math.abs(deltaY) * 1.35) return;
  await runAction(() => appStore.navigate(deltaX < 0 ? 'next' : 'prev'), deltaX < 0 ? '下一页' : '上一页');
}

async function seek(): Promise<void> {
  const durationMs = activeSession.value?.duration_ms || 0;
  if (!durationMs) return;
  await appStore.navigate('seek', 0, Math.round((seekPercent.value / 1000) * durationMs));
}
</script>

<template>
  <nav class="window-tabs" aria-label="播放窗口选择">
    <button
      v-for="windowId in [1, 2, 3, 4]"
      :key="windowId"
      type="button"
      :class="{ active: appStore.activeWindowId === windowId }"
      :disabled="hasAnyPendingAction"
      @click="appStore.activeWindowId = windowId"
    >
      窗口 {{ windowId }}
    </button>
    <button type="button" :disabled="hasAnyPendingAction" @click="runAction(appStore.showWindowIds, '显示窗口 ID')">显示窗口 ID</button>
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

  <section
    class="panel remote ppt-remote"
    :class="{ 'ppt-remote--disabled': !canNavigateSlides }"
    @touchstart.passive="rememberTouchStart"
    @touchend.passive="handleRemoteSwipe"
  >
    <div class="remote__header">
      <div>
        <span class="eyebrow">手机 PPT 遥控</span>
        <h2>窗口 {{ appStore.activeWindowId }}</h2>
      </div>
      <span class="chip" :class="{ 'chip--accent': canNavigateSlides }">
        {{ canNavigateSlides ? 'PPT 可控' : '等待 PPT' }}
      </span>
    </div>

    <div class="remote__meter" aria-live="polite">
      <div class="remote__slide-number">
        <span>当前页</span>
        <strong>{{ currentSlide || '-' }}</strong>
        <small>/ {{ totalSlides || '-' }}</small>
      </div>
      <div class="remote__source-name">
        <strong>{{ activeSession?.source_name || '未打开媒体源' }}</strong>
        <small>{{ activeSession?.playback_state_label || '待机' }} · {{ remoteActionLabel }}</small>
      </div>
      <div class="slide-progress" aria-hidden="true">
        <span :style="slideProgressStyle"></span>
      </div>
    </div>

    <div class="remote__focus" aria-label="手机 PPT 核心翻页区">
      <button type="button" class="remote__prev" :disabled="!canGoPrev" @click="runAction(goPrevSlide, '上一页')">
        <span>上一页</span>
        <small>右滑同效</small>
      </button>
      <button type="button" class="remote__next" :disabled="!canGoNext" @click="runAction(goNextSlide, '下一页')">
        <span>下一页</span>
        <strong>{{ currentSlide || '-' }} / {{ totalSlides || '-' }}</strong>
        <small>左滑同效</small>
      </button>
    </div>

    <div class="remote__source-picker">
      <select v-model="selectedSourceId" aria-label="选择 PPT 源">
        <option value="">选择 PPT 源</option>
        <option v-for="source in pptSources" :key="source.id" :value="source.id">
          {{ source.name }}
        </option>
      </select>
      <button type="button" :disabled="!selectedSourceId || blocksActiveWindowAction" @click="runAction(openSelected, '打开 PPT')">打开</button>
    </div>

    <div class="remote__buttons remote__buttons--pager">
      <button type="button" :disabled="!canGoPrev" @click="runAction(goPrevSlide, '上一页')">
        上一页
        <small>向右滑也可返回</small>
      </button>
      <button type="button" class="primary" :disabled="!canGoNext" @click="runAction(goNextSlide, '下一页')">
        下一页
        <small>向左滑也可前进</small>
      </button>
    </div>

    <div class="remote__quick-jump">
      <button type="button" :disabled="!canNavigateSlides || blocksActiveWindowAction" @click="runAction(() => gotoPage(1), '跳到首页')">首页</button>
      <button type="button" :disabled="!canNavigateSlides || blocksActiveWindowAction" @click="runAction(() => jumpRelative(-10), '后退 10 页')">-10</button>
      <button type="button" :disabled="!canNavigateSlides || blocksActiveWindowAction" @click="runAction(() => jumpRelative(10), '前进 10 页')">+10</button>
      <button type="button" :disabled="!canNavigateSlides || !totalSlides || blocksActiveWindowAction" @click="runAction(() => gotoPage(totalSlides), '跳到末页')">末页</button>
    </div>

    <div class="remote__goto">
      <button type="button" :disabled="blocksActiveWindowAction" aria-label="目标页减一" @click="adjustTargetPage(-1)">-</button>
      <input v-model.number="targetPage" type="number" inputmode="numeric" pattern="[0-9]*" min="1" :max="totalSlides || undefined" aria-label="目标页码" @blur="normalizeTargetPage" />
      <button type="button" :disabled="blocksActiveWindowAction" aria-label="目标页加一" @click="adjustTargetPage(1)">+</button>
      <button type="button" class="primary" :disabled="!canNavigateSlides || blocksActiveWindowAction" @click="runAction(gotoPage, '跳页')">跳页</button>
    </div>
    <p class="remote__hint">{{ remoteStatusText }}</p>
  </section>

  <section class="grid two desktop-controls">
    <article class="panel">
      <h2>打开媒体源</h2>
      <select v-model="selectedSourceId">
        <option value="">选择媒体源</option>
        <option v-for="source in appStore.availableSources" :key="source.id" :value="source.id">
          {{ source.name }}（{{ source.source_type }}）
        </option>
      </select>
      <button type="button" :disabled="blocksActiveWindowAction" @click="runAction(openSelected, '打开媒体源')">打开到窗口 {{ appStore.activeWindowId }}</button>
    </article>

    <article class="panel">
      <h2>基本控制</h2>
      <div class="button-grid">
        <button type="button" :disabled="blocksActiveWindowAction" @click="runAction(() => appStore.control('play'), '播放')">播放</button>
        <button type="button" :disabled="blocksActiveWindowAction" @click="runAction(() => appStore.control('pause'), '暂停')">暂停</button>
        <button type="button" :disabled="blocksActiveWindowAction" @click="runAction(() => appStore.control('stop'), '停止')">停止</button>
        <button type="button" class="danger" :disabled="blocksActiveWindowAction" @click="runAction(appStore.closeActive, '关闭')">关闭</button>
        <button type="button" :disabled="blocksActiveWindowAction" @click="runAction(appStore.toggleLoop, '循环切换')">切换循环</button>
      </div>
    </article>

    <article class="panel">
      <h2>内容导航</h2>
      <div class="button-grid">
        <button type="button" :disabled="!canNavigateSlides || blocksActiveWindowAction" @click="runAction(() => appStore.navigate('prev'), '上一页')">上一页</button>
        <button type="button" :disabled="!canNavigateSlides || blocksActiveWindowAction" @click="runAction(() => appStore.navigate('next'), '下一页')">下一页</button>
      </div>
      <div class="inline-form">
        <input v-model.number="targetPage" type="number" min="1" :max="totalSlides || undefined" @blur="normalizeTargetPage" />
        <button type="button" :disabled="!canNavigateSlides || blocksActiveWindowAction" @click="runAction(gotoPage, '跳页')">跳页</button>
      </div>
    </article>

    <article class="panel">
      <h2>视频进度</h2>
      <p>{{ formatDuration(activeSession?.position_ms || 0) }} / {{ formatDuration(activeSession?.duration_ms || 0) }}</p>
      <input v-model.number="seekPercent" type="range" min="0" max="1000" :disabled="!activeSession?.duration_ms || blocksActiveWindowAction" @change="runAction(seek, '视频跳转')" />
    </article>
  </section>
</template>
