<script setup lang="ts">
/**
 * 仪表盘：Hero + 大屏模式 + 系统音量 + 设备电源四块。
 * 仅承载顶层、无需进入子页即可完成的指令。
 *  - 不放预案调用、上传、窗口状态等明细能力；
 *  - 关机统一走 useDialog 二次确认。
 */
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import {
  NAlert,
  NButton,
  NCard,
  NSlider,
  NSpin,
  NSwitch,
} from 'naive-ui';

import FIcon from '@/design-system/FIcon.vue';
import BigScreenModeButtons from '@/features/runtime/BigScreenModeButtons.vue';
import { useDialog } from '@/composables/useDialog';
import { useThrottledSlider } from '@/composables/useThrottledSlider';
import { useToast } from '@/composables/useToast';
import { useRuntimeStore } from '@/stores/runtime';
import { useDeviceStore } from '@/stores/devices';

const { t } = useI18n();
const runtime = useRuntimeStore();
const device = useDeviceStore();
const toast = useToast();
const dialog = useDialog();

const pendingMode = ref<'single' | 'double' | null>(null);
const isModeSwitching = computed(() => pendingMode.value !== null);
const currentScreenMode = computed<'single' | 'double'>(() => runtime.runtime?.big_screen_mode ?? 'single');

async function switchScreenMode(mode: 'single' | 'double'): Promise<void> {
  if (isModeSwitching.value) return;
  pendingMode.value = mode;
  try {
    await runtime.setBigScreenMode(mode);
    toast.push({
      level: 'success',
      message: mode === 'double' ? t('dashboard.switchedDouble') : t('dashboard.switchedSingle'),
      action: {
        label: t('dashboard.undo'),
        onTrigger: async () => {
          await runtime.setBigScreenMode(mode === 'double' ? 'single' : 'double');
        },
      },
    });
  } catch (error) {
    toast.error(t('dashboard.switchFail'), error instanceof Error ? error.message : t('common.retry'));
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

const heroSubtitle = computed(() => {
  const sse = runtime.sseStatus === 'connected'
    ? t('app.sse.connected')
    : runtime.sseStatus === 'reconnecting'
      ? t('app.sse.reconnectingLong')
      : runtime.sseStatus === 'connecting'
        ? t('app.sse.connectingLong')
        : t('app.sse.closed');
  return `${runtime.bigScreenLabel} · ${sse}`;
});

async function powerOnSplice(): Promise<void> {
  try {
    await device.power('splice_screen', 'on');
    toast.success(t('dashboard.spliceOnOk'));
  } catch (error) {
    toast.error(t('dashboard.spliceOnFail'), error instanceof Error ? error.message : t('common.retry'));
  }
}

async function powerOffSplice(): Promise<void> {
  const confirmed = await dialog.danger({
    title: t('dashboard.spliceOffTitle'),
    description: t('dashboard.spliceOffDesc'),
    confirmLabel: t('dashboard.spliceOffConfirm'),
    cancelLabel: t('common.cancel'),
  });
  if (!confirmed) return;
  try {
    await device.power('splice_screen', 'off');
    toast.warning(t('dashboard.spliceOffOk'), t('dashboard.spliceOffOkDetail'));
  } catch (error) {
    toast.error(t('dashboard.spliceOffFail'), error instanceof Error ? error.message : t('dashboard.spliceOffFailDetail'));
  }
}

async function toggleTv(deviceType: 'tv_left' | 'tv_right', label: string): Promise<void> {
  try {
    await device.toggle(deviceType);
    toast.success(t('dashboard.tvToggleOk', { label }), t('dashboard.tvToggleOkDetail'));
  } catch (error) {
    toast.error(t('dashboard.tvToggleFail', { label }), error instanceof Error ? error.message : t('common.retry'));
  }
}

const hasDeviceError = computed(() =>
  Object.values(device.lastActionResult).some((status) => status === 'error'),
);
</script>

<template>
  <div class="dashboard">
    <section class="dashboard__hero" :aria-label="t('dashboard.overview')">
      <p class="dashboard__hero-eyebrow">{{ t('dashboard.heroEyebrow') }}</p>
      <h2 class="dashboard__hero-title">{{ heroSubtitle }}</h2>
      <p class="dashboard__hero-caption">{{ t('dashboard.heroCaption') }}</p>
    </section>

    <n-alert v-if="hasDeviceError" type="error" :title="t('dashboard.deviceErrorTitle')">
      {{ t('dashboard.deviceErrorBody') }}
    </n-alert>

    <section class="dashboard__grid" :aria-label="t('dashboard.topCommands')">
      <n-card class="dashboard__card" :title="t('dashboard.bigScreenTitle')">
        <template #header-extra>
          <span class="dashboard__eyebrow">{{ t('dashboard.bigScreenEyebrow') }}</span>
        </template>
        <BigScreenModeButtons
          :current-mode="currentScreenMode"
          :pending-mode="pendingMode"
          block
          @select="switchScreenMode"
        />
        <p v-if="isModeSwitching" class="dashboard__hint dashboard__hint--switching">
          <n-spin :size="14" /> {{ t('dashboard.switching') }}
        </p>
        <p v-else class="dashboard__hint">{{ t('dashboard.bigScreenHint') }}</p>
      </n-card>

      <n-card class="dashboard__card" :title="t('dashboard.volumeTitle')">
        <template #header-extra>
          <span class="dashboard__eyebrow">{{ t('dashboard.volumeEyebrow') }}</span>
        </template>
        <n-slider
          :value="volume.value.value"
          :min="0"
          :max="100"
          :aria-label="t('dashboard.volumeAria')"
          @update:value="volume.handleInput"
          @dragend="volume.handleChange(volume.value.value)"
        />
        <div class="dashboard__mute-row">
          <span>{{ t('dashboard.enableSystemMute') }}</span>
          <n-switch v-model:value="muteToggle" />
        </div>
      </n-card>

      <n-card class="dashboard__card" :title="t('dashboard.powerTitle')">
        <template #header-extra>
          <span class="dashboard__eyebrow">{{ t('dashboard.powerEyebrow') }}</span>
        </template>
        <div class="dashboard__power-row">
          <span class="dashboard__power-label">{{ t('dashboard.splice') }}</span>
          <n-button type="primary" @click="powerOnSplice">
            <template #icon><FIcon name="power_24_regular" /></template>
            {{ t('dashboard.powerOn') }}
          </n-button>
          <n-button type="error" @click="powerOffSplice">
            <template #icon><FIcon name="plug_disconnected_24_regular" /></template>
            {{ t('dashboard.powerOff') }}
          </n-button>
        </div>
        <div class="dashboard__power-row">
          <span class="dashboard__power-label">{{ t('dashboard.tvLeft') }}</span>
          <n-button @click="toggleTv('tv_left', t('dashboard.tvLeft'))">
            <template #icon><FIcon name="arrow_swap_24_regular" /></template>
            {{ t('dashboard.toggleState') }}
          </n-button>
        </div>
        <div class="dashboard__power-row">
          <span class="dashboard__power-label">{{ t('dashboard.tvRight') }}</span>
          <n-button @click="toggleTv('tv_right', t('dashboard.tvRight'))">
            <template #icon><FIcon name="arrow_swap_24_regular" /></template>
            {{ t('dashboard.toggleState') }}
          </n-button>
        </div>
      </n-card>
    </section>
  </div>
</template>

<style scoped>
.dashboard {
  display: flex;
  flex-direction: column;
  gap: var(--spacingVerticalXXL);
  max-width: 1280px;
}

.dashboard__hero {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: var(--spacingVerticalS);
  padding: var(--spacingVerticalXXL) var(--spacingHorizontalXXXL);
  border-radius: var(--borderRadius2XLarge);
  background: linear-gradient(135deg, var(--colorBrandBackground2) 0%, var(--colorNeutralBackground1) 100%);
  border: 1px solid var(--colorNeutralStroke2);
  box-shadow: var(--shadow4);
  overflow: hidden;
}

.dashboard__hero::after {
  content: '';
  position: absolute;
  right: -120px;
  bottom: -120px;
  width: 320px;
  height: 320px;
  border-radius: var(--borderRadiusCircular);
  background: radial-gradient(circle at center,
      color-mix(in srgb, var(--colorBrandBackground) 24%, transparent) 0%,
      transparent 70%);
  pointer-events: none;
}

.dashboard__hero-eyebrow {
  position: relative;
  z-index: 1;
  margin: 0;
  font-size: var(--fontSizeBase200);
  letter-spacing: 0.16em;
  font-weight: 700;
  color: var(--colorBrandForeground1);
  text-transform: uppercase;
}

.dashboard__hero-title {
  position: relative;
  z-index: 1;
  margin: 0;
  font-size: var(--fontSizeHero800);
  line-height: var(--lineHeightHero800);
  font-weight: 600;
  color: var(--colorNeutralForeground1);
}

.dashboard__hero-caption {
  position: relative;
  z-index: 1;
  margin: 0;
  color: var(--colorNeutralForeground2);
  max-width: 720px;
}

.dashboard__grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: var(--spacingHorizontalL);
}

.dashboard__card {
  min-height: 220px;
}

.dashboard__hint {
  margin: var(--spacingVerticalS) 0 0;
  color: var(--colorNeutralForeground3);
  font-size: var(--fontSizeBase200);
}

.dashboard__hint--switching {
  display: inline-flex;
  align-items: center;
  gap: var(--spacingHorizontalXS);
  color: var(--colorBrandForeground1);
  font-weight: 600;
}

.dashboard__eyebrow {
  font-size: var(--fontSizeBase200);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--colorNeutralForeground3);
}

.dashboard__mute-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: var(--spacingVerticalM);
}

.dashboard__power-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--spacingHorizontalS);
  margin-bottom: var(--spacingVerticalS);
}

.dashboard__power-label {
  flex: 1 1 100px;
  font-weight: 600;
}

@media (max-width: 767px) {
  .dashboard__hero {
    padding: var(--spacingVerticalL) var(--spacingHorizontalL) var(--spacingVerticalXL);
  }

  .dashboard__hero-title {
    font-size: var(--fontSizeHero700);
    line-height: var(--lineHeightHero700);
  }

  .dashboard__grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
