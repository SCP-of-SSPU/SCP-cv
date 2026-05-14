<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import {
  FButton,
  FCombobox,
  FEmpty,
  FIcon,
  FMessageBar,
  FProgress,
  FSpinner,
  FTag,
} from '@/design-system';
import { useBreakpoint } from '@/composables/useBreakpoint';
import { useToast } from '@/composables/useToast';
import { api, buildBackendUrl, type PptMediaItem, type PptResourceItem } from '@/services/api';
import { useRuntimeStore } from '@/stores/runtime';
import { useSessionStore } from '@/stores/sessions';

import PptSlideRail from './PptSlideRail.vue';

interface PptSlideRailItem {
  pageIndex: number;
  imageUrl: string;
  hasMedia: boolean;
}

const route = useRoute();
const router = useRouter();
const { isLandscape } = useBreakpoint();
const runtimeStore = useRuntimeStore();
const sessionStore = useSessionStore();
const toast = useToast();

const isFullscreen = ref(false);
const resources = ref<PptResourceItem[]>([]);
const loadError = ref('');
const isLoading = ref(false);
const selectedMediaKey = ref<string | null>(null);

const windowId = computed(() => Number.parseInt(String(route.params.windowId ?? '0'), 10));
const session = computed(() => sessionStore.byWindowId(windowId.value));
const pptSourceId = computed(() => (session.value?.source_type === 'ppt' ? session.value.source_id : null));
const orientationKey = computed<'landscape' | 'portrait'>(() => (isLandscape.value ? 'landscape' : 'portrait'));

const slidesProgress = computed(() => ({
  total: session.value?.total_slides ?? 0,
  current: session.value?.current_slide ?? 0,
}));

const currentResource = computed(() =>
  resources.value.find((resource) => resource.page_index === (session.value?.current_slide ?? 1)),
);

const thumbnailItems = computed<PptSlideRailItem[]>(() =>
  [...resources.value]
    .sort((left, right) => left.page_index - right.page_index)
    .map((resource) => ({
      pageIndex: resource.page_index,
      imageUrl: resource.slide_image ? buildBackendUrl(resource.slide_image) : '',
      hasMedia: resource.has_media,
    })),
);

const slideImage = computed(() => {
  const path = currentResource.value?.slide_image;
  return path ? buildBackendUrl(path) : '';
});

const nextSlideImage = computed(() => {
  const path = currentResource.value?.next_slide_image;
  return path ? buildBackendUrl(path) : '';
});

const nextSlideNumber = computed(() => {
  if (slidesProgress.value.total <= 0 || slidesProgress.value.current >= slidesProgress.value.total) return null;
  return slidesProgress.value.current + 1;
});

const currentMediaItems = computed(() => currentResource.value?.media_items ?? []);

const currentMediaOptions = computed(() =>
  currentMediaItems.value.map((media) => ({
    value: mediaSelectionValue(media),
    label: media.name || `媒体 ${media.media_index}`,
    hint: media.media_type === 'audio' ? '音频' : media.media_type === 'video' ? '视频' : media.media_type,
  })),
);

const selectedMedia = computed(() =>
  currentMediaItems.value.find((media) => mediaSelectionValue(media) === selectedMediaKey.value) ?? null,
);

const canControlSelectedMedia = computed(() => !!session.value && !!selectedMedia.value);
const isMediaPickerDisabled = computed(() => currentMediaOptions.value.length === 0);
const mediaSelectPlaceholder = computed(() => {
  if (!currentMediaOptions.value.length) return '当前页无媒体';
  return currentMediaOptions.value.length === 1 ? '自动选择媒体' : '选择媒体';
});

const teleprompterText = computed(() => sanitizeSpeakerNotes(
  currentResource.value?.speaker_notes ?? '',
  slidesProgress.value.current,
  slidesProgress.value.total,
));

const windowLabel = computed(() => {
  switch (windowId.value) {
    case 1:
      return runtimeStore.runtime?.big_screen_mode === 'double' ? '大屏左' : '大屏';
    case 2:
      return '大屏右';
    case 3:
      return 'TV左';
    case 4:
      return 'TV右';
    default:
      return `窗口 ${windowId.value}`;
  }
});

