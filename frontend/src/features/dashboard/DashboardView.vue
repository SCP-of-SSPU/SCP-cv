<script setup lang="ts">
/**
 * 仪表盘：Hero + 大屏模式 + 系统音量 + 设备电源四块。
 * 设计稿 §4.1：仅承载顶层、无需进入子页即可完成的指令。
 *  - 不放预案调用、上传、窗口状态等明细能力；
 *  - 关机统一走 useDialog 二次确认。
 */
import { computed } from 'vue';

import {
  FCard,
  FButton,
  FSegmented,
  FSlider,
  FSwitch,
  FTag,
  FMessageBar,
} from '@/design-system';
import { useDialog } from '@/composables/useDialog';
import { useToast } from '@/composables/useToast';
import { useRuntimeStore } from '@/stores/runtime';
import { useDeviceStore } from '@/stores/devices';

const runtime = useRuntimeStore();
const device = useDeviceStore();
const toast = useToast();
const dialog = useDialog();

const screenMode = computed({
  get: (): 'single' | 'double' => runtime.runtime?.big_screen_mode ?? 'single',
  set: async (mode: 'single' | 'double'): Promise<void> => {
    try {
      await runtime.setBigScreenMode(mode);
      toast.push({
        level: 'success',
        message: mode === 'double' ? '已切换为双屏' : '已切换为单屏',
        action: {
          label: '撤销',
          onTrigger: async () => {
            await runtime.setBigScreenMode(mode === 'double' ? 'single' : 'double');
          },
        },
      });
    } catch (error) {
      toast.error('大屏模式切换失败', error instanceof Error ? error.message : '请稍后重试');
    }
  },
});

const volumeLevel = computed({
  get: () => runtime.systemVolume.level,
  set: async (next: number) => {
    try {
      await runtime.setSystemVolume(next, runtime.systemVolume.muted);
    } catch (error) {
      toast.error('系统音量设置失败', error instanceof Error ? error.message : '请稍后重试');
    }
  },
});

const muteToggle = computed({
  get: () => runtime.systemVolume.muted,
  set: async (next: boolean) => {
    try {
      await runtime.setSystemVolume(runtime.systemVolume.level, next);
    } catch (error) {
      toast.error('系统静音切换失败', error instanceof Error ? error.message : '请稍后重试');
    }
  },
});

const volumeBackendLabel = computed(() => {
  switch (runtime.systemVolume.backend) {
    case 'windows_core_audio':
      return '后端：windows_core_audio';
    case 'runtime_state':
      return '后端：runtime_state（系统接口不可用，仅本地保留）';
    default:
      return `后端：${runtime.systemVolume.backend}`;
  }
});

const volumeBackendTone = computed<'subtle' | 'warning'>(
  () => (runtime.systemVolume.backend === 'windows_core_audio' ? 'subtle' : 'warning'),
);

const heroSubtitle = computed(() => {
  const sse = runtime.sseStatus === 'connected'
    ? '实时已连接'
    : runtime.sseStatus === 'reconnecting'
      ? '正在自动重连'
      : runtime.sseStatus === 'connecting'
        ? '建立连接中'
        : '连接已关闭';
  return `${runtime.bigScreenLabel} · ${sse}`;
});

async function powerOnSplice(): Promise<void> {
  try {
    await device.power('splice_screen', 'on');
    toast.success('拼接屏开机指令已发送');
  } catch (error) {
    toast.error('拼接屏开机失败', error instanceof Error ? error.message : '请稍后重试');
  }
}

async function powerOffSplice(): Promise<void> {
  const confirmed = await dialog.danger({
    title: '拼接屏关机？',
    description:
      '将向 192.168.5.10:8889 发送关机 TCP 指令，5 秒后再发送第二帧；此过程不可中断。请确认现场无正在进行的演讲。',
    confirmLabel: '确认关机',
    cancelLabel: '取消',
  });
  if (!confirmed) return;
  try {
    await device.power('splice_screen', 'off');
    toast.warning('拼接屏关机指令已发送', '约 5 秒后第二帧 TCP 指令会自动跟进');
  } catch (error) {
    toast.error('拼接屏关机失败', error instanceof Error ? error.message : '请检查 TCP 连接');
  }
}

