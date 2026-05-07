<script setup lang="ts">
/**
 * PPT 专注模式：完全替换 Shell 的全屏深色舞台。
 *  - ≥ lg 横屏：当前页 PNG 大预览 + 下一页缩略 + 进度 + 提词器；
 *  - < lg 或竖屏：方向阻断 EmptyState，提供「返回 / 紧凑模式」两条出路。
 */
import { computed, onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import {
  FButton,
  FEmpty,
  FIcon,
  FMessageBar,
  FProgress,
  FSpinner,
  FTag,
} from '@/design-system';
import { useBreakpoint } from '@/composables/useBreakpoint';
import { useToast } from '@/composables/useToast';
import { useSessionStore } from '@/stores/sessions';
import { api, buildBackendUrl, type PptResourceItem } from '@/services/api';

const route = useRoute();
const router = useRouter();
const { canUseFocusMode } = useBreakpoint();
const sessionStore = useSessionStore();
const toast = useToast();

const compactMode = ref(false);
const isPinned = ref(false);

const windowId = computed(() => Number.parseInt(String(route.params.windowId ?? '0'), 10));
const session = computed(() => sessionStore.byWindowId(windowId.value));

const resources = ref<PptResourceItem[]>([]);
const loadError = ref('');
const isLoading = ref(false);

const currentResource = computed(() =>
  resources.value.find((res) => res.page_index === Math.max(0, (session.value?.current_slide ?? 1) - 1)),
);
const nextResource = computed(() =>
  resources.value.find((res) => res.page_index === (session.value?.current_slide ?? 1)),
);

const slidesProgress = computed(() => {
  const total = session.value?.total_slides ?? 0;
  const current = session.value?.current_slide ?? 0;
  return { total, current };
});

const eligible = computed(() => canUseFocusMode.value || compactMode.value);

async function loadResources(): Promise<void> {
  if (!session.value?.source_id || session.value?.source_type !== 'ppt') {
    resources.value = [];
    return;
  }
  isLoading.value = true;
  loadError.value = '';
  try {
    const payload = await api.listPptResources(session.value.source_id);
    resources.value = payload.resources;
  } catch (error) {
    loadError.value = error instanceof Error ? error.message : '加载 PPT 资源失败';
  } finally {
    isLoading.value = false;
  }
}

watch(session, loadResources, { immediate: true });

onMounted(() => {
  // 进入专注模式时补一次拉取，避免进入页面时 SSE 还没刷新。
  void sessionStore.refresh();
});

async function nav(action: 'prev' | 'next'): Promise<void> {
  if (!session.value) return;
  try {
    await sessionStore.navigate(session.value.window_id, action);
  } catch (error) {
    toast.error('翻页失败', error instanceof Error ? error.message : '请稍后重试');
  }
}

async function togglePlayPause(): Promise<void> {
  if (!session.value) return;
  const current = currentResource.value;
  if (!current?.media_items?.length) {
    toast.info('当前页无媒体可播放');
    return;
  }
  const isPlaying = session.value.playback_state === 'playing';
  try {
    await Promise.all(
      current.media_items.map((media) =>
        sessionStore.controlPptMedia(session.value!.window_id, isPlaying ? 'pause' : 'play', media.id, media.media_index),
      ),
    );
  } catch (error) {
    toast.error('PPT 媒体控制失败', error instanceof Error ? error.message : '请稍后重试');
  }
}

async function togglePin(): Promise<void> {
  isPinned.value = !isPinned.value;
  if (isPinned.value && document.documentElement.requestFullscreen) {
    try {
      await document.documentElement.requestFullscreen();
    } catch {
      // requestFullscreen 在用户首次交互前可能被拒绝，不视为错误。
    }
  } else if (!isPinned.value && document.fullscreenElement) {
    await document.exitFullscreen();
  }
}

function exitFocus(): void {
  void router.push(`/display/${windowMappingForExit.value}`);
}

const windowMappingForExit = computed(() => {
  switch (windowId.value) {
    case 2:
      return 'big-right';
    case 3:
      return 'tv-left';
    case 4:
      return 'tv-right';
    case 1:
    default:
      return 'big-left';
  }
});

const slideImage = computed(() => (currentResource.value?.slide_image ? buildBackendUrl(currentResource.value.slide_image) : ''));
const nextSlideImage = computed(() => (nextResource.value?.slide_image ? buildBackendUrl(nextResource.value.slide_image) : ''));

const enterCompact = (): void => {
  compactMode.value = true;
};
</script>

<template>
  <div class="ppt-focus" data-theme="dark">
    <header class="ppt-focus__topbar">
      <FButton appearance="subtle" icon-start="arrow_left_24_regular" @click="exitFocus">
        返回屏幕控制
      </FButton>
      <div class="ppt-focus__topbar-center">
        <FTag tone="info">窗口 {{ windowId }}</FTag>
        <span class="ppt-focus__topbar-title">{{ session?.source_name || '未选择 PPT 源' }}</span>
        <FTag :tone="session?.playback_state === 'playing' ? 'success' : 'subtle'">
          {{ session?.playback_state_label || session?.playback_state || '未知' }}
        </FTag>
        <span class="ppt-focus__topbar-progress" v-if="slidesProgress.total > 0">
          {{ slidesProgress.current }} / {{ slidesProgress.total }}
        </span>
      </div>
      <FButton
        appearance="subtle"
        :icon-start="isPinned ? 'pin_24_filled' : 'pin_24_regular'"
        @click="togglePin"
      >
        {{ isPinned ? '已固定' : '固定窗口' }}
      </FButton>
    </header>

    <main v-if="eligible" class="ppt-focus__stage" :class="{ 'ppt-focus__stage--compact': compactMode }">
      <FMessageBar v-if="loadError" tone="error" title="无法加载 PPT 资源">
        {{ loadError }}
      </FMessageBar>

      <div v-if="isLoading" class="ppt-focus__loading">
        <FSpinner :size="32" />
        <span>正在加载 PPT 页面…</span>
      </div>

      <template v-else-if="!session?.source_id">
        <FEmpty
          title="该窗口当前没有打开 PPT"
          description="请先在显示控制页打开 PPT 源后再进入专注模式。"
          icon="document_24_regular"
        >
          <template #actions>
            <FButton appearance="primary" @click="exitFocus">返回屏幕控制</FButton>
          </template>
        </FEmpty>
      </template>

      <template v-else>
        <div class="ppt-focus__layout">
          <figure class="ppt-focus__current">
            <img v-if="slideImage" :src="slideImage" :alt="`Page ${slidesProgress.current}`" />
            <div v-else class="ppt-focus__current-fallback">
              <FIcon name="document_24_regular" />
              <span>Page {{ slidesProgress.current }}</span>
            </div>
            <figcaption class="ppt-focus__current-caption">
              Page {{ slidesProgress.current }}
            </figcaption>
          </figure>

          <aside class="ppt-focus__side">
            <div class="ppt-focus__next">
              <p class="ppt-focus__side-eyebrow">下一页</p>
              <img v-if="nextSlideImage" :src="nextSlideImage" alt="下一页预览" />
              <div v-else class="ppt-focus__next-fallback">{{ slidesProgress.current + 1 }}</div>
            </div>
            <div class="ppt-focus__progress">
              <p class="ppt-focus__side-eyebrow">进度</p>
              <FProgress
                :value="slidesProgress.current"
                :max="slidesProgress.total || 1"
                show-label
              />
              <p class="ppt-focus__progress-meta">
                资源 {{ resources.length }} · 媒体 {{ currentResource?.media_items?.length ?? 0 }}
              </p>
            </div>
          </aside>
        </div>

        <div class="ppt-focus__controls">
          <FButton appearance="secondary" icon-start="previous_24_regular" @click="nav('prev')">
            上一页
          </FButton>
          <FButton
            appearance="primary"
            :icon-start="session.playback_state === 'playing' ? 'pause_24_regular' : 'play_24_regular'"
            @click="togglePlayPause"
          >
            {{ session.playback_state === 'playing' ? '暂停媒体' : '播放媒体' }}
          </FButton>
          <FButton appearance="secondary" icon-start="next_24_regular" @click="nav('next')">
            下一页
          </FButton>
        </div>

        <section class="ppt-focus__teleprompter">
          <p class="ppt-focus__side-eyebrow">提词器</p>
          <p v-if="currentResource?.speaker_notes" class="ppt-focus__teleprompter-text">
            {{ currentResource.speaker_notes }}
          </p>
          <p v-else class="ppt-focus__teleprompter-empty">该页暂无提词器内容。</p>
        </section>
      </template>
    </main>

    <main v-else class="ppt-focus__blocked">
      <FEmpty
        title="专注模式仅支持横屏大屏"
        description="请将设备旋转为横屏，或在更大屏幕（≥ 1024 × 768）上打开。"
        icon="warning_24_filled"
      >
        <template #actions>
          <FButton appearance="primary" @click="exitFocus">返回屏幕控制</FButton>
          <FButton appearance="subtle" @click="enterCompact">继续以紧凑模式打开</FButton>
        </template>
      </FEmpty>
    </main>
  </div>
</template>

<style scoped>
.ppt-focus {
  background: #0f1115;
  color: #f3f3f3;
  min-height: var(--app-height, 100vh);
  display: flex;
  flex-direction: column;
}

.ppt-focus__topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-l);
  padding: var(--spacing-m) var(--spacing-2xl);
  background: rgba(255, 255, 255, 0.04);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.ppt-focus__topbar :deep(.f-button) {
  color: inherit;
}

