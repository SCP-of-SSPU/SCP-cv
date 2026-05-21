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
  FButton,
  FIcon,
  FInput,
  FProgress,
  FSlider,
  FSwitch,
  FTag,
  FMessageBar,
} from '@/design-system';
import type { TagTone } from '@/design-system';
import { useToast } from '@/composables/useToast';
import { useThrottledSlider } from '@/composables/useThrottledSlider';
import { useSessionStore } from '@/stores/sessions';
import { useSourceStore } from '@/stores/sources';
import { formatDuration } from '@/design-system/utils';
import { api, type PptResourceItem, type SessionSnapshot } from '@/services/api';
import { usePlaybackErrorGate } from './usePlaybackErrorGate';

const props = defineProps<{ session: SessionSnapshot }>();

const { t } = useI18n();
const toast = useToast();
const sessionStore = useSessionStore();
const sourceStore = useSourceStore();

const category = computed(() => sourceStore.resolveCategory(props.session.source_type));

const stateTone = computed<TagTone>(() => {
  switch (props.session.playback_state) {
    case 'playing':
      return 'success';
    case 'paused':
      return 'warning';
    case 'loading':
      return 'warning';
    case 'error':
      return 'error';
    case 'idle':
      return 'subtle';
    default:
      return 'neutral';
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
  // 后端 PlaybackCommand 中跳页指令命名为 GOTO；早先误传 'jump' 会被
  // services.playback.navigate_content 校验为「无效的导航动作」，跳转无效。
  void call(() => sessionStore.navigate(props.session.window_id, 'goto', target), t('playback.jumpFail'));
}

function onLoopToggle(value: boolean): void {
  void call(() => sessionStore.setLoop(props.session.window_id, value), t('playback.loopFail'));
}

function onMuteToggle(value: boolean): void {
  void call(() => sessionStore.setWindowMute(props.session.window_id, value), t('playback.windowMuteFail'));
}

// 窗口音量节流：拖动每 ~120 ms 上报一次，抬手再 flush，
// SSE 回写在拖动 / 飞行 / 待发期间不会覆盖本地 UI 值。
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

// 后端 PptResource.page_index 与 session.current_slide 都是 1-based，
// 这里直接对齐即可；旧实现 `- 1` 会取到前一页，使「当前页媒体」比实际播放慢一页。
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

const seekValue = computed(() => Math.min(props.session.duration_ms, Math.max(0, props.session.position_ms)));

const isPlaying = computed(() => props.session.playback_state === 'playing');

/*
 * 直播首帧握手期间可能短暂 error；错误条由 usePlaybackErrorGate 延迟确认。
 */
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
        <FTag :tone="stateTone">
          {{ session.playback_state_label || session.playback_state }}
        </FTag>
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

    <FMessageBar v-if="showErrorBar" tone="error" :title="errorBarTitle" dismissible @dismiss="dismissErrorBar">
      {{ errorBarDescription }}
      <template #actions>
        <FButton appearance="secondary" size="compact" :disabled="!session.source_id" @click="reopenCurrentSource">
          {{ t('playback.reopen') }}
        </FButton>
      </template>
    </FMessageBar>

    <!-- PPT 控制 -->
    <section v-if="category === 'ppt'" class="playback-control__section">
      <div class="playback-control__row playback-control__row--ppt">
        <FButton appearance="secondary" icon-start="previous_24_regular" @click="onPrev">{{ t('playback.prevPage') }}</FButton>
        <FButton appearance="primary" icon-start="next_24_regular" @click="onNext">{{ t('playback.nextPage') }}</FButton>
        <div class="playback-control__jump">
          <FInput v-model="jumpInput" type="number" :placeholder="t('playback.jumpPlaceholder')" :max-length="4" />
          <FButton appearance="secondary" @click="onJump">{{ t('playback.jump') }}</FButton>
        </div>
      </div>
      <div v-if="session.total_slides > 0" class="playback-control__row playback-control__row--progress">
        <FProgress :value="session.current_slide" :max="session.total_slides" />
        <span class="playback-control__progress-label">{{ pptProgressLabel }}</span>
      </div>

      <FMessageBar v-if="pptError" tone="error" :title="t('playback.pptLoadFail')">
        {{ pptError }}
      </FMessageBar>

      <div v-if="currentResource && currentResource.media_items.length > 0" class="playback-control__media">
        <h4 class="playback-control__media-title">{{ t('playback.currentMedia') }}</h4>
        <ul class="playback-control__media-list">
          <li v-for="media in currentResource.media_items" :key="media.id" class="playback-control__media-item">
            <span class="playback-control__media-name">{{ media.name }}</span>
            <span class="playback-control__media-actions">
              <FButton size="compact" icon-only icon-start="play_24_regular" :aria-label="t('playback.playMedia')"
                @click="pptMediaAction(media.id, media.media_index, 'play')" />
              <FButton size="compact" icon-only icon-start="pause_24_regular" :aria-label="t('playback.pauseMedia')"
                @click="pptMediaAction(media.id, media.media_index, 'pause')" />
              <FButton size="compact" icon-only icon-start="stop_24_regular" :aria-label="t('playback.stopMedia')" appearance="danger"
                @click="pptMediaAction(media.id, media.media_index, 'stop')" />
            </span>
          </li>
        </ul>
      </div>
    </section>

    <!-- 视频控制（旧 audio 源回退至此分支） -->
    <section v-else-if="category === 'video'" class="playback-control__section">
      <div class="playback-control__row">
        <FButton v-if="!isPlaying" appearance="primary" icon-start="play_24_regular" @click="onPlay">
          {{ t('playback.play') }}
        </FButton>
        <FButton v-else appearance="primary" icon-start="pause_24_regular" @click="onPause">
          {{ t('playback.pause') }}
        </FButton>
        <FButton appearance="secondary" icon-start="stop_24_regular" @click="onStop">{{ t('playback.stop') }}</FButton>
        <FSwitch :model-value="session.loop_enabled" :label="t('playback.loop')" @update:modelValue="onLoopToggle" />
      </div>
      <div v-if="session.duration_ms > 0" class="playback-control__row playback-control__row--seek">
        <FSlider :model-value="seekValue" :min="0" :max="session.duration_ms" :step="1000" :aria-label="t('playback.seekAria')"
          @update:modelValue="onSeek" />
        <span class="playback-control__progress-label">
          {{ formatDuration(session.position_ms) }} / {{ formatDuration(session.duration_ms) }}
        </span>
      </div>
    </section>

    <!-- 图片 / 网页 -->
    <section v-else-if="category === 'image' || category === 'web'" class="playback-control__section">
      <p v-if="session.source_uri" class="playback-control__uri">{{ session.source_uri }}</p>
      <p v-else class="playback-control__uri">{{ t('playback.uriMissing') }}</p>
    </section>

    <!-- 直播 -->
    <section v-else-if="category === 'stream'" class="playback-control__section">
      <FTag :tone="session.source_uri ? 'warning' : 'subtle'" :dot="!!session.source_uri">
        {{ session.source_uri ? t('playback.live') : t('playback.notStreaming') }}
      </FTag>
      <p v-if="session.source_uri" class="playback-control__uri">{{ session.source_uri }}</p>
    </section>

    <section v-else class="playback-control__section">
      <p class="playback-control__caption">{{ t('playback.noSource') }}</p>
    </section>

    <!-- 通用：窗口音量、关闭显示 -->
    <section class="playback-control__section">
      <div class="playback-control__row">
        <span class="playback-control__field-label">{{ t('playback.windowVolume') }}</span>
        <FSlider :model-value="windowVolume.value.value" :min="0" :max="100" :aria-label="t('playback.windowVolumeAria')" show-value
          :disabled="category === 'image' || category === 'web'" @update:modelValue="windowVolume.handleInput"
          @change="windowVolume.handleChange" />
      </div>
      <div class="playback-control__row">
        <FSwitch :model-value="session.is_muted" :label="t('playback.windowMute')" :disabled="category === 'image' || category === 'web'"
          @update:modelValue="onMuteToggle" />
        <FButton appearance="danger" icon-start="dismiss_24_regular" :disabled="!session.source_id" @click="onClose">
          {{ t('playback.closeDisplay') }}
        </FButton>
      </div>
    </section>
  </div>
</template>

<style scoped>
.playback-control {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-l);
}

.playback-control__heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--spacing-l);
}

