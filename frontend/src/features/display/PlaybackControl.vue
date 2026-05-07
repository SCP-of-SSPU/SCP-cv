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

const props = defineProps<{ session: SessionSnapshot }>();

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
    toast.error(errorTitle, error instanceof Error ? error.message : '请稍后重试');
  }
}

function onPlay(): void {
  void call(() => sessionStore.control(props.session.window_id, 'play'), '播放失败');
}
function onPause(): void {
  void call(() => sessionStore.control(props.session.window_id, 'pause'), '暂停失败');
}
function onStop(): void {
  void call(() => sessionStore.control(props.session.window_id, 'stop'), '停止失败');
}
function onPrev(): void {
  void call(() => sessionStore.navigate(props.session.window_id, 'prev'), '翻页失败');
}
function onNext(): void {
  void call(() => sessionStore.navigate(props.session.window_id, 'next'), '翻页失败');
}
function onJump(): void {
  const target = Number.parseInt(jumpInput.value, 10);
  if (!Number.isFinite(target) || target <= 0) {
    toast.warning('页码无效', '请输入大于 0 的整数');
    return;
  }
  void call(() => sessionStore.navigate(props.session.window_id, 'jump', target), '跳页失败');
}

function onLoopToggle(value: boolean): void {
  void call(() => sessionStore.setLoop(props.session.window_id, value), '循环切换失败');
}

function onMuteToggle(value: boolean): void {
  void call(() => sessionStore.setWindowMute(props.session.window_id, value), '窗口静音失败');
}

// 窗口音量节流：拖动每 ~120 ms 上报一次，抬手再 flush，
// SSE 回写在拖动 / 飞行 / 待发期间不会覆盖本地 UI 值。
const windowVolume = useThrottledSlider(
  () => props.session.volume,
  {
    commit: (value: number) => sessionStore.setWindowVolume(props.session.window_id, value),
    onError: (error) => {
      toast.error('音量调整失败', error instanceof Error ? error.message : '请稍后重试');
    },
  },
);

function onSeek(positionMs: number): void {
  void call(
    () => sessionStore.navigate(props.session.window_id, 'seek', 0, positionMs),
    'Seek 失败',
  );
}

function onClose(): void {
  void call(() => sessionStore.closeSource(props.session.window_id), '关闭显示失败');
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
    pptError.value = error instanceof Error ? error.message : '加载失败';
  }
}

watch(
  () => [category.value, props.session.source_id, props.session.current_slide] as const,
  loadPptResources,
  { immediate: true },
);

const currentResource = computed(() =>
  pptResources.value.find((res) => res.page_index === props.session.current_slide - 1),
);

async function pptMediaAction(mediaId: string, mediaIndex: number, action: string): Promise<void> {
  try {
    await sessionStore.controlPptMedia(props.session.window_id, action, mediaId, mediaIndex);
  } catch (error) {
    toast.error('PPT 媒体控制失败', error instanceof Error ? error.message : '请稍后重试');
  }
}

const pptProgressLabel = computed(() => {
  if (props.session.total_slides <= 0) return '';
  return `${props.session.current_slide} / ${props.session.total_slides}`;
});

const seekValue = computed(() => Math.min(props.session.duration_ms, Math.max(0, props.session.position_ms)));

const isPlaying = computed(() => props.session.playback_state === 'playing');
</script>