async function toggleTv(deviceType: 'tv_left' | 'tv_right', label: string): Promise<void> {
  try {
    await device.toggle(deviceType);
    toast.success(`${label} 切换指令已发送`, '该指令仅发送切换，不读取真实开关状态');
  } catch (error) {
    toast.error(`${label} 切换失败`, error instanceof Error ? error.message : '请稍后重试');
  }
}

const hasDeviceError = computed(() =>
  Object.values(device.lastActionResult).some((status) => status === 'error'),
);
</script>

<template>
  <div class="dashboard">
    <section class="dashboard__hero" aria-label="运行态概览">
      <p class="dashboard__hero-eyebrow">COMMAND CENTER</p>
      <h2 class="dashboard__hero-title">{{ heroSubtitle }}</h2>
      <p class="dashboard__hero-caption">
        仪表盘只承载全局运行态与顶层指令；媒体源、预案、显示控制请在左侧导航中打开。
      </p>
    </section>

    <FMessageBar v-if="hasDeviceError" tone="error" title="部分设备指令失败">
      请到「设置 → 设备电源」查看 TCP 目标与最近一次失败原因，必要时重试。
    </FMessageBar>

    <section class="dashboard__grid" aria-label="顶层指令">
      <FCard class="dashboard__card">
        <template #eyebrow>BIG SCREEN</template>
        <template #title>大屏模式</template>
        <FSegmented
          v-model="screenMode"
          :options="[
            { label: '单屏', value: 'single' },
            { label: '双屏', value: 'double' },
          ]"
          full-width
          aria--label="大屏模式选择"
        />
        <p class="dashboard__hint">
          单屏模式下窗口 2 自动静音；双屏模式下「大屏左 / 大屏右」窗口独立可控。
        </p>
      </FCard>

      <FCard class="dashboard__card">
        <template #eyebrow>SYSTEM VOLUME</template>
        <template #title>系统音量</template>
        <FSlider v-model="volumeLevel" :min="0" :max="100" aria-label="系统音量" show-value />
        <FSwitch v-model="muteToggle" label="启用系统静音" />
        <FTag :tone="volumeBackendTone">{{ volumeBackendLabel }}</FTag>
      </FCard>

      <FCard class="dashboard__card">
        <template #eyebrow>POWER</template>
        <template #title>电源指令</template>
        <div class="dashboard__power-row">
          <span class="dashboard__power-label">拼接屏</span>
          <FButton appearance="primary" icon-start="power_24_regular" @click="powerOnSplice">
            开机
          </FButton>
          <FButton appearance="danger" icon-start="plug_disconnected_24_regular" @click="powerOffSplice">
            关机
          </FButton>
        </div>
        <div class="dashboard__power-row">
          <span class="dashboard__power-label">电视左</span>
          <FButton appearance="secondary" icon-start="arrow_swap_24_regular" @click="toggleTv('tv_left', '电视左')">
            切换
          </FButton>
        </div>
        <div class="dashboard__power-row">
          <span class="dashboard__power-label">电视右</span>
          <FButton appearance="secondary" icon-start="arrow_swap_24_regular" @click="toggleTv('tv_right', '电视右')">
            切换
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
  display: flex;
  flex-direction: column;
  gap: var(--spacing-s);
  padding: var(--spacing-2xl) var(--spacing-3xl);
  border-radius: var(--radius-large);
  background:
    linear-gradient(135deg, rgba(27, 134, 224, 0.12) 0%, rgba(15, 108, 189, 0.04) 60%),
    var(--color-background-card);
  border: 1px solid var(--color-border-subtle);
}

.dashboard__hero-eyebrow {
  margin: 0;
  font-size: var(--type-caption1-size);
  letter-spacing: 0.12em;
  font-weight: 600;
  color: var(--color-text-brand);
  text-transform: uppercase;
}

.dashboard__hero-title {
  margin: 0;
  font-size: var(--type-title1-size);
  line-height: var(--type-title1-line);
  font-weight: 600;
  color: var(--color-text-primary);
}

.dashboard__hero-caption {
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
}

.dashboard__hint {
  margin: 0;
  color: var(--color-text-tertiary);
  font-size: var(--type-caption1-size);
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