watch(currentMediaItems, (items) => {
  if (!items.length) {
    selectedMediaKey.value = null;
    return;
  }
  if (items.length === 1) {
    selectedMediaKey.value = mediaSelectionValue(items[0]);
    return;
  }
  if (!items.some((media) => mediaSelectionValue(media) === selectedMediaKey.value)) {
    selectedMediaKey.value = null;
  }
}, { immediate: true });

watch(pptSourceId, loadResources, { immediate: true });

onMounted(() => {
  void sessionStore.refresh();
  if (!runtimeStore.runtime) {
    void runtimeStore.refresh().catch(() => undefined);
  }
});

function mediaSelectionValue(media: PptMediaItem): string {
  return `${media.id}:${media.media_index}`;
}

function sanitizeSpeakerNotes(notes: string, currentPage: number, totalPages: number): string {
  if (!notes.trim()) return '';
  const lines = notes.replace(/\r/g, '').split('\n');
  while (lines.length && !lines[lines.length - 1]?.trim()) {
    lines.pop();
  }
  const lastLine = lines[lines.length - 1]?.trim() ?? '';
  const normalizedLastLine = lastLine.toLowerCase().replace(/\s+/g, '');
  const pageMarkers = new Set([
    String(currentPage),
    `第${currentPage}页`,
    `page${currentPage}`,
    totalPages > 0 ? `${currentPage}/${totalPages}` : '',
    totalPages > 0 ? `page${currentPage}/${totalPages}` : '',
  ].filter(Boolean).map((item) => item.toLowerCase().replace(/\s+/g, '')));
  if (pageMarkers.has(normalizedLastLine)) {
    lines.pop();
  }
  return lines.join('\n').trim();
}

async function loadResources(sourceId: number | null): Promise<void> {
  if (!sourceId) {
    resources.value = [];
    loadError.value = '';
    isLoading.value = false;
    return;
  }
  isLoading.value = true;
  loadError.value = '';
  try {
    const payload = await api.listPptResources(sourceId);
    if (pptSourceId.value === sourceId) {
      resources.value = payload.resources;
    }
  } catch (error) {
    if (pptSourceId.value === sourceId) {
      loadError.value = error instanceof Error ? error.message : '加载 PPT 资源失败';
    }
  } finally {
    if (pptSourceId.value === sourceId) {
      isLoading.value = false;
    }
  }
}

async function nav(action: 'prev' | 'next'): Promise<void> {
  if (!session.value) return;
  try {
    await sessionStore.navigate(session.value.window_id, action);
  } catch (error) {
    toast.error('翻页失败', error instanceof Error ? error.message : '请稍后重试');
  }
}

async function jumpToSlide(pageIndex: number): Promise<void> {
  if (!session.value || pageIndex === session.value.current_slide) return;
  try {
    await sessionStore.navigate(session.value.window_id, 'goto', pageIndex);
  } catch (error) {
    toast.error('跳页失败', error instanceof Error ? error.message : '请稍后重试');
  }
}

async function controlSelectedMedia(action: 'play' | 'pause'): Promise<void> {
  if (!session.value || !selectedMedia.value) {
    if (currentMediaItems.value.length > 1) {
      toast.info('请先选择要控制的媒体');
    }
    return;
  }
  try {
    await sessionStore.controlPptMedia(
      session.value.window_id,
      action,
      selectedMedia.value.id,
      selectedMedia.value.media_index,
    );
  } catch (error) {
    toast.error('PPT 媒体控制失败', error instanceof Error ? error.message : '请稍后重试');
  }
}