<template>
  <div class="playback-control">
    <header class="playback-control__heading">
      <div>
        <FTag :tone="stateTone">
          {{ session.playback_state_label || session.playback_state }}
        </FTag>
        <h3 class="playback-control__source-name">
          {{ session.source_name || '未打开任何源' }}
        </h3>
        <p class="playback-control__caption">
          {{ session.source_type_label || '空闲' }}
          <template v-if="session.is_spliced">· {{ session.spliced_display_label || '拼接' }}</template>
        </p>
      </div>
      <RouterLink v-if="category === 'ppt' && session.source_id" :to="`/ppt-focus/${session.window_id}`"
        class="playback-control__focus-link">
        <FIcon name="arrow_maximize_24_regular" />
        <span>PPT 专注模式</span>
      </RouterLink>
    </header>

    <FMessageBar v-if="session.playback_state === 'error'" tone="error" title="播放器异常">
      请检查源是否可用或重新打开源；如反复失败，可在「应急 → 重置全部窗口」恢复。
    </FMessageBar>

    <!-- PPT 控制 -->
    <section v-if="category === 'ppt'" class="playback-control__section">
      <div class="playback-control__row playback-control__row--ppt">
        <FButton appearance="secondary" icon-start="previous_24_regular" @click="onPrev">上一页</FButton>
        <FButton appearance="primary" icon-start="next_24_regular" @click="onNext">下一页</FButton>
        <div class="playback-control__jump">
          <FInput v-model="jumpInput" type="number" placeholder="跳页" :max-length="4" />
          <FButton appearance="secondary" @click="onJump">跳转</FButton>
        </div>
      </div>
      <div v-if="session.total_slides > 0" class="playback-control__row playback-control__row--progress">
        <FProgress :value="session.current_slide" :max="session.total_slides" />
        <span class="playback-control__progress-label">{{ pptProgressLabel }}</span>
      </div>

      <FMessageBar v-if="pptError" tone="error" title="加载 PPT 资源失败">
        {{ pptError }}
      </FMessageBar>

      <div v-if="currentResource && currentResource.media_items.length > 0" class="playback-control__media">
        <h4 class="playback-control__media-title">当前页媒体</h4>
        <ul class="playback-control__media-list">
          <li v-for="media in currentResource.media_items" :key="media.id" class="playback-control__media-item">
            <span class="playback-control__media-name">{{ media.name }}</span>
            <span class="playback-control__media-actions">
              <FButton size="compact" icon-only icon-start="play_24_regular" aria-label="播放媒体"
                @click="pptMediaAction(media.id, media.media_index, 'play')" />
              <FButton size="compact" icon-only icon-start="pause_24_regular" aria-label="暂停媒体"
                @click="pptMediaAction(media.id, media.media_index, 'pause')" />
              <FButton size="compact" icon-only icon-start="stop_24_regular" aria-label="停止媒体" appearance="danger"
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
          播放
        </FButton>
        <FButton v-else appearance="primary" icon-start="pause_24_regular" @click="onPause">
          暂停
        </FButton>
        <FButton appearance="secondary" icon-start="stop_24_regular" @click="onStop">停止</FButton>
        <FSwitch :model-value="session.loop_enabled" label="循环播放" @update:modelValue="onLoopToggle" />
      </div>
      <div v-if="session.duration_ms > 0" class="playback-control__row playback-control__row--seek">
        <FSlider :model-value="seekValue" :min="0" :max="session.duration_ms" :step="1000" aria-label="播放进度"
          @update:modelValue="onSeek" />
        <span class="playback-control__progress-label">
          {{ formatDuration(session.position_ms) }} / {{ formatDuration(session.duration_ms) }}
        </span>
      </div>
    </section>

    <!-- 图片 / 网页 -->
    <section v-else-if="category === 'image' || category === 'web'" class="playback-control__section">
      <p v-if="session.source_uri" class="playback-control__uri">{{ session.source_uri }}</p>
      <p v-else class="playback-control__uri">资源未提供 URI</p>
    </section>

    <!-- 直播 -->
    <section v-else-if="category === 'stream'" class="playback-control__section">
      <FTag :tone="session.source_uri ? 'warning' : 'subtle'" :dot="!!session.source_uri">
        {{ session.source_uri ? '直播中' : '未推流' }}
      </FTag>
      <p v-if="session.source_uri" class="playback-control__uri">{{ session.source_uri }}</p>
    </section>

    <section v-else class="playback-control__section">
      <p class="playback-control__caption">该窗口当前没有源；请从左侧列表选择源打开。</p>
    </section>

    <!-- 通用：窗口音量、关闭显示 -->
    <section class="playback-control__section">
      <div class="playback-control__row">
        <span class="playback-control__field-label">窗口音量</span>
        <FSlider :model-value="windowVolume.value.value" :min="0" :max="100" aria-label="窗口音量" show-value
          :disabled="category === 'image' || category === 'web'" @update:modelValue="windowVolume.handleInput"
          @change="windowVolume.handleChange" />
      </div>
      <div class="playback-control__row">
        <FSwitch :model-value="session.is_muted" label="窗口静音" :disabled="category === 'image' || category === 'web'"
          @update:modelValue="onMuteToggle" />
        <FButton appearance="danger" icon-start="dismiss_24_regular" :disabled="!session.source_id" @click="onClose">
          关闭显示
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
  font-size: var(--type-title3-size);
  line-height: var(--type-title3-line);
  font-weight: 600;
}

.playback-control__caption {
  margin: var(--spacing-xs) 0 0;
  color: var(--color-text-secondary);
  font-size: var(--type-caption1-size);
}

.playback-control__focus-link {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-xs);
  padding: var(--spacing-s) var(--spacing-m);
  border-radius: var(--radius-medium);
  background: var(--color-background-brand-selected);
  color: var(--color-text-brand);
  font-weight: 600;
  text-decoration: none;
}

.playback-control__focus-link:hover {
  background: var(--color-background-brand);
  color: var(--color-text-inverse);
}

.playback-control__section {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-m);
  padding: var(--spacing-l);
  border-radius: var(--radius-large);
  background: var(--color-background-subtle);
  border: 1px solid var(--color-border-subtle);
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
  color: var(--color-text-secondary);
  flex-shrink: 0;
}

.playback-control__media-title {
  margin: 0;
  font-size: var(--type-subtitle2-size);
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
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-medium);
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
  font-family: var(--font-family-mono);
  color: var(--color-text-secondary);
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
