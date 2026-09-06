<script setup lang="ts">
/**
 * 设置中心运行态 Tab。
 * 承载大屏模式、系统音量、SSE 状态与重置全部窗口等全局运行控制。
 */
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import {
  NButton,
  NCard,
  NSlider,
  NSwitch,
  NTag,
} from 'naive-ui';

import FIcon from '@/design-system/FIcon.vue';
import { sliderAriaLabel as vSliderAriaLabel } from '@/design-system/sliderAriaLabel';
import BigScreenModeButtons from '@/features/runtime/BigScreenModeButtons.vue';
import { useThrottledSlider } from '@/composables/useThrottledSlider';
import { useToast } from '@/composables/useToast';
import { useRuntimeStore } from '@/stores/runtime';
import { useSessionStore } from '@/stores/sessions';

const { t } = useI18n();
const runtime = useRuntimeStore();
const session = useSessionStore();
const toast = useToast();
const pendingMode = ref<'single' | 'double' | null>(null);

const currentScreenMode = computed<'single' | 'double'>(() => runtime.runtime?.big_screen_mode ?? 'single');

async function switchScreenMode(mode: 'single' | 'double'): Promise<void> {
  if (pendingMode.value !== null) return;
  pendingMode.value = mode;
  try {
    await runtime.setBigScreenMode(mode);
    toast.success(mode === 'double' ? t('more.switchedDouble') : t('more.switchedSingle'));
  } catch (error) {
    toast.error(t('more.switchFail'), error instanceof Error ? error.message : t('common.retry'));
  } finally {
    pendingMode.value = null;
  }
}

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
    <n-card :title="t('settings.bigScreenMode')">
      <BigScreenModeButtons
        :current-mode="currentScreenMode"
        :pending-mode="pendingMode"
        block
        @select="switchScreenMode"
      />
      <p class="settings-view__hint">{{ t('settings.bigScreenHint') }}</p>
    </n-card>

    <n-card :title="t('settings.systemVolume')">
      <div class="settings-view__volume-row">
        <n-slider
          v-slider-aria-label="t('settings.systemVolumeAria')"
          :value="volume.value.value"
          :min="0"
          :max="100"
          :aria-label="t('settings.systemVolumeAria')"
          :disabled="runtime.systemVolume.muted"
          @update:value="volume.handleInput"
          @dragend="volume.handleChange(volume.value.value)"
        />
        <span class="settings-view__volume-value">{{ runtime.systemVolume.muted ? '—' : volume.value.value + '%' }}</span>
      </div>
      <div class="settings-view__row">
        <span>{{ t('settings.enableSystemMute') }}</span>
        <n-switch v-model:value="muteToggle" />
      </div>
      <n-tag :type="runtime.systemVolume.backend === 'windows_core_audio' ? 'default' : 'warning'" size="small" round>
        {{ t('settings.backendTag', { backend: runtime.systemVolume.backend }) }}
      </n-tag>
    </n-card>

    <n-card :title="t('settings.sseStatus')">
      <p class="settings-view__row">
        <n-tag :type="runtime.sseStatus === 'connected' ? 'success' : 'warning'" size="small" round>
          {{ sseLabel }}
        </n-tag>
        <span>{{ sseLastUpdateLabel }}</span>
      </p>
      <n-button @click="refreshSse">
        <template #icon><FIcon name="arrow_clockwise_24_regular" /></template>
        {{ t('settings.reconnect') }}
      </n-button>
    </n-card>
  </section>

  <section class="settings-view__danger-zone">
    <n-card :title="t('settings.emergencyTools')">
      <n-button type="error" @click="resetAll">
        <template #icon><FIcon name="arrow_reset_24_regular" /></template>
        {{ t('settings.resetAll') }}
      </n-button>
      <p class="settings-view__hint">{{ t('settings.resetAllHint') }}</p>
    </n-card>
  </section>
</template>
