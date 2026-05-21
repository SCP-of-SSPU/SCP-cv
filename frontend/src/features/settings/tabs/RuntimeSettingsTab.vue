<script setup lang="ts">
/**
 * 设置中心运行态 Tab。
 * 承载大屏模式、系统音量、SSE 状态与重置全部窗口等全局运行控制。
 */
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';

import {
  FButton,
  FCard,
  FSegmented,
  FSlider,
  FSwitch,
  FTag,
} from '@/design-system';
import { useThrottledSlider } from '@/composables/useThrottledSlider';
import { useToast } from '@/composables/useToast';
import { useRuntimeStore } from '@/stores/runtime';
import { useSessionStore } from '@/stores/sessions';

const { t } = useI18n();
const runtime = useRuntimeStore();
const session = useSessionStore();
const toast = useToast();

const screenMode = computed({
  get: () => runtime.runtime?.big_screen_mode ?? 'single',
  set: async (mode: 'single' | 'double') => {
    try {
      await runtime.setBigScreenMode(mode);
      toast.success(mode === 'double' ? t('more.switchedDouble') : t('more.switchedSingle'));
    } catch (error) {
      toast.error(t('more.switchFail'), error instanceof Error ? error.message : t('common.retry'));
    }
  },
});

const volume = useThrottledSlider(
  () => runtime.systemVolume.level,
  {
    commit: (level: number) => runtime.setSystemVolume(level, runtime.systemVolume.muted),
    onError: (error) => {
      toast.error(t('dashboard.volumeFail'), error instanceof Error ? error.message : t('common.retry'));
    },
  },
);

const muteToggle = computed({
  get: () => runtime.systemVolume.muted,
  set: async (next: boolean) => {
    try {
      // 静音切换沿用滑块当前显示值，避免回写到节流前的旧值。
      await runtime.setSystemVolume(volume.value.value, next);
    } catch (error) {
      toast.error(t('dashboard.muteFail'), error instanceof Error ? error.message : t('common.retry'));
    }
  },
});

const sseLabel = computed(() => {
  switch (runtime.sseStatus) {
    case 'connected':
      return t('app.sse.connected');
    case 'connecting':
      return t('app.sse.connecting');
    case 'reconnecting':
      return t('app.sse.reconnecting');
    case 'closed':
    default:
      return t('app.sse.closed');
  }
});

const sseLastUpdateLabel = computed(() => {
  if (!runtime.sseLastUpdate) return t('settings.sseNoUpdate');
  const date = new Date(runtime.sseLastUpdate);
  return t('settings.sseLastUpdate', { time: date.toLocaleTimeString() });
});

async function refreshSse(): Promise<void> {
  runtime.disconnectEvents();
  runtime.connectEvents();
  toast.info(t('settings.sseReconnected'));
}

async function resetAll(): Promise<void> {
  try {
    await session.resetAll();
    toast.success(t('settings.resetAllOk'));
  } catch (error) {
    toast.error(t('settings.resetAllFail'), error instanceof Error ? error.message : t('common.retry'));
  }
}
</script>

<template>
  <section class="settings-view__grid">
    <FCard padding="cozy">
      <template #title>{{ t('settings.bigScreenMode') }}</template>
      <FSegmented v-model="screenMode" :options="[
        { label: t('screen.single'), value: 'single' },
        { label: t('screen.double'), value: 'double' },
      ]" full-width />
      <p class="settings-view__hint">
        {{ t('settings.bigScreenHint') }}
      </p>
    </FCard>

    <FCard padding="cozy">
      <template #title>{{ t('settings.systemVolume') }}</template>
      <FSlider :model-value="volume.value.value" :min="0" :max="100" show-value :aria-label="t('settings.systemVolumeAria')"
        @update:modelValue="volume.handleInput" @change="volume.handleChange" />
      <FSwitch v-model="muteToggle" :label="t('settings.enableSystemMute')" />
      <FTag :tone="runtime.systemVolume.backend === 'windows_core_audio' ? 'subtle' : 'warning'">
        {{ t('settings.backendTag', { backend: runtime.systemVolume.backend }) }}
      </FTag>
    </FCard>

    <FCard padding="cozy">
      <template #title>{{ t('settings.sseStatus') }}</template>
      <p class="settings-view__row">
        <FTag :tone="runtime.sseStatus === 'connected' ? 'success' : 'warning'"
          :dot="runtime.sseStatus === 'reconnecting'">
          {{ sseLabel }}
        </FTag>
        <span>{{ sseLastUpdateLabel }}</span>
      </p>
      <FButton appearance="secondary" icon-start="arrow_clockwise_24_regular" @click="refreshSse">
        {{ t('settings.reconnect') }}
      </FButton>
    </FCard>

    <FCard padding="cozy">
      <template #title>{{ t('settings.emergencyTools') }}</template>
      <FButton appearance="danger" icon-start="arrow_reset_24_regular" @click="resetAll">
        {{ t('settings.resetAll') }}
      </FButton>
      <p class="settings-view__hint">
        {{ t('settings.resetAllHint') }}
      </p>
    </FCard>
  </section>
</template>