.ppt-focus__topbar-center {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-s);
  color: #f3f3f3;
}

.ppt-focus__topbar-title {
  font-weight: 600;
  max-width: 320px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.ppt-focus__topbar-progress {
  font-variant-numeric: tabular-nums;
  color: rgba(255, 255, 255, 0.6);
}

.ppt-focus__stage {
  flex: 1 1 auto;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-l);
  padding: var(--spacing-2xl);
}

.ppt-focus__stage--compact {
  padding: var(--spacing-l);
}

.ppt-focus__layout {
  display: grid;
  grid-template-columns: 6fr 2fr;
  gap: var(--spacing-l);
  flex: 1 1 auto;
}

.ppt-focus__current {
  margin: 0;
  background: #181a20;
  border-radius: var(--radius-large);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.ppt-focus__current img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  flex: 1 1 auto;
}

.ppt-focus__current-fallback {
  flex: 1 1 auto;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-s);
  color: rgba(255, 255, 255, 0.5);
  font-size: var(--type-title2-size);
}

.ppt-focus__current-caption {
  padding: var(--spacing-s) var(--spacing-l);
  background: rgba(255, 255, 255, 0.06);
  font-weight: 600;
}

.ppt-focus__side {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-l);
}

.ppt-focus__next {
  background: #181a20;
  border-radius: var(--radius-large);
  padding: var(--spacing-m);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.ppt-focus__next img {
  border-radius: var(--radius-medium);
  width: 100%;
  aspect-ratio: 16 / 9;
  object-fit: cover;
  background: rgba(255, 255, 255, 0.04);
}

.ppt-focus__next-fallback {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  aspect-ratio: 16 / 9;
  background: linear-gradient(135deg, rgba(40, 153, 245, 0.18), rgba(15, 108, 189, 0.04));
  color: rgba(255, 255, 255, 0.7);
  font-size: var(--type-title3-size);
  border-radius: var(--radius-medium);
}

.ppt-focus__progress {
  background: #181a20;
  border-radius: var(--radius-large);
  padding: var(--spacing-m);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.ppt-focus__progress-meta {
  margin: 0;
  color: rgba(255, 255, 255, 0.6);
  font-size: var(--type-caption1-size);
}

.ppt-focus__side-eyebrow {
  margin: 0;
  font-size: var(--type-caption1-size);
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.55);
}

.ppt-focus__controls {
  display: flex;
  justify-content: center;
  gap: var(--spacing-m);
}

.ppt-focus__controls :deep(.f-button) {
  min-width: 160px;
}

.ppt-focus__teleprompter {
  background: #181a20;
  border-radius: var(--radius-large);
  padding: var(--spacing-l);
  flex-shrink: 0;
}

.ppt-focus__teleprompter-text {
  margin: var(--spacing-xs) 0 0;
  font-size: 22px;
  line-height: 30px;
  white-space: pre-wrap;
  color: rgba(255, 255, 255, 0.92);
}

.ppt-focus__teleprompter-empty {
  margin: var(--spacing-xs) 0 0;
  color: rgba(255, 255, 255, 0.45);
}

.ppt-focus__loading {
  flex: 1 1 auto;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-s);
  color: rgba(255, 255, 255, 0.7);
}

.ppt-focus__blocked {
  flex: 1 1 auto;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-2xl);
}

@media (max-width: 1023px) and (min-aspect-ratio: 1/1) {
  .ppt-focus__layout {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 767px) {
  .ppt-focus__topbar {
    flex-wrap: wrap;
    padding: var(--spacing-s) var(--spacing-l);
  }
}
</style>
