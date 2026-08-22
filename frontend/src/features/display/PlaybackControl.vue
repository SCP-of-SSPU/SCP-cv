<script setup lang="ts">
/**
 * 单窗口播放控制条：按 source_type 渲染不同分支
 *  - PPT：上一页 / 下一页 / 跳页 / PPT 进度条 / 当前页媒体子表
 *  - video：播放暂停停止 / 循环 / Seek
 *  - image / web：仅展示 URI + 关闭按钮
 *  - *_stream：直播状态 Tag + URI（无 Seek）
 *
 * 音量调节走 useThrottledSlider：拖动期间节流上报、抬手再 flush 一次，
 * 避免高频 PATCH 与 SSE 回写在拖动中竞态导致滑块回弹/卡顿。
 */
import { computed, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { RouterLink } from 'vue-router';
import {
  NAlert,
  NButton,
  NInput,
  NProgress,
  NSlider,
  NSwitch,
  NTag,
} from 'naive-ui';

import FIcon from '@/design-system/FIcon.vue';
import { sliderAriaLabel as vSliderAriaLabel } from '@/design-system/sliderAriaLabel';
import SourceThumbnail from '@/features/sources/SourceThumbnail.vue';
import { useToast } from '@/composables/useToast';
import { useThrottledSlider } from '@/composables/useThrottledSlider';
import { useSessionStore } from '@/stores/sessions';
import { useSourceStore } from '@/stores/sources';
import { formatDuration } from '@/design-system/utils';
import { api, buildBackendUrl, type PptResourceItem, type SessionSnapshot } from '@/services/api';
import { usePlaybackErrorGate } from './usePlaybackErrorGate';

const props = defineProps<{ session: SessionSnapshot }>();

const { t } = useI18n();
const toast = useToast();
const sessionStore = useSessionStore();
const sourceStore = useSourceStore();

const category = computed(() => sourceStore.resolveCategory(props.session.source_type));
const isPdfMode = computed(() => props.session.playback_mode === 'pdf');
const currentSource = computed(() => sourceStore.findById(props.session.source_id) ?? null);

type NTagType = 'default' | 'primary' | 'info' | 'success' | 'warning' | 'error';

const stateType = computed<NTagType>(() => {
  if (!props.session.source_id) return 'default';
  switch (props.session.playback_state) {
    case 'playing':
      return 'success';
    case 'paused':
    case 'loading':
      return 'warning';
    case 'error':
      return 'error';
    case 'idle':
    default:
      return 'default';
  }
});

const jumpInput = ref<string>('');

watch(
  () => props.session.current_slide,
  (slide) => {
    if (category.value === 'ppt' && slide > 0) {
      jumpInput.value = String(slide);
    }
  },
  { immediate: true },
);

async function call(action: () => Promise<void>, errorTitle: string): Promise<void> {
  try {
    await action();
  } catch (error) {
    toast.error(errorTitle, error instanceof Error ? error.message : t('common.retry'));
  }
}

function onPlay(): void {
  void call(() => sessionStore.control(props.session.window_id, 'play'), t('playback.playFail'));
}
function onPause(): void {
  void call(() => sessionStore.control(props.session.window_id, 'pause'), t('playback.pauseFail'));
}
function onStop(): void {
  void call(() => sessionStore.control(props.session.window_id, 'stop'), t('playback.stopFail'));
}
function onPrev(): void {
  void call(() => sessionStore.navigate(props.session.window_id, 'prev'), t('playback.navFail'));
}
function onNext(): void {
  void call(() => sessionStore.navigate(props.session.window_id, 'next'), t('playback.navFail'));
}
function onJump(): void {
  const target = Number.parseInt(jumpInput.value, 10);
  if (!Number.isFinite(target) || target <= 0) {
    toast.warning(t('playback.pageInvalid'), t('playback.pageInvalidDetail'));
    return;
  }
  void call(() => sessionStore.navigate(props.session.window_id, 'goto', target), t('playback.jumpFail'));
}

function onLoopToggle(value: boolean): void {
  void call(() => sessionStore.setLoop(props.session.window_id, value), t('playback.loopFail'));
}

function onMuteToggle(value: boolean): void {
  void call(() => sessionStore.setWindowMute(props.session.window_id, value), t('playback.windowMuteFail'));
}

const windowVolume = useThrottledSlider(
  () => props.session.volume,
  {
    commit: (value: number) => sessionStore.setWindowVolume(props.session.window_id, value),
    onError: (error) => {
      toast.error(t('playback.volumeFail'), error instanceof Error ? error.message : t('common.retry'));
    },
  },
);

const seekValue = computed(() => Math.min(props.session.duration_ms, Math.max(0, props.session.position_ms)));

const videoSeek = useThrottledSlider(
  () => seekValue.value,
  {
    commit: (positionMs: number) => sessionStore.navigate(props.session.window_id, 'seek', 0, positionMs),
    onError: (error) => toast.error(t('playback.seekFail'), error instanceof Error ? error.message : t('common.retry')),
  },
);

function onClose(): void {
  void call(() => sessionStore.closeSource(props.session.window_id), t('playback.closeFail'));
}

const pptResources = ref<PptResourceItem[]>([]);
const pptError = ref('');

async function loadPptResources(): Promise<void> {
  if (category.value !== 'ppt' || !props.session.source_id) {
    pptResources.value = [];
    return;
  }
  try {
    pptError.value = '';
    const payload = await api.listPptResources(props.session.source_id);
    pptResources.value = payload.resources;
  } catch (error) {
    pptError.value = error instanceof Error ? error.message : t('playback.loadFailGeneric');
  }
}

watch(
  () => [category.value, props.session.source_id] as const,
  loadPptResources,
  { immediate: true },
);

const currentResource = computed(() =>
  pptResources.value.find((res) => res.page_index === props.session.current_slide),
);
const currentPagePreviewUrl = computed(() => {
  if (category.value !== 'ppt' || !currentResource.value?.slide_image) return '';
  return buildBackendUrl(currentResource.value.slide_image);
});

async function pptMediaAction(mediaId: string, mediaIndex: number, action: string): Promise<void> {
  try {
    await sessionStore.controlPptMedia(props.session.window_id, action, mediaId, mediaIndex);
  } catch (error) {
    toast.error(t('playback.pptMediaFail'), error instanceof Error ? error.message : t('common.retry'));
  }
}

const pptProgressLabel = computed(() => {
  if (props.session.total_slides <= 0) return '';
  return `${props.session.current_slide} / ${props.session.total_slides}`;
});

const pptProgressPercentage = computed(() => {
  if (props.session.total_slides <= 0) return 0;
  return Math.round((props.session.current_slide / props.session.total_slides) * 100);
});

const isPlaying = computed(() => props.session.playback_state === 'playing');

async function reopenCurrentSource(): Promise<void> {
  if (!props.session.source_id) return;
  try {
    await sessionStore.openSource(props.session.window_id, props.session.source_id, true);
    toast.info(t('playback.reopenOk'), t('playback.reopenOkDetail'));
  } catch (error) {
    toast.error(t('playback.reopenFail'), error instanceof Error ? error.message : t('common.retry'));
  }
}

async function refreshWebSource(): Promise<void> {
  if (!props.session.source_id) return;
  try {
    await sessionStore.control(props.session.window_id, 'play');
    toast.info(t('playback.refreshOk'));
  } catch (error) {
    toast.error(t('playback.refreshFail'), error instanceof Error ? error.message : t('common.retry'));
  }
}

const { showErrorBar, dismissErrorBar } = usePlaybackErrorGate({
  session: () => props.session,
  category: () => category.value,
});

const adapterErrorMessage = computed(() => (props.session.error_message || '').trim());
const errorBarTitle = computed(() => {
  if (!adapterErrorMessage.value && category.value === 'stream') return t('playback.streamNotReady');
  return category.value === 'stream' ? t('playback.streamError') : t('playback.playerError');
});
const errorBarDescription = computed(() => {
  if (adapterErrorMessage.value) return adapterErrorMessage.value;
  if (category.value === 'stream') {
    return t('playback.streamErrorDesc');
  }
  return t('playback.genericErrorDesc');
});
</script>

<template>
  <div class="playback-control">
    <header class="playback-control__heading">
      <div class="playback-control__identity">
        <SourceThumbnail v-if="currentSource" :source="currentSource" size="comfortable" />
        <div>
          <n-tag :type="stateType" round size="small">
            {{ session.source_id ? (session.playback_state_label || session.playback_state) : t('playback.idle') }}
          </n-tag>
          <h3 class="playback-control__source-name">
            {{ session.source_id ? (session.source_name || t('playback.notOpened')) : t('playback.noSource') }}
          </h3>
          <p class="playback-control__caption">
            {{ session.source_id ? (session.source_type_label || t('playback.idle')) : t('playback.noSource') }}
            <template v-if="session.is_spliced">· {{ session.spliced_display_label || t('playback.spliced') }}</template>
            <n-tag v-if="category === 'ppt' && session.playback_mode === 'pdf'" type="info" round size="small">
              {{ t('playback.pdfBadge') }}
            </n-tag>
            <n-tag v-else-if="category === 'ppt' && session.playback_mode === 'powerpoint'" type="warning" round size="small">
              {{ t('playback.powerpointBadge') }}
            </n-tag>
          </p>
        </div>
      </div>
      <RouterLink v-if="category === 'ppt' && session.source_id" :to="`/ppt-focus/${session.window_id}`"
        class="playback-control__focus-link">
        <FIcon name="arrow_maximize_24_regular" />
        <span>{{ t('playback.focusLink') }}</span>
      </RouterLink>
    </header>

    <section v-if="currentSource" class="playback-control__monitor" aria-live="polite">
      <SourceThumbnail :source="currentSource" size="stage" :image-url="currentPagePreviewUrl" />
      <div class="playback-control__monitor-copy">
        <span class="playback-control__monitor-eyebrow">{{ t('playback.currentOutput') }}</span>
        <strong>{{ currentSource.name }}</strong>
        <span>{{ t('playback.previewReference') }}</span>
      </div>
    </section>

    <n-alert v-if="showErrorBar" type="error" :title="errorBarTitle" closable @close="dismissErrorBar">
      <div class="playback-control__alert-body">
        <span>{{ errorBarDescription }}</span>
        <n-button size="small" :disabled="!session.source_id" @click="reopenCurrentSource">
          {{ t('playback.reopen') }}
        </n-button>
      </div>
    </n-alert>

    <section v-if="category === 'ppt'" class="playback-control__section">
      <div class="playback-control__row playback-control__row--ppt">
        <n-button @click="onPrev">
          <template #icon><FIcon name="previous_24_regular" /></template>
          {{ t('playback.prevPage') }}
        </n-button>
        <n-button type="primary" @click="onNext">
          <template #icon><FIcon name="next_24_regular" /></template>
          {{ t('playback.nextPage') }}
        </n-button>
        <div class="playback-control__jump">
          <n-input v-model:value="jumpInput" type="text" :placeholder="t('playback.jumpPlaceholder')" :maxlength="4" />
          <n-button @click="onJump">{{ t('playback.jump') }}</n-button>
        </div>
      </div>
      <div v-if="session.total_slides > 0" class="playback-control__row playback-control__row--progress">
        <n-progress
          type="line"
          :percentage="pptProgressPercentage"
          :show-indicator="false"
          class="playback-control__progress"
        />
        <span class="playback-control__progress-label">{{ pptProgressLabel }}</span>
      </div>

      <n-alert v-if="pptError" type="error" :title="t('playback.pptLoadFail')">
        {{ pptError }}
      </n-alert>

      <div v-if="!isPdfMode && currentResource && currentResource.media_items.length > 0" class="playback-control__media">
        <h4 class="playback-control__media-title">{{ t('playback.currentMedia') }}</h4>
        <ul class="playback-control__media-list">
          <li v-for="media in currentResource.media_items" :key="media.id" class="playback-control__media-item">
            <span class="playback-control__media-name">{{ media.name }}</span>
            <span class="playback-control__media-actions">
              <n-button size="small" circle :aria-label="t('playback.playMedia')"
                @click="pptMediaAction(media.id, media.media_index, 'play')">
                <template #icon><FIcon name="play_24_regular" /></template>
              </n-button>
              <n-button size="small" circle :aria-label="t('playback.pauseMedia')"
                @click="pptMediaAction(media.id, media.media_index, 'pause')">
                <template #icon><FIcon name="pause_24_regular" /></template>
              </n-button>
              <n-button size="small" circle type="error" :aria-label="t('playback.stopMedia')"
                @click="pptMediaAction(media.id, media.media_index, 'stop')">
                <template #icon><FIcon name="stop_24_regular" /></template>
              </n-button>
            </span>
          </li>
        </ul>
      </div>
    </section>

    <section v-else-if="category === 'video'" class="playback-control__section">
      <div class="playback-control__row">
        <n-button v-if="!isPlaying" type="primary" @click="onPlay">
          <template #icon><FIcon name="play_24_regular" /></template>
          {{ t('playback.play') }}
        </n-button>
        <n-button v-else type="primary" @click="onPause">
          <template #icon><FIcon name="pause_24_regular" /></template>
          {{ t('playback.pause') }}
        </n-button>
        <n-button @click="onStop">
          <template #icon><FIcon name="stop_24_regular" /></template>
          {{ t('playback.stop') }}
        </n-button>
        <div class="playback-control__switch">
          <span>{{ t('playback.loop') }}</span>
          <n-switch :value="session.loop_enabled" :aria-label="t('playback.loop')"
            @update:value="onLoopToggle" />
        </div>
      </div>
      <div v-if="session.duration_ms > 0" class="playback-control__row playback-control__row--seek">
        <n-slider
          v-slider-aria-label="t('playback.seekAria')"
          :value="videoSeek.value.value"
          :min="0"
          :max="session.duration_ms"
          :step="1000"
          :aria-label="t('playback.seekAria')"
          class="playback-control__seek"
          @update:value="videoSeek.handleInput"
          @dragend="videoSeek.handleChange(videoSeek.value.value)"
          @keyup="videoSeek.handleChange(videoSeek.value.value)"
        />
        <span class="playback-control__progress-label">
          {{ formatDuration(session.position_ms) }} / {{ formatDuration(session.duration_ms) }}
        </span>
      </div>
    </section>

    <section v-else-if="category === 'image' || category === 'web'" class="playback-control__section">
      <p v-if="session.source_uri" class="playback-control__uri">{{ session.source_uri }}</p>
      <p v-else class="playback-control__uri">{{ t('playback.uriMissing') }}</p>
      <n-button v-if="category === 'web'" size="small" :disabled="!session.source_id" @click="refreshWebSource">
        <template #icon><FIcon name="arrow_clockwise_24_regular" /></template>
        {{ t('playback.refresh') }}
      </n-button>
    </section>

    <section v-else-if="category === 'stream'" class="playback-control__section">
      <n-tag :type="session.source_uri ? 'warning' : 'default'" round size="small">
        {{ session.source_uri ? t('playback.live') : t('playback.notStreaming') }}
      </n-tag>
      <p v-if="session.source_uri" class="playback-control__uri">{{ session.source_uri }}</p>
      <n-button size="small" :disabled="!session.source_id" @click="refreshWebSource">
        <template #icon><FIcon name="arrow_clockwise_24_regular" /></template>
        {{ t('playback.refresh') }}
      </n-button>
    </section>

    <section v-else class="playback-control__section">
      <p class="playback-control__caption">{{ t('playback.noSource') }}</p>
    </section>

    <section class="playback-control__section">
      <div class="playback-control__row">
        <span class="playback-control__field-label">{{ t('playback.windowVolume') }}</span>
        <n-slider
          v-slider-aria-label="t('playback.windowVolumeAria')"
          :value="windowVolume.value.value"
          :min="0"
          :max="100"
          :aria-label="t('playback.windowVolumeAria')"
          :disabled="!session.source_id || category === 'audio' || category === 'image' || category === 'web'"
          class="playback-control__seek"
          @update:value="windowVolume.handleInput"
          @dragend="windowVolume.handleChange(windowVolume.value.value)"
          @keyup="windowVolume.handleChange(windowVolume.value.value)"
        />
      </div>
      <div class="playback-control__row">
        <div class="playback-control__switch">
          <span>{{ t('playback.windowMute') }}</span>
          <n-switch
            :value="session.is_muted"
            :aria-label="t('playback.windowMute')"
            :disabled="!session.source_id || category === 'audio' || category === 'image' || category === 'web'"
            @update:value="onMuteToggle"
          />
        </div>
        <n-button v-if="session.source_id" type="error" @click="onClose">
          <template #icon><FIcon name="dismiss_24_regular" /></template>
          {{ t('playback.closeDisplay') }}
        </n-button>
      </div>
    </section>
  </div>
</template>

<style scoped src="./PlaybackControl.css"></style>
