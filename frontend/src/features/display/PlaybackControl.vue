<script setup lang="ts">
/**
 * 单窗口播放控制条：按 source_type 渲染不同分支
 *  - PPT：上一页 / 下一页 / 跳页 / PPT 进度条 / 当前页媒体子表
 *  - video：播放暂停停止 / 循环 / Seek（旧 audio 会话亦回退到本分支）
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
  NFormItem,
  NInput,
  NProgress,
  NSelect,
  NSlider,
  NSwitch,
  NTag,
} from 'naive-ui';

import FIcon from '@/design-system/FIcon.vue';
import { useDialog } from '@/composables/useDialog';
import { useToast } from '@/composables/useToast';
import { useThrottledSlider } from '@/composables/useThrottledSlider';
import { useSessionStore } from '@/stores/sessions';
import { useSourceStore } from '@/stores/sources';
import { formatDuration } from '@/design-system/utils';
import { api, type PptBackend, type PptResourceItem, type SessionSnapshot } from '@/services/api';
import { usePlaybackErrorGate } from './usePlaybackErrorGate';

const props = defineProps<{ session: SessionSnapshot }>();

const { t } = useI18n();
const dialog = useDialog();
const toast = useToast();
const sessionStore = useSessionStore();
const sourceStore = useSourceStore();

const category = computed(() => sourceStore.resolveCategory(props.session.source_type));

type NTagType = 'default' | 'primary' | 'info' | 'success' | 'warning' | 'error';

const stateType = computed<NTagType>(() => {
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
const selectedPptBackend = ref<PptBackend>('libreoffice');

watch(
  () => props.session.current_slide,
  (slide) => {
    if (category.value === 'ppt' && slide > 0) {
      jumpInput.value = String(slide);
    }
  },
  { immediate: true },
);

watch(
  () => props.session.ppt_backend,
  (backend) => {
    selectedPptBackend.value = backend || 'libreoffice';
  },
  { immediate: true },
);

const pptBackendOptions = computed(() => [
  { label: t('sources.pptBackend.libreoffice'), value: 'libreoffice' },
  { label: t('sources.pptBackend.powerpoint'), value: 'powerpoint' },
  { label: t('sources.pptBackend.wps'), value: 'wps' },
]);

function pptBackendLabel(backend: PptBackend): string {
  return t(`sources.pptBackend.${backend}`);
}

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

function onSeek(positionMs: number): void {
  void call(
    () => sessionStore.navigate(props.session.window_id, 'seek', 0, positionMs),
    t('playback.seekFail'),
  );
}

function onClose(): void {
  void call(() => sessionStore.closeSource(props.session.window_id), t('playback.closeFail'));
}

async function onPptBackendChange(nextBackend: PptBackend): Promise<void> {
  const previousBackend = props.session.ppt_backend || 'libreoffice';
  if (nextBackend === previousBackend) return;
  const backendLabel = pptBackendLabel(nextBackend);
  const confirmed = await dialog.confirm({
    title: t('playback.switchPptBackendTitle'),
    description: t('playback.switchPptBackendDesc', { backend: backendLabel }),
    confirmLabel: t('playback.switchPptBackendConfirm'),
    cancelLabel: t('common.cancel'),
  });
  if (!confirmed) {
    selectedPptBackend.value = previousBackend;
    return;
  }
  await call(() => sessionStore.switchPptBackend(props.session.window_id, nextBackend), t('playback.switchPptBackendFail'));
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
  () => [category.value, props.session.source_id, props.session.current_slide] as const,
  loadPptResources,
  { immediate: true },
);

const currentResource = computed(() =>
  pptResources.value.find((res) => res.page_index === props.session.current_slide),
);

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

const seekValue = computed(() => Math.min(props.session.duration_ms, Math.max(0, props.session.position_ms)));

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
      <div>
        <n-tag :type="stateType" round size="small">
          {{ session.playback_state_label || session.playback_state }}
        </n-tag>
        <h3 class="playback-control__source-name">
          {{ session.source_name || t('playback.notOpened') }}
        </h3>
        <p class="playback-control__caption">
          {{ session.source_type_label || t('playback.idle') }}
          <template v-if="session.is_spliced">· {{ session.spliced_display_label || t('playback.spliced') }}</template>
        </p>
      </div>
      <RouterLink v-if="category === 'ppt' && session.source_id" :to="`/ppt-focus/${session.window_id}`"
        class="playback-control__focus-link">
        <FIcon name="arrow_maximize_24_regular" />
        <span>{{ t('playback.focusLink') }}</span>
      </RouterLink>
    </header>

    <n-alert v-if="showErrorBar" type="error" :title="errorBarTitle" closable @close="dismissErrorBar">
      <div class="playback-control__alert-body">
        <span>{{ errorBarDescription }}</span>
        <n-button size="small" :disabled="!session.source_id" @click="reopenCurrentSource">
          {{ t('playback.reopen') }}
        </n-button>
      </div>
    </n-alert>

    <section v-if="category === 'ppt'" class="playback-control__section">
      <n-form-item :label="t('playback.pptBackend')" :feedback="t('playback.pptBackendHint')">
        <n-select v-model:value="selectedPptBackend" :options="pptBackendOptions" @update:value="onPptBackendChange" />
      </n-form-item>
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

      <div v-if="currentResource && currentResource.media_items.length > 0" class="playback-control__media">
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
          <n-switch :value="session.loop_enabled" @update:value="onLoopToggle" />
        </div>
      </div>
      <div v-if="session.duration_ms > 0" class="playback-control__row playback-control__row--seek">
        <n-slider
          :value="seekValue"
          :min="0"
          :max="session.duration_ms"
          :step="1000"
          :aria-label="t('playback.seekAria')"
          class="playback-control__seek"
          @update:value="onSeek"
        />
        <span class="playback-control__progress-label">
          {{ formatDuration(session.position_ms) }} / {{ formatDuration(session.duration_ms) }}
        </span>
      </div>
    </section>

    <section v-else-if="category === 'image' || category === 'web'" class="playback-control__section">
      <p v-if="session.source_uri" class="playback-control__uri">{{ session.source_uri }}</p>
      <p v-else class="playback-control__uri">{{ t('playback.uriMissing') }}</p>
    </section>

    <section v-else-if="category === 'stream'" class="playback-control__section">
      <n-tag :type="session.source_uri ? 'warning' : 'default'" round size="small">
        {{ session.source_uri ? t('playback.live') : t('playback.notStreaming') }}
      </n-tag>
      <p v-if="session.source_uri" class="playback-control__uri">{{ session.source_uri }}</p>
    </section>

    <section v-else class="playback-control__section">
      <p class="playback-control__caption">{{ t('playback.noSource') }}</p>
    </section>

    <section class="playback-control__section">
      <div class="playback-control__row">
        <span class="playback-control__field-label">{{ t('playback.windowVolume') }}</span>
        <n-slider
          :value="windowVolume.value.value"
          :min="0"
          :max="100"
          :aria-label="t('playback.windowVolumeAria')"
          :disabled="category === 'image' || category === 'web'"
          class="playback-control__seek"
          @update:value="windowVolume.handleInput"
          @dragend="windowVolume.handleChange(windowVolume.value.value)"
        />
      </div>
      <div class="playback-control__row">
        <div class="playback-control__switch">
          <span>{{ t('playback.windowMute') }}</span>
          <n-switch
            :value="session.is_muted"
            :disabled="category === 'image' || category === 'web'"
            @update:value="onMuteToggle"
          />
        </div>
        <n-button type="error" :disabled="!session.source_id" @click="onClose">
          <template #icon><FIcon name="dismiss_24_regular" /></template>
          {{ t('playback.closeDisplay') }}
        </n-button>
      </div>
    </section>
  </div>
</template>

<style scoped>
.playback-control {
  display: flex;
  flex-direction: column;
  gap: var(--spacingVerticalL);
}

.playback-control__heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--spacingHorizontalL);
}

.playback-control__source-name {
  margin: var(--spacingVerticalXS) 0 0;
  font-size: var(--fontSizeBase600);
  line-height: var(--lineHeightBase600);
  font-weight: 600;
}

.playback-control__caption {
  margin: var(--spacingVerticalXS) 0 0;
  color: var(--colorNeutralForeground2);
  font-size: var(--fontSizeBase200);
}

.playback-control__focus-link {
  display: inline-flex;
  align-items: center;
  gap: var(--spacingHorizontalXS);
  padding: var(--spacingVerticalS) var(--spacingHorizontalM);
  border-radius: var(--borderRadiusMedium);
  background: var(--colorBrandBackground2);
  color: var(--colorBrandForeground1);
  font-weight: 600;
  text-decoration: none;
}

.playback-control__focus-link:hover {
  background: var(--colorBrandBackground);
  color: #ffffff;
}

.playback-control__section {
  display: flex;
  flex-direction: column;
  gap: var(--spacingVerticalM);
  padding: var(--spacingVerticalL);
  border-radius: var(--borderRadiusLarge);
  background: var(--colorNeutralBackground2);
  border: 1px solid var(--colorNeutralStroke2);
}

.playback-control__row {
  display: flex;
  align-items: center;
  gap: var(--spacingHorizontalM);
  flex-wrap: wrap;
}

.playback-control__jump {
  display: inline-flex;
  align-items: center;
  gap: var(--spacingHorizontalS);
  flex: 0 0 auto;
}

.playback-control__jump :deep(.n-input) {
  width: 96px;
}

.playback-control__row--progress,
.playback-control__row--seek {
  align-items: center;
  flex-wrap: nowrap;
}

.playback-control__progress,
.playback-control__seek {
  flex: 1 1 auto;
}

.playback-control__progress-label {
  font-variant-numeric: tabular-nums;
  color: var(--colorNeutralForeground2);
  flex-shrink: 0;
}

.playback-control__switch {
  display: inline-flex;
  align-items: center;
  gap: var(--spacingHorizontalS);
}

.playback-control__media-title {
  margin: 0;
  font-size: var(--fontSizeBase400);
  font-weight: 600;
}

.playback-control__media-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--spacingVerticalXS);
}

.playback-control__media-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacingHorizontalM);
  padding: var(--spacingVerticalS) var(--spacingHorizontalM);
  background: var(--colorNeutralBackground1);
  border: 1px solid var(--colorNeutralStroke2);
  border-radius: var(--borderRadiusMedium);
}

.playback-control__media-name {
  flex: 1 1 auto;
  font-weight: 500;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.playback-control__media-actions {
  display: inline-flex;
  align-items: center;
  gap: var(--spacingHorizontalXS);
}

.playback-control__uri {
  margin: 0;
  font-family: var(--fontFamilyMonospace);
  color: var(--colorNeutralForeground2);
  word-break: break-all;
}

.playback-control__field-label {
  flex: 0 0 96px;
  font-weight: 600;
}

@media (max-width: 767px) {
  .playback-control__heading {
    flex-direction: column;
    gap: var(--spacingVerticalS);
  }

  .playback-control__row {
    align-items: stretch;
    flex-direction: column;
  }

  .playback-control__field-label {
    flex: 0 0 auto;
  }
}
</style>
