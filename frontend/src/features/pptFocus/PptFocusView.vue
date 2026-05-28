<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRoute, useRouter } from 'vue-router';
import {
  NAlert,
  NButton,
  NEmpty,
  NProgress,
  NSelect,
  NSpin,
  NTag,
} from 'naive-ui';

import FIcon from '@/design-system/FIcon.vue';
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
  })),
);

function mediaTypeHint(rawType: string): string {
  const key = rawType?.toLowerCase() as KnownMediaType;
  if (KNOWN_MEDIA_TYPES.has(key)) return t(`pptFocus.mediaType.${key}`);
  return t('pptFocus.mediaType.other');
}
void mediaTypeHint;

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

const slidesProgressPercentage = computed(() => {
  if (slidesProgress.value.total <= 0) return 0;
  return Math.round((slidesProgress.value.current / slidesProgress.value.total) * 100);
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
  try {
    if (document.fullscreenElement) {
      await document.exitFullscreen();
    } else if (document.documentElement.requestFullscreen) {
      await document.documentElement.requestFullscreen();
    }
  } catch {
    syncFullscreen();
  }
}

function exitFocus(): void {
  void router.push(`/display/${windowIdToSlug(windowId.value)}`);
}
</script>

<template>
  <div class="ppt-focus">
    <header class="ppt-focus__topbar">
      <n-button tertiary @click="exitFocus">
        <template #icon><FIcon name="arrow_left_24_regular" /></template>
        {{ t('pptFocus.back') }}
      </n-button>
      <div class="ppt-focus__topbar-center">
        <n-tag type="info" size="small" round>{{ windowLabel }}</n-tag>
        <span class="ppt-focus__topbar-title">{{ session?.source_name || t('pptFocus.noSourceSelected') }}</span>
        <n-tag :type="session?.playback_state === 'playing' ? 'success' : 'default'" size="small" round>
          {{ session?.playback_state_label || session?.playback_state || t('pptFocus.unknown') }}
        </n-tag>
        <span v-if="slidesProgress.total > 0" class="ppt-focus__topbar-progress">
          {{ slidesProgress.current }} / {{ slidesProgress.total }}
        </span>
      </div>
      <n-button tertiary @click="toggleFullscreen">
        <template #icon>
          <FIcon :name="isFullscreen ? 'full_screen_minimize_24_regular' : 'full_screen_maximize_24_regular'" />
        </template>
        {{ isFullscreen ? t('pptFocus.exitFullscreen') : t('pptFocus.fullscreen') }}
      </n-button>
    </header>

    <main class="ppt-focus__stage" :data-orientation="orientationKey">
      <n-alert v-if="loadError" type="error" :title="t('pptFocus.loadFailTitle')">
        {{ loadError }}
      </n-alert>

      <div v-if="isLoading" class="ppt-focus__loading">
        <n-spin :size="32" />
        <span>{{ t('pptFocus.loadingPages') }}</span>
      </div>

      <template v-else-if="!session?.source_id">
        <n-empty :description="t('pptFocus.noPptDesc')">
          <template #icon>
            <FIcon name="document_24_regular" />
          </template>
          <template #extra>
            <n-button type="primary" @click="exitFocus">{{ t('pptFocus.back') }}</n-button>
          </template>
        </n-empty>
      </template>

      <template v-else>
        <div class="ppt-focus__layout">
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
                <n-progress type="line" :percentage="slidesProgressPercentage" />
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
            <n-select
              v-model:value="selectedMediaKey"
              :options="currentMediaOptions"
              :placeholder="mediaSelectPlaceholder"
              :disabled="isMediaPickerDisabled"
              :filterable="currentMediaOptions.length >= 10"
              :aria-label="t('pptFocus.mediaAria')"
              size="large"
            />
          </div>
          <n-button @click="nav('prev')">
            <template #icon><FIcon name="previous_24_regular" /></template>
            <span class="ppt-focus__control-label">{{ t('pptFocus.prevPage') }}</span>
          </n-button>
          <n-button :disabled="!canControlSelectedMedia" @click="controlSelectedMedia('pause')">
            <template #icon><FIcon name="pause_24_regular" /></template>
            <span class="ppt-focus__control-label">{{ t('pptFocus.pauseMedia') }}</span>
          </n-button>
          <n-button type="primary" :disabled="!canControlSelectedMedia" @click="controlSelectedMedia('play')">
            <template #icon><FIcon name="play_24_regular" /></template>
            <span class="ppt-focus__control-label">{{ t('pptFocus.playMedia') }}</span>
          </n-button>
          <n-button @click="nav('next')">
            <template #icon><FIcon name="next_24_regular" /></template>
            <span class="ppt-focus__control-label">{{ t('pptFocus.nextPage') }}</span>
          </n-button>
        </div>
      </template>
    </main>
  </div>
</template>

<style scoped src="./PptFocusView.css"></style>
