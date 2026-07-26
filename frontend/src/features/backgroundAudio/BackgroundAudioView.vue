<script setup lang="ts">
/**
 * 背景音乐控制台：展示全局音频状态、播放列表和可加入的音频源。
 */
import { computed, onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import {
  NButton,
  NCard,
  NEmpty,
  NProgress,
  NSlider,
  NSwitch,
  NTag,
} from 'naive-ui';

import AddSourceDrawer from '@/features/sources/AddSourceDrawer.vue';
import SourceThumbnail from '@/features/sources/SourceThumbnail.vue';
import FIcon from '@/design-system/FIcon.vue';
import { sliderAriaLabel as vSliderAriaLabel } from '@/design-system/sliderAriaLabel';
import { useDialog } from '@/composables/useDialog';
import { useToast } from '@/composables/useToast';
import { useThrottledSlider } from '@/composables/useThrottledSlider';
import { formatBytes } from '@/design-system/utils';
import { formatDuration, type BackgroundAudioPlaylistItem, type MediaSourceItem } from '@/services/api';
import { useBackgroundAudioStore } from '@/stores/backgroundAudio';
import { useSourceStore } from '@/stores/sources';

const { t } = useI18n();
const audioStore = useBackgroundAudioStore();
const sourceStore = useSourceStore();
const toast = useToast();
const dialog = useDialog();

const drawerOpen = ref(false);
const busyAction = ref('');

const currentState = computed(() => audioStore.state);
const playlist = computed(() => audioStore.playlist);
const audioSources = computed(() => sourceStore.sources.filter((source) => source.source_type === 'audio'));
const currentSource = computed(() => currentState.value?.source ?? null);
const progressPercent = computed(() => {
  const duration = currentState.value?.duration_ms ?? 0;
  if (duration <= 0) return 0;
  return Math.min(100, Math.round(((currentState.value?.position_ms ?? 0) / duration) * 100));
});
const statusLabel = computed(() => {
  const status = currentState.value?.playback_state ?? 'idle';
  return t(`backgroundAudio.status.${status}`);
});
const playlistCaption = computed(() => t('backgroundAudio.playlistCount', { n: playlist.value.length }));
const sourceCaption = computed(() => t('backgroundAudio.sourceCount', { n: audioSources.value.length }));
const playPauseAria = computed(() => audioStore.isPlaying
  ? t('backgroundAudio.pause')
  : t('backgroundAudio.play'));

const backgroundVolume = useThrottledSlider(
  () => currentState.value?.volume ?? 70,
  {
    commit: (value: number) => audioStore.setVolume(value),
    onError: (error) => {
      toast.error(t('backgroundAudio.actionFail'), error instanceof Error ? error.message : t('common.retry'));
    },
  },
);

onMounted(() => {
  void refreshAll();
});

async function refreshAll(): Promise<void> {
  busyAction.value = 'refresh';
  try {
    await Promise.all([audioStore.refresh(), sourceStore.refresh()]);
  } catch (error) {
    toast.error(t('backgroundAudio.loadFail'), error instanceof Error ? error.message : t('common.retry'));
  } finally {
    busyAction.value = '';
  }
}

async function runAction(actionKey: string, action: () => Promise<void>, successMessage = ''): Promise<void> {
  busyAction.value = actionKey;
  try {
    await action();
    if (successMessage) toast.success(successMessage);
  } catch (error) {
    toast.error(t('backgroundAudio.actionFail'), error instanceof Error ? error.message : t('common.retry'));
  } finally {
    busyAction.value = '';
  }
}

function playOrPause(): Promise<void> {
  return runAction(
    'play-toggle',
    () => audioStore.control(audioStore.isPlaying ? 'pause' : 'play'),
  );
}

function playItem(item: BackgroundAudioPlaylistItem): Promise<void> {
  return runAction('play-item', () => audioStore.playItem(item.id), t('backgroundAudio.playingOk', { name: item.source_name }));
}

function playSource(source: MediaSourceItem): Promise<void> {
  return runAction('play-source', () => audioStore.playSource(source.id), t('backgroundAudio.playingOk', { name: source.name }));
}

function addSource(source: MediaSourceItem): Promise<void> {
  return runAction('add-source', () => audioStore.addSource(source.id), t('backgroundAudio.addedOk'));
}

function removeItem(item: BackgroundAudioPlaylistItem): Promise<void> {
  return runAction('remove-item', () => audioStore.removeItem(item.id), t('backgroundAudio.removedOk'));
}

async function clearPlaylist(): Promise<void> {
  const confirmed = await dialog.danger({
    title: t('backgroundAudio.clearTitle'),
    description: t('backgroundAudio.clearDesc'),
    confirmLabel: t('backgroundAudio.clearPlaylist'),
  });
  if (!confirmed) return;
  await runAction('clear', () => audioStore.clearPlaylist(), t('backgroundAudio.clearedOk'));
}

function setLoop(enabled: boolean): Promise<void> {
  return runAction('loop', () => audioStore.setLoop(enabled));
}

function setMute(muted: boolean): Promise<void> {
  return runAction('mute', () => audioStore.setMute(muted));
}

</script>

<template>
  <div class="background-audio">
    <header class="background-audio__hero">
      <div class="background-audio__hero-copy">
        <span class="background-audio__eyebrow">{{ t('backgroundAudio.routeTitle') }}</span>
        <h2>{{ t('backgroundAudio.title') }}</h2>
        <p>{{ t('backgroundAudio.subtitle') }}</p>
      </div>
      <div class="background-audio__hero-actions">
        <n-button :loading="busyAction === 'refresh'" @click="refreshAll">
          <template #icon><FIcon name="arrow_clockwise_20_regular" /></template>
          {{ t('backgroundAudio.refresh') }}
        </n-button>
        <n-button type="primary" @click="drawerOpen = true">
          <template #icon><FIcon name="add_24_regular" /></template>
          {{ t('backgroundAudio.addAudio') }}
        </n-button>
      </div>
    </header>

    <section class="background-audio__deck">
      <n-card class="background-audio__player" content-style="padding:0">
        <div class="background-audio__player-surface">
          <div class="background-audio__disc" :class="{ 'background-audio__disc--playing': audioStore.isPlaying }">
            <FIcon name="music_note_2_24_regular" />
          </div>
          <div class="background-audio__wave" aria-hidden="true">
            <span v-for="bar in 18" :key="bar" />
          </div>
          <div class="background-audio__now">
            <n-tag round :type="currentState?.playback_state === 'error' ? 'error' : 'info'">{{ statusLabel }}</n-tag>
            <h3>{{ currentSource?.name || t('backgroundAudio.standbyTitle') }}</h3>
            <p>{{ currentSource?.uri || t('backgroundAudio.standbyHint') }}</p>
          </div>
          <div class="background-audio__progress-row">
            <span>{{ formatDuration(currentState?.position_ms ?? 0) }}</span>
            <n-progress type="line" :percentage="progressPercent" :show-indicator="false" />
            <span>{{ formatDuration(currentState?.duration_ms ?? 0) }}</span>
          </div>
          <p v-if="currentState?.error_message" class="background-audio__error">{{ currentState.error_message }}</p>
        </div>

        <div class="background-audio__controls">
          <n-button circle secondary :aria-label="t('backgroundAudio.previous')"
            @click="() => runAction('prev', () => audioStore.control('prev'))">
            <template #icon><FIcon name="previous_24_regular" /></template>
          </n-button>
          <n-button circle type="primary" size="large" :aria-label="playPauseAria"
            :loading="busyAction === 'play-toggle'" @click="playOrPause">
            <template #icon><FIcon :name="audioStore.isPlaying ? 'pause_24_filled' : 'play_24_filled'" /></template>
          </n-button>
          <n-button circle secondary :aria-label="t('backgroundAudio.next')"
            @click="() => runAction('next', () => audioStore.control('next'))">
            <template #icon><FIcon name="next_24_regular" /></template>
          </n-button>
          <n-button secondary @click="() => runAction('stop', () => audioStore.control('stop'))">
            <template #icon><FIcon name="stop_24_regular" /></template>
            {{ t('backgroundAudio.stop') }}
          </n-button>
        </div>

        <div class="background-audio__mix-row">
          <label>
            <span>{{ t('backgroundAudio.loop') }}</span>
            <n-switch :value="currentState?.loop_enabled ?? true" :aria-label="t('backgroundAudio.loop')"
              @update:value="setLoop" />
          </label>
          <label>
            <span>{{ t('backgroundAudio.mute') }}</span>
            <n-switch :value="currentState?.is_muted ?? false" :aria-label="t('backgroundAudio.mute')"
              @update:value="setMute" />
          </label>
          <div class="background-audio__volume">
            <span>{{ t('backgroundAudio.volume') }}</span>
            <n-slider
              v-slider-aria-label="t('backgroundAudio.volume')"
              :value="backgroundVolume.value.value"
              :min="0"
              :max="100"
              :step="1"
              :aria-label="t('backgroundAudio.volume')"
              @update:value="backgroundVolume.handleInput"
              @dragend="backgroundVolume.handleChange(backgroundVolume.value.value)"
              @keyup="backgroundVolume.handleChange(backgroundVolume.value.value)"
            />
          </div>
        </div>
      </n-card>

      <n-card class="background-audio__sources" content-style="padding:0">
        <template #header>
          <div class="background-audio__section-title">
            <span>{{ t('backgroundAudio.audioSources') }}</span>
            <small>{{ sourceCaption }}</small>
          </div>
        </template>
        <n-empty v-if="audioSources.length === 0" :description="t('backgroundAudio.emptyAudioHint')">
          <template #icon><FIcon name="music_note_2_24_regular" /></template>
          <template #extra>
            <n-button type="primary" @click="drawerOpen = true">{{ t('backgroundAudio.addAudio') }}</n-button>
          </template>
        </n-empty>
        <div v-else class="background-audio__source-list">
          <article v-for="source in audioSources" :key="source.id" class="background-audio__source-item">
            <SourceThumbnail :source="source" />
            <div class="background-audio__item-main">
              <strong>{{ source.name }}</strong>
              <span>{{ source.file_size ? formatBytes(source.file_size) : source.uri }}</span>
            </div>
            <n-button size="small" secondary @click="() => addSource(source)">{{ t('backgroundAudio.addToPlaylist') }}</n-button>
            <n-button size="small" type="primary" @click="() => playSource(source)">{{ t('backgroundAudio.playNow') }}</n-button>
          </article>
        </div>
      </n-card>
    </section>

    <n-card class="background-audio__playlist" content-style="padding:0">
      <template #header>
        <div class="background-audio__section-title">
          <span>{{ t('backgroundAudio.playlist') }}</span>
          <small>{{ playlistCaption }}</small>
        </div>
      </template>
      <template #header-extra>
        <n-button quaternary size="small" :disabled="playlist.length === 0" @click="clearPlaylist">
          {{ t('backgroundAudio.clearPlaylist') }}
        </n-button>
      </template>
      <n-empty v-if="playlist.length === 0" :description="t('backgroundAudio.emptyPlaylist')">
        <template #icon><FIcon name="music_note_2_24_regular" /></template>
      </n-empty>
      <div v-else class="background-audio__playlist-grid">
        <article v-for="item in playlist" :key="item.id" class="background-audio__playlist-item"
          :class="{ 'background-audio__playlist-item--active': item.id === currentState?.current_item_id }">
          <SourceThumbnail :source="item.source" />
          <div class="background-audio__item-main">
            <strong>{{ item.source_name }}</strong>
            <span>{{ item.source.uri }}</span>
          </div>
          <n-tag v-if="item.id === currentState?.current_item_id" round type="success">{{ t('backgroundAudio.currentBadge') }}</n-tag>
          <n-button size="small" secondary @click="() => playItem(item)">{{ t('backgroundAudio.play') }}</n-button>
          <n-button size="small" quaternary @click="() => removeItem(item)">{{ t('backgroundAudio.remove') }}</n-button>
        </article>
      </div>
    </n-card>

    <AddSourceDrawer v-model:open="drawerOpen" @added="refreshAll" />
  </div>
</template>

<style scoped src="./BackgroundAudioView.css"></style>
