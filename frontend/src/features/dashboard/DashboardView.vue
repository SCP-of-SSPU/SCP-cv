<script setup lang="ts">
/**
 * 仪表盘：Hero + 大屏模式 + 系统音量 + 设备电源四块。
 * 设计稿 §4.1：仅承载顶层、无需进入子页即可完成的指令。
 *  - 不放预案调用、上传、窗口状态等明细能力；
 *  - 关机统一走 useDialog 二次确认。
 */
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';

import {
  FCard,
  FButton,
  FSegmented,
  FSlider,
  FSwitch,
  FMessageBar,
  FSpinner,
} from '@/design-system';
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

/*
 * 大屏模式切换：后端会同步关闭/打开窗口、刷新会话快照，整体耗时 1–3 秒；
 * 历史实现仅 await + 成功 toast，过程没有任何视觉反馈，导致操作员误以为点击未生效
 * 进而重复点击。新实现：
 *   - 显式 pendingMode：被锁定的目标值，期间 FSegmented 锁定为 disabled；
 *   - inline Loading + 提示文字「切换中…」；
 *   - 同一时刻只允许一笔切换；并发点击被忽略，避免多笔互相覆盖。
 */
const pendingMode = ref<'single' | 'double' | null>(null);
const isModeSwitching = computed(() => pendingMode.value !== null);

const screenMode = computed({
  get: (): 'single' | 'double' => pendingMode.value ?? (runtime.runtime?.big_screen_mode ?? 'single'),
  set: (mode: 'single' | 'double'): void => {
    if (isModeSwitching.value) return;
    void switchScreenMode(mode);
  },
});

async function switchScreenMode(mode: 'single' | 'double'): Promise<void> {
  if (mode === (runtime.runtime?.big_screen_mode ?? 'single')) return;
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

// 系统音量节流：拖动期间 120 ms 节流提交、抬手时一次最终上报；
// 后端 PATCH 响应在拖动期间不会覆盖本地 UI 值，避免回弹。
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
    // 设备无回读，按钮按"切换电源 toggle"语义命名；此处也保持「开/关机状态」用语统一。
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
      <p class="dashboard__hero-caption">
        {{ t('dashboard.heroCaption') }}
      </p>
    </section>

    <FMessageBar v-if="hasDeviceError" tone="error" :title="t('dashboard.deviceErrorTitle')">
      {{ t('dashboard.deviceErrorBody') }}
    </FMessageBar>

    <section class="dashboard__grid" :aria-label="t('dashboard.topCommands')">
      <FCard class="dashboard__card">
        <template #eyebrow>{{ t('dashboard.bigScreenEyebrow') }}</template>
        <template #title>{{ t('dashboard.bigScreenTitle') }}</template>
        <FSegmented v-model="screenMode" :options="[
          { label: t('screen.single'), value: 'single' },
          { label: t('screen.double'), value: 'double' },
        ]" :disabled="isModeSwitching" full-width :aria-label="t('dashboard.screenSelectAria')" />
        <p class="dashboard__hint dashboard__hint--switching" v-if="isModeSwitching">
          <FSpinner :size="14" /> {{ t('dashboard.switching') }}
        </p>
        <p class="dashboard__hint" v-else>
          {{ t('dashboard.bigScreenHint') }}
        </p>
      </FCard>

      <FCard class="dashboard__card">
        <template #eyebrow>{{ t('dashboard.volumeEyebrow') }}</template>
        <template #title>{{ t('dashboard.volumeTitle') }}</template>
        <FSlider :model-value="volume.value.value" :min="0" :max="100" :aria-label="t('dashboard.volumeAria')" show-value
          @update:modelValue="volume.handleInput" @change="volume.handleChange" />
        <FSwitch v-model="muteToggle" :label="t('dashboard.enableSystemMute')" />
      </FCard>

      <FCard class="dashboard__card">
        <template #eyebrow>{{ t('dashboard.powerEyebrow') }}</template>
        <template #title>{{ t('dashboard.powerTitle') }}</template>
        <div class="dashboard__power-row">
          <span class="dashboard__power-label">{{ t('dashboard.splice') }}</span>
          <FButton appearance="primary" icon-start="power_24_regular" @click="powerOnSplice">
            {{ t('dashboard.powerOn') }}
          </FButton>
          <FButton appearance="danger" icon-start="plug_disconnected_24_regular" @click="powerOffSplice">
            {{ t('dashboard.powerOff') }}
          </FButton>
        </div>
        <div class="dashboard__power-row">
          <span class="dashboard__power-label">{{ t('dashboard.tvLeft') }}</span>
          <FButton appearance="secondary" icon-start="arrow_swap_24_regular" @click="toggleTv('tv_left', t('dashboard.tvLeft'))">
            {{ t('dashboard.toggleState') }}
          </FButton>
        </div>
        <div class="dashboard__power-row">
          <span class="dashboard__power-label">{{ t('dashboard.tvRight') }}</span>
          <FButton appearance="secondary" icon-start="arrow_swap_24_regular" @click="toggleTv('tv_right', t('dashboard.tvRight'))">
            {{ t('dashboard.toggleState') }}
          </FButton>
        </div>
      </FCard>
    </section>
  </div>