async function toggleFullscreen(): Promise<void> {
  isFullscreen.value = !isFullscreen.value;
  if (isFullscreen.value && document.documentElement.requestFullscreen) {
    try {
      await document.documentElement.requestFullscreen();
    } catch {
      isFullscreen.value = !!document.fullscreenElement;
    }
  } else if (!isFullscreen.value && document.fullscreenElement) {
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
</script>

<template>
  <div class="ppt-focus" data-theme="dark">
    <header class="ppt-focus__topbar">
      <FButton appearance="subtle" icon-start="arrow_left_24_regular" @click="exitFocus">
        返回屏幕控制
      </FButton>
      <div class="ppt-focus__topbar-center">
        <FTag tone="info">{{ windowLabel }}</FTag>
        <span class="ppt-focus__topbar-title">{{ session?.source_name || '未选择 PPT 源' }}</span>
        <FTag :tone="session?.playback_state === 'playing' ? 'success' : 'subtle'">
          {{ session?.playback_state_label || session?.playback_state || '未知' }}
        </FTag>
        <span v-if="slidesProgress.total > 0" class="ppt-focus__topbar-progress">
          {{ slidesProgress.current }} / {{ slidesProgress.total }}
        </span>
      </div>
      <FButton
        appearance="subtle"
        :icon-start="isFullscreen ? 'full_screen_minimize_24_regular' : 'full_screen_maximize_24_regular'"
        @click="toggleFullscreen"
      >
        {{ isFullscreen ? '退出全屏' : '全屏' }}
      </FButton>
    </header>

    <main class="ppt-focus__stage" :data-orientation="orientationKey">
      <FMessageBar v-if="loadError" tone="error" title="无法加载 PPT 资源">
        {{ loadError }}
      </FMessageBar>

      <div v-if="isLoading" class="ppt-focus__loading">
        <FSpinner :size="32" />
        <span>正在加载 PPT 页面…</span>
      </div>

      <template v-else-if="!session?.source_id">
        <FEmpty title="该窗口当前没有打开 PPT" description="请先在显示控制页打开 PPT 源后再进入专注模式。" icon="document_24_regular">
          <template #actions>
            <FButton appearance="primary" @click="exitFocus">返回屏幕控制</FButton>
          </template>
        </FEmpty>
      </template>

      <template v-else>
        <div class="ppt-focus__layout">
          <PptSlideRail
            class="ppt-focus__slide-rail"
            :items="thumbnailItems"
            :current-page="slidesProgress.current"
            :total-pages="slidesProgress.total"
            @jump="jumpToSlide"
          />

          <figure class="ppt-focus__current">
            <img v-if="slideImage" :src="slideImage" :alt="`Page ${slidesProgress.current}`" />
            <div v-else class="ppt-focus__current-fallback">
              <FIcon name="document_24_regular" />
              <span>Page {{ slidesProgress.current }}</span>
            </div>
          </figure>

          <aside class="ppt-focus__side">
            <div class="ppt-focus__next">
              <p class="ppt-focus__side-eyebrow">下一页</p>
              <img v-if="nextSlideImage" :src="nextSlideImage" alt="下一页预览" />
              <div v-else class="ppt-focus__next-fallback">{{ nextSlideNumber ?? '—' }}</div>
            </div>

            <div class="ppt-focus__progress">
              <p class="ppt-focus__side-eyebrow">进度</p>
              <FProgress :value="slidesProgress.current" :max="slidesProgress.total || 1" show-label />
              <p class="ppt-focus__progress-page">Page {{ slidesProgress.current }}/{{ slidesProgress.total }}</p>
            </div>

            <section class="ppt-focus__teleprompter">
              <header class="ppt-focus__teleprompter-head">
                <p class="ppt-focus__side-eyebrow">提词器</p>
                <span class="ppt-focus__teleprompter-page">第 {{ slidesProgress.current }} 页</span>
              </header>
              <div class="ppt-focus__teleprompter-body">
                <p v-if="teleprompterText" class="ppt-focus__teleprompter-text">{{ teleprompterText }}</p>
                <p v-else class="ppt-focus__teleprompter-empty">该页暂无提词器内容。</p>
              </div>
            </section>
          </aside>
        </div>

        <div class="ppt-focus__controls" aria-label="PPT 专注控制条">
          <div class="ppt-focus__media-picker">
            <FCombobox
              v-model="selectedMediaKey"
              :options="currentMediaOptions"
              :placeholder="mediaSelectPlaceholder"
              :disabled="isMediaPickerDisabled"
              :searchable="currentMediaOptions.length >= 10"
              aria-label="选择当前页媒体"
              size="large"
            />
          </div>
          <FButton appearance="secondary" icon-start="previous_24_regular" @click="nav('prev')">
            上一页
          </FButton>
          <FButton appearance="secondary" icon-start="pause_24_regular" :disabled="!canControlSelectedMedia" @click="controlSelectedMedia('pause')">
            暂停媒体
          </FButton>
          <FButton appearance="primary" icon-start="play_24_regular" :disabled="!canControlSelectedMedia" @click="controlSelectedMedia('play')">
            播放媒体
          </FButton>
          <FButton appearance="secondary" icon-start="next_24_regular" @click="nav('next')">
            下一页
          </FButton>
        </div>
      </template>
    </main>
  </div>
</template>

<style scoped src="./PptFocusView.css"></style>