.playback-control__source-name {
  margin: var(--spacing-xs) 0 0;
  font-size: var(--fontSizeBase600);
  line-height: var(--lineHeightBase600);
  font-weight: 600;
}

.playback-control__caption {
  margin: var(--spacing-xs) 0 0;
  color: var(--colorNeutralForeground2);
  font-size: var(--fontSizeBase200);
}

.playback-control__focus-link {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-xs);
  padding: var(--spacing-s) var(--spacing-m);
  border-radius: var(--borderRadiusMedium);
  background: var(--colorBrandBackgroundSelected);
  color: var(--colorBrandForeground1);
  font-weight: 600;
  text-decoration: none;
  box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--colorBrandBackground) 18%, transparent);
  transition:
    background var(--motion-duration-medium) var(--motion-curve-ease),
    color var(--motion-duration-medium) var(--motion-curve-ease),
    box-shadow var(--motion-duration-medium) var(--motion-curve-ease),
    transform var(--motion-duration-medium) var(--motion-curve-ease);
}

.playback-control__focus-link:hover {
  background: var(--colorBrandBackground);
  color: var(--color-text-inverse);
  transform: translateY(-1px);
  box-shadow: var(--shadow-brand);
}

.playback-control__focus-link:focus-visible {
  outline: none;
  box-shadow: var(--shadow-focus);
}

.playback-control__section {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-m);
  padding: var(--spacing-l);
  border-radius: var(--borderRadiusLarge);
  background: var(--colorNeutralBackground2);
  border: 1px solid var(--colorNeutralStroke2);
}

.playback-control__row {
  display: flex;
  align-items: center;
  gap: var(--spacing-m);
  flex-wrap: wrap;
}

.playback-control__row--ppt {
  align-items: stretch;
}

.playback-control__jump {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-s);
  flex: 0 0 auto;
}

.playback-control__jump :deep(.f-input) {
  width: 96px;
}

.playback-control__row--progress,
.playback-control__row--seek {
  align-items: center;
  flex-wrap: nowrap;
}

.playback-control__progress-label {
  font-variant-numeric: tabular-nums;
  color: var(--colorNeutralForeground2);
  flex-shrink: 0;
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
  gap: var(--spacing-xs);
}

.playback-control__media-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-m);
  padding: var(--spacing-s) var(--spacing-m);
  background: var(--color-background-card);
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
  gap: var(--spacing-xs);
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
    gap: var(--spacing-s);
  }

  .playback-control__row {
    align-items: stretch;
    flex-direction: column;
  }

  .playback-control__row :deep(.f-button) {
    width: 100%;
  }

  .playback-control__field-label {
    flex: 0 0 auto;
  }
}
</style>