</template>

<style scoped>
.dashboard {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-2xl);
  max-width: 1280px;
}

.dashboard__hero {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-s);
  padding: var(--spacing-2xl) var(--spacing-3xl);
  /* Hero 用 xxlarge 大圆角与渐变背景配合，是仪表盘视觉重心。渐变来自 token，便于深色模式复用。 */
  border-radius: var(--radius-xxlarge);
  background: var(--gradient-hero);
  border: 1px solid color-mix(in srgb, var(--color-border-subtle) 60%, transparent);
  box-shadow: var(--shadow-card), var(--ring-accent);
  overflow: hidden;
  animation: f-rise var(--motion-duration-entrance) var(--motion-curve-emphasized) both;
}

/* 装饰性光晕：右下角放一颗模糊的 brand 色光球，让 hero 有"现场感"。 */
.dashboard__hero::after {
  content: '';
  position: absolute;
  right: -120px;
  bottom: -120px;
  width: 320px;
  height: 320px;
  border-radius: var(--radius-circular);
  background: radial-gradient(circle at center,
      color-mix(in srgb, var(--color-background-brand) 24%, transparent) 0%,
      transparent 70%);
  pointer-events: none;
}

.dashboard__hero-eyebrow {
  position: relative;
  z-index: 1;
  margin: 0;
  font-size: var(--type-caption1-size);
  letter-spacing: 0.16em;
  font-weight: 700;
  color: var(--color-text-brand);
  text-transform: uppercase;
}

.dashboard__hero-title {
  position: relative;
  z-index: 1;
  margin: 0;
  font-size: var(--type-title1-size);
  line-height: var(--type-title1-line);
  font-weight: 600;
  color: var(--color-text-primary);
}

.dashboard__hero-caption {
  position: relative;
  z-index: 1;
  margin: 0;
  color: var(--color-text-secondary);
  max-width: 720px;
}

.dashboard__grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: var(--spacing-l);
}

.dashboard__card {
  min-height: 220px;
  transition: transform var(--motion-duration-entrance) var(--motion-curve-emphasized);
}

.dashboard__card:hover {
  transform: translateY(var(--motion-hover-lift));
}

/*
 * 列表内卡片入场加 30 ms 错峰，整组卡片"瀑布式"浮起。
 * 当浏览器命中 prefers-reduced-motion 时，delay 仍生效但 duration 已被 token 收敛到 0，
 * 视觉上等价于一次性同时出现。
 */
.dashboard__grid>.dashboard__card:nth-child(2) {
  animation-delay: 40ms;
}

.dashboard__grid>.dashboard__card:nth-child(3) {
  animation-delay: 80ms;
}

.dashboard__hint {
  margin: 0;
  color: var(--color-text-tertiary);
  font-size: var(--type-caption1-size);
}

.dashboard__hint--switching {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-xs);
  color: var(--color-text-brand);
  font-weight: 600;
}

.dashboard__power-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--spacing-s);
}

.dashboard__power-label {
  flex: 1 1 100px;
  font-weight: 600;
}

@media (max-width: 767px) {
  .dashboard__hero {
    padding: var(--spacing-l) var(--spacing-l) var(--spacing-xl);
  }

  .dashboard__hero-title {
    font-size: var(--type-title2-size);
    line-height: var(--type-title2-line);
  }

  .dashboard__grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .dashboard__power-row :deep(.f-button) {
    flex: 1 1 0;
  }
}
</style>
