<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
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
import { useTheme, type ThemeMode } from '@/composables/useTheme';
import { useToast } from '@/composables/useToast';
import { api, buildBackendUrl, type PptMediaItem, type PptResourceItem } from '@/services/api';
import { useRuntimeStore } from '@/stores/runtime';
import { useSessionStore } from '@/stores/sessions';
import { windowIdToSlug } from '@/features/display/displayTargets';

import PptSlideRail from './PptSlideRail.vue';
import { sanitizeSpeakerNotes } from './speakerNotes';

type KnownMediaType = 'audio' | 'video' | 'image';
const KNOWN_MEDIA_TYPES = new Set<KnownMediaType>(['audio', 'video', 'image']);

interface PptSlideRailItem {
  pageIndex: number;
  imageUrl: string;
  hasMedia: boolean;
}

const { t } = useI18n();
const route = useRoute();
const router = useRouter();
const { isLandscape } = useBreakpoint();
const runtimeStore = useRuntimeStore();
const sessionStore = useSessionStore();
const toast = useToast();
const { pushOverride, popOverride } = useTheme();

const isFullscreen = ref(false);
const resources = ref<PptResourceItem[]>([]);
const loadError = ref('');
const isLoading = ref(false);
const selectedMediaKey = ref<string | null>(null);
// 进入 focus 前的主题，仅用于诊断；真正恢复由 popOverride 完成。
const _restoreTheme = ref<ThemeMode | null>(null);

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
    label: media.name || t('pptFocus.mediaFallback', { n: media.media_index }),
    hint: mediaTypeHint(media.media_type),
  })),
);

function mediaTypeHint(rawType: string): string {
  const key = rawType?.toLowerCase() as KnownMediaType;
  if (KNOWN_MEDIA_TYPES.has(key)) return t(`pptFocus.mediaType.${key}`);
  return t('pptFocus.mediaType.other');
}

const selectedMedia = computed(() =>
  currentMediaItems.value.find((media) => mediaSelectionValue(media) === selectedMediaKey.value) ?? null,
);

const canControlSelectedMedia = computed(() => !!session.value && !!selectedMedia.value);
const isMediaPickerDisabled = computed(() => currentMediaOptions.value.length === 0);
const mediaSelectPlaceholder = computed(() => {
  if (!currentMediaOptions.value.length) return t('pptFocus.noMedia');
  return currentMediaOptions.value.length === 1 ? t('pptFocus.autoSelectMedia') : t('pptFocus.selectMedia');
});

const teleprompterText = computed(() => sanitizeSpeakerNotes(
  currentResource.value?.speaker_notes ?? '',
  slidesProgress.value.current,
  slidesProgress.value.total,
));

const windowLabel = computed(() => {
  switch (windowId.value) {
    case 1:
      return runtimeStore.runtime?.big_screen_mode === 'double' ? t('pptFocus.winBigLeft') : t('pptFocus.winBig');
    case 2:
      return t('pptFocus.winBigRight');
    case 3:
      return t('pptFocus.winTvLeft');
    case 4:
      return t('pptFocus.winTvRight');
    default:
      return t('pptFocus.winFallback', { id: windowId.value });
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

function syncFullscreen(): void {
  isFullscreen.value = !!document.fullscreenElement;
}

onMounted(() => {
  // 进入专注页：用 useTheme 的 override 通道临时锁定 dark，
  // 不污染 localStorage；退出时 popOverride 立即回到用户偏好。
  pushOverride('dark');
  document.addEventListener('fullscreenchange', syncFullscreen);
  void sessionStore.refresh();
  if (!runtimeStore.runtime) {
    void runtimeStore.refresh().catch(() => undefined);
  }
});

onBeforeUnmount(() => {
  popOverride();
  document.removeEventListener('fullscreenchange', syncFullscreen);
});

function mediaSelectionValue(media: PptMediaItem): string {
  return `${media.id}:${media.media_index}`;
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
      loadError.value = error instanceof Error ? error.message : t('pptFocus.loadFailTitle');
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
    toast.error(t('pptFocus.navFail'), error instanceof Error ? error.message : t('common.retry'));
  }
}

async function jumpToSlide(pageIndex: number): Promise<void> {
  if (!session.value || pageIndex === session.value.current_slide) return;
  try {
    await sessionStore.navigate(session.value.window_id, 'goto', pageIndex);
  } catch (error) {
    toast.error(t('pptFocus.jumpFail'), error instanceof Error ? error.message : t('common.retry'));
  }
}

async function controlSelectedMedia(action: 'play' | 'pause'): Promise<void> {
  if (!session.value || !selectedMedia.value) {
    if (currentMediaItems.value.length > 1) {
      toast.info(t('pptFocus.pickMediaFirst'));
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
    toast.error(t('pptFocus.mediaFail'), error instanceof Error ? error.message : t('common.retry'));
  }
}

async function toggleFullscreen(): Promise<void> {
  // 实际状态由 fullscreenchange 监听器同步，这里只发起请求。
  try {
    if (document.fullscreenElement) {
      await document.exitFullscreen();
    } else if (document.documentElement.requestFullscreen) {
      await document.documentElement.requestFullscreen();
    }
  } catch {
    // Safari 在某些容器上会拒绝退出全屏；忽略错误，依赖事件回填状态。
    syncFullscreen();
  }
}

function exitFocus(): void {
  void router.push(`/display/${windowIdToSlug(windowId.value)}`);
}
</script>

<template>
  <!--
    根容器不再写 data-theme="dark"：tokens.css 的 dark 块绑在 :root[data-theme='dark']，
    放在子节点上对 CSS 变量无作用；真实主题切换由 useTheme().pushOverride('dark')
    在 onMounted 中完成，退出时自动恢复。
  -->
  <div class="ppt-focus">
    <header class="ppt-focus__topbar">
      <FButton appearance="subtle" icon-start="arrow_left_24_regular" @click="exitFocus">
        {{ t('pptFocus.back') }}
      </FButton>
      <div class="ppt-focus__topbar-center">
        <FTag tone="info">{{ windowLabel }}</FTag>
        <span class="ppt-focus__topbar-title">{{ session?.source_name || t('pptFocus.noSourceSelected') }}</span>
        <FTag :tone="session?.playback_state === 'playing' ? 'success' : 'subtle'">
          {{ session?.playback_state_label || session?.playback_state || t('pptFocus.unknown') }}
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
        {{ isFullscreen ? t('pptFocus.exitFullscreen') : t('pptFocus.fullscreen') }}
      </FButton>
    </header>

    <main class="ppt-focus__stage" :data-orientation="orientationKey">
      <FMessageBar v-if="loadError" tone="error" :title="t('pptFocus.loadFailTitle')">
        {{ loadError }}
      </FMessageBar>

      <div v-if="isLoading" class="ppt-focus__loading">
        <FSpinner :size="32" />
        <span>{{ t('pptFocus.loadingPages') }}</span>
      </div>

      <template v-else-if="!session?.source_id">
        <FEmpty :title="t('pptFocus.noPptTitle')" :description="t('pptFocus.noPptDesc')" icon="document_24_regular">
          <template #actions>
            <FButton appearance="primary" @click="exitFocus">{{ t('pptFocus.back') }}</FButton>
          </template>
        </FEmpty>
      </template>

      <template v-else>
        <div class="ppt-focus__layout">
          <!--
            竖屏 (portrait) 时缩略图栏在视觉上隐藏，组件也不挂载，
            避免后台仍然发起几十/上百张缩略图请求并占用 DOM。
          -->
          <PptSlideRail
            v-if="isLandscape"
            class="ppt-focus__slide-rail"
            :items="thumbnailItems"
            :current-page="slidesProgress.current"
            :total-pages="slidesProgress.total"
            @jump="jumpToSlide"
          />

          <figure class="ppt-focus__current">
            <img v-if="slideImage" :src="slideImage" :alt="t('pptFocus.pageAlt', { n: slidesProgress.current })" />
            <div v-else class="ppt-focus__current-fallback">
              <FIcon name="document_24_regular" />
              <span>{{ t('pptFocus.pageAlt', { n: slidesProgress.current }) }}</span>
            </div>
          </figure>

          <aside class="ppt-focus__side">
            <div class="ppt-focus__next">
              <p class="ppt-focus__side-eyebrow">{{ t('pptFocus.nextEyebrow') }}</p>
              <img v-if="nextSlideImage" :src="nextSlideImage" :alt="t('pptFocus.nextAlt')" />
              <div v-else class="ppt-focus__next-fallback">{{ nextSlideNumber ?? '—' }}</div>
            </div>

            <div class="ppt-focus__progress">
              <p class="ppt-focus__side-eyebrow">{{ t('pptFocus.progressEyebrow') }}</p>
              <template v-if="slidesProgress.total > 0">
                <FProgress :value="slidesProgress.current" :max="slidesProgress.total" show-label />
                <p class="ppt-focus__progress-page">{{ t('pptFocus.progressPage', { current: slidesProgress.current, total: slidesProgress.total }) }}</p>
              </template>
              <p v-else class="ppt-focus__progress-page">{{ t('pptFocus.progressUnknown') }}</p>
            </div>

            <section class="ppt-focus__teleprompter">
              <header class="ppt-focus__teleprompter-head">
                <p class="ppt-focus__side-eyebrow">{{ t('pptFocus.prompterEyebrow') }}</p>
                <span class="ppt-focus__teleprompter-page">{{ t('pptFocus.prompterPage', { n: slidesProgress.current }) }}</span>
              </header>
              <div class="ppt-focus__teleprompter-body">
                <p v-if="teleprompterText" class="ppt-focus__teleprompter-text">{{ teleprompterText }}</p>
                <p v-else class="ppt-focus__teleprompter-empty">{{ t('pptFocus.prompterEmpty') }}</p>
              </div>
            </section>
          </aside>
        </div>

        <div class="ppt-focus__controls" :aria-label="t('pptFocus.controlsAria')">
          <div class="ppt-focus__media-picker">
            <FCombobox
              v-model="selectedMediaKey"
              :options="currentMediaOptions"
              :placeholder="mediaSelectPlaceholder"
              :disabled="isMediaPickerDisabled"
              :searchable="currentMediaOptions.length >= 10"
              :aria-label="t('pptFocus.mediaAria')"
              size="large"
            />
          </div>
          <FButton appearance="secondary" icon-start="previous_24_regular" @click="nav('prev')">
            {{ t('pptFocus.prevPage') }}
          </FButton>
          <FButton appearance="secondary" icon-start="pause_24_regular" :disabled="!canControlSelectedMedia" @click="controlSelectedMedia('pause')">
            {{ t('pptFocus.pauseMedia') }}
          </FButton>
          <FButton appearance="primary" icon-start="play_24_regular" :disabled="!canControlSelectedMedia" @click="controlSelectedMedia('play')">
            {{ t('pptFocus.playMedia') }}
          </FButton>
          <FButton appearance="secondary" icon-start="next_24_regular" @click="nav('next')">
            {{ t('pptFocus.nextPage') }}
          </FButton>
        </div>
      </template>
    </main>
  </div>
</template>

<style scoped src="./PptFocusView.css"></style>
