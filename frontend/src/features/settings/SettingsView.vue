<script setup lang="ts">
/**
 * 设置中心：合并原「关于」内容。
 *  - AppHeader：版本号 / 端口汇总 / 入口（打开 logs / 上报）
 *  - Pivot Tabs：运行态 / 显示器 / 设备电源 / 开发
 *  - 桌面与移动同结构，Tab 在小屏内可横滑。
 */
import { computed, ref } from 'vue';

import {
  FButton,
  FCard,
  FIcon,
  FMessageBar,
  FSegmented,
  FSlider,
  FSwitch,
  FTabs,
  FTag,
} from '@/design-system';
import type { FTabsItem } from '@/design-system';
import { useDialog } from '@/composables/useDialog';
import { useThrottledSlider } from '@/composables/useThrottledSlider';
import { useToast } from '@/composables/useToast';
import { useDeviceStore } from '@/stores/devices';
import { useDisplayStore } from '@/stores/displays';
import { useRuntimeStore } from '@/stores/runtime';
import { useSessionStore } from '@/stores/sessions';
import type { DisplayTargetItem } from '@/services/api';

interface SettingsTab {
  value: 'runtime' | 'display' | 'devices' | 'dev';
  label: string;
}

const tabs: FTabsItem<SettingsTab['value']>[] = [
  { label: '运行态', value: 'runtime' },
  { label: '显示器', value: 'display' },
  { label: '设备电源', value: 'devices' },
  { label: '开发', value: 'dev' },
];

const activeTab = ref<SettingsTab['value']>('runtime');

const runtime = useRuntimeStore();
const session = useSessionStore();
const display = useDisplayStore();
const device = useDeviceStore();
const toast = useToast();
const dialog = useDialog();

const screenMode = computed({
  get: () => runtime.runtime?.big_screen_mode ?? 'single',
  set: async (mode: 'single' | 'double') => {
    try {
      await runtime.setBigScreenMode(mode);
      toast.success(mode === 'double' ? '已切换为双屏' : '已切换为单屏');
    } catch (error) {
      toast.error('切换失败', error instanceof Error ? error.message : '请稍后重试');
    }
  },
});

// 系统音量节流：与仪表盘共享同一份 store，节流策略保证拖动时不会被 PATCH 回写覆盖。
const volume = useThrottledSlider(
  () => runtime.systemVolume.level,
  {
    commit: (level: number) => runtime.setSystemVolume(level, runtime.systemVolume.muted),
    onError: (error) => {
      toast.error('系统音量设置失败', error instanceof Error ? error.message : '请稍后重试');
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
      toast.error('系统静音切换失败', error instanceof Error ? error.message : '请稍后重试');
    }
  },
});

const sseLabel = computed(() => {
  switch (runtime.sseStatus) {
    case 'connected':
      return '实时已连接';
    case 'connecting':
      return '建立连接…';
    case 'reconnecting':
      return '断开重连中';
    case 'closed':
    default:
      return '连接已关闭';
  }
});

const sseLastUpdateLabel = computed(() => {
  if (!runtime.sseLastUpdate) return '尚未收到推送';
  const date = new Date(runtime.sseLastUpdate);
  return `最近一次推送：${date.toLocaleTimeString()}`;
});

async function refreshSse(): Promise<void> {
  runtime.disconnectEvents();
  runtime.connectEvents();
  toast.info('SSE 已重新建立连接');
}

const targetWindowId = ref<number>(1);

interface DisplaySelection {
  target: DisplayTargetItem | null;
  mode: 'single' | 'left_right_splice';
  label: string;
}

const displaySelection = ref<DisplaySelection>({
  target: null,
  mode: 'single',
  label: '',
});

function pickDisplay(target: DisplayTargetItem): void {
  displaySelection.value = {
    target,
    mode: 'single',
    label: target.name,
  };
}

function pickSplice(): void {
  displaySelection.value = {
    target: null,
    mode: 'left_right_splice',
    label: display.spliceLabel,
  };
}

async function applyDisplay(): Promise<void> {
  const selection = displaySelection.value;
  if (!selection.label) {
    toast.warning('请先选择一个显示器或拼接 label');
    return;
  }
  try {
    await display.applyToWindow(targetWindowId.value, selection.mode, selection.label);
    toast.success(`已应用到窗口 ${targetWindowId.value}`);
  } catch (error) {
    toast.error('应用显示器失败', error instanceof Error ? error.message : '请稍后重试');
  }
}

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
    description: '将向 192.168.5.10:8889 发送关机 TCP 指令，5 秒后再发送第二帧；此过程不可中断。',
    confirmLabel: '确认关机',
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
    toast.success(`${label} 切换指令已发送`);
  } catch (error) {
    toast.error(`${label} 切换失败`, error instanceof Error ? error.message : '请稍后重试');
  }
}

async function resetAll(): Promise<void> {
  try {
    await session.resetAll();
    toast.success('已将所有窗口重置为待机');
  } catch (error) {
    toast.error('重置失败', error instanceof Error ? error.message : '请稍后重试');
  }
}

const backendTarget = computed(() => String(import.meta.env.VITE_BACKEND_TARGET || ''));

const portsCaption = computed(() =>
  `REST :8000 · gRPC :50051 · MediaMTX :8890/9997 · Vite :${import.meta.env.VITE_FRONTEND_PORT || '5173'}`,
);

function lastActionLabel(deviceType: string): string {
  const at = device.lastActionAt[deviceType];
  if (!at) return '尚未操作';
  const date = new Date(at);
  const detail = device.lastActionDetail[deviceType] ?? '';
  return `${date.toLocaleTimeString()} · ${detail}`;
}

const version = '1.0.0';
</script>

<template>
  <div class="settings-view">
    <header class="settings-view__app-header">
      <div class="settings-view__brand">
        <span class="settings-view__brand-mark">S</span>
        <div>
          <p class="settings-view__brand-eyebrow">SCP-cv</p>
          <h2 class="settings-view__brand-title">播放控制台 · v{{ version }}</h2>
          <p class="settings-view__brand-caption">{{ portsCaption }}</p>
        </div>
      </div>
      <div class="settings-view__app-actions">
        <FButton appearance="secondary" icon-start="open_24_regular" :disabled="true" aria-label="桌面壳层未启用">
          打开 logs/
        </FButton>
        <FButton appearance="subtle" icon-start="info_24_regular"
          @click="() => toast.info('请把控制台日志反馈给现场维护人员', '若可附带错误代码与时间戳更佳')">
          上报问题
        </FButton>
      </div>
    </header>

    <FTabs v-model="activeTab" :items="tabs" appearance="line" full-width aria-label="设置分组" />

    <!-- 运行态 -->
    <section v-if="activeTab === 'runtime'" class="settings-view__grid">
      <FCard padding="cozy">
        <template #title>大屏模式</template>
        <FSegmented v-model="screenMode" :options="[
          { label: '单屏', value: 'single' },
          { label: '双屏', value: 'double' },
        ]" full-width />
        <p class="settings-view__hint">
          单屏模式下窗口 2 自动静音；双屏模式可独立控制大屏左 / 右。
        </p>
      </FCard>

      <FCard padding="cozy">
        <template #title>系统音量</template>
        <FSlider :model-value="volume.value.value" :min="0" :max="100" show-value aria-label="系统音量"
          @update:modelValue="volume.handleInput" @change="volume.handleChange" />
        <FSwitch v-model="muteToggle" label="启用系统静音" />
        <FTag :tone="runtime.systemVolume.backend === 'windows_core_audio' ? 'subtle' : 'warning'">
          后端：{{ runtime.systemVolume.backend }}
        </FTag>
      </FCard>

      <FCard padding="cozy">
        <template #title>SSE 状态</template>
        <p class="settings-view__row">
          <FTag :tone="runtime.sseStatus === 'connected' ? 'success' : 'warning'"
            :dot="runtime.sseStatus === 'reconnecting'">
            {{ sseLabel }}
          </FTag>
          <span>{{ sseLastUpdateLabel }}</span>
        </p>
        <FButton appearance="secondary" icon-start="arrow_clockwise_24_regular" @click="refreshSse">
          重新建立连接
        </FButton>
      </FCard>

      <FCard padding="cozy">
        <template #title>应急工具</template>
        <FButton appearance="danger" icon-start="arrow_reset_24_regular" @click="resetAll">
          重置全部窗口
        </FButton>
        <p class="settings-view__hint">
          紧急时可一键将所有窗口重置为待机；该操作不会影响媒体源库与预案。
        </p>
      </FCard>
    </section>

    <!-- 显示器 -->
    <section v-if="activeTab === 'display'" class="settings-view__display">
      <FCard padding="cozy">
        <template #title>窗口选择</template>
        <FSegmented v-model="targetWindowId" :options="[
          { label: '窗口 1', value: 1 },
          { label: '窗口 2', value: 2 },
          { label: '窗口 3', value: 3 },
          { label: '窗口 4', value: 4 },
        ]" full-width />
      </FCard>

      <FCard padding="cozy">
        <template #title>可用显示器</template>
        <div class="settings-view__display-grid">
          <button v-for="target in display.targets" :key="target.index" type="button"
            class="settings-view__display-tile"
            :class="{ 'settings-view__display-tile--selected': displaySelection.label === target.name && displaySelection.mode === 'single' }"
            @click="pickDisplay(target)">
            <p class="settings-view__display-name">Display {{ target.index + 1 }}</p>
            <p class="settings-view__display-meta">{{ target.width }} × {{ target.height }}</p>
            <p class="settings-view__display-meta">({{ target.x }}, {{ target.y }})</p>
            <FIcon v-if="target.is_primary" class="settings-view__display-primary" name="star_24_filled" />
          </button>
          <button type="button" class="settings-view__display-tile settings-view__display-tile--splice"
            :class="{ 'settings-view__display-tile--selected': displaySelection.mode === 'left_right_splice' }"
            :disabled="!display.spliceLabel" @click="pickSplice">
            <p class="settings-view__display-name">{{ display.spliceLabel || '尚未配置拼接' }}</p>
            <p class="settings-view__display-meta">左右拼接显示</p>
          </button>
        </div>
      </FCard>

      <FButton appearance="primary" icon-start="checkmark_24_regular" :disabled="!displaySelection.label"
        @click="applyDisplay">
        应用到窗口 {{ targetWindowId }}
      </FButton>
    </section>

    <!-- 设备电源 -->
    <section v-if="activeTab === 'devices'" class="settings-view__grid">
      <FCard padding="cozy">
        <template #title>拼接屏</template>
        <p class="settings-view__hint">
          TCP 192.168.5.10:8889；关机为 Danger 操作，第二帧 5 秒后自动跟进。
        </p>
        <div class="settings-view__row">
          <FButton appearance="primary" icon-start="power_24_regular" @click="powerOnSplice">开机</FButton>
          <FButton appearance="danger" icon-start="plug_disconnected_24_regular" @click="powerOffSplice">
            关机
          </FButton>
        </div>
        <p class="settings-view__hint">
          上次操作：{{ lastActionLabel('splice_screen') }}
        </p>
        <FMessageBar v-if="device.lastActionResult.splice_screen === 'error'" tone="error" title="拼接屏 TCP 失败">
          {{ device.lastActionDetail.splice_screen }}
        </FMessageBar>
      </FCard>

      <FCard padding="cozy">
        <template #title>电视</template>
        <p class="settings-view__hint">仅发送切换指令，不会读取真实开关状态。</p>
        <div class="settings-view__row">
          <FButton appearance="secondary" icon-start="arrow_swap_24_regular" @click="toggleTv('tv_left', '电视左')">
            电视左 切换
          </FButton>
          <FButton appearance="secondary" icon-start="arrow_swap_24_regular" @click="toggleTv('tv_right', '电视右')">
            电视右 切换
          </FButton>
        </div>
        <p class="settings-view__hint">
          电视左 上次操作：{{ lastActionLabel('tv_left') }}<br />
          电视右 上次操作：{{ lastActionLabel('tv_right') }}
        </p>
      </FCard>
    </section>

    <!-- 开发 -->
    <section v-if="activeTab === 'dev'" class="settings-view__grid">
      <FCard padding="cozy">
        <template #title>API 端点</template>
        <ul class="settings-view__api-list">
          <li><code>{{ backendTarget }}/api/sources/</code></li>
          <li><code>{{ backendTarget }}/api/scenarios/</code></li>
          <li><code>{{ backendTarget }}/api/sessions/</code></li>
          <li><code>{{ backendTarget }}/api/runtime/</code></li>
          <li><code>{{ backendTarget }}/api/events/</code></li>
        </ul>
      </FCard>

      <FCard padding="cozy">
        <template #title>端口汇总</template>
        <p class="settings-view__hint">{{ portsCaption }}</p>
      </FCard>

      <FCard padding="cozy">
        <template #title>日志路径</template>
        <p class="settings-view__hint">
          后端会写入项目根 <code>logs/*.log</code>；前端日志请打开浏览器 DevTools 查看。
        </p>
      </FCard>

      <FCard padding="cozy">
        <template #title>环境变量</template>
        <p class="settings-view__hint">
          前端读 <code>frontend/.env</code> 中的 <code>VITE_FRONTEND_PORT</code> 与 <code>VITE_BACKEND_TARGET</code>；
          根目录 <code>.env</code> 用于后端与 MediaMTX。
        </p>
      </FCard>
    </section>
  </div>
</template>

<style scoped>
.settings-view {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-l);
  max-width: 1280px;
}

.settings-view__app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-l);
  padding: var(--spacing-l) var(--spacing-2xl);
  background: var(--color-background-card);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-large);
  flex-wrap: wrap;
}

.settings-view__brand {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-m);
  min-width: 0;
}

.settings-view__brand-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  border-radius: var(--radius-medium);
  background: var(--color-background-brand);
  color: var(--color-text-inverse);
  font-weight: 700;
  font-size: var(--type-title3-size);
}

.settings-view__brand-eyebrow {
  margin: 0;
  font-size: var(--type-caption2-size);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--color-text-tertiary);
}

.settings-view__brand-title {
  margin: 2px 0 0;
  font-size: var(--type-title3-size);
  line-height: var(--type-title3-line);
  font-weight: 600;
}

.settings-view__brand-caption {
  margin: 4px 0 0;
  color: var(--color-text-secondary);
  font-size: var(--type-caption1-size);
}

.settings-view__app-actions {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-s);
}

.settings-view__grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: var(--spacing-l);
}

.settings-view__display {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-l);
}

.settings-view__display-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: var(--spacing-m);
}

.settings-view__display-tile {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
  padding: var(--spacing-l);
  border-radius: var(--radius-large);
  border: 1px solid var(--color-border-subtle);
  background: var(--color-background-card);
  cursor: pointer;
  font: inherit;
  text-align: left;
}

.settings-view__display-tile:hover:not(:disabled) {
  border-color: var(--color-background-brand);
}

.settings-view__display-tile--selected {
  border-color: var(--color-background-brand);
  box-shadow: 0 0 0 1px var(--color-background-brand);
  background: var(--color-background-brand-selected);
}

.settings-view__display-tile--splice {
  background: var(--color-background-subtle);
}

.settings-view__display-tile:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.settings-view__display-name {
  margin: 0;
  font-weight: 600;
}

.settings-view__display-meta {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: var(--type-caption1-size);
}

.settings-view__display-primary {
  position: absolute;
  top: var(--spacing-s);
  right: var(--spacing-s);
  color: var(--color-text-warning);
  width: 18px;
  height: 18px;
}

.settings-view__row {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-s);
  flex-wrap: wrap;
}

.settings-view__hint {
  margin: 0;
  color: var(--color-text-tertiary);
  font-size: var(--type-caption1-size);
}

.settings-view__api-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.settings-view__api-list code {
  font-family: var(--font-family-mono);
  background: var(--color-background-subtle);
  padding: 2px var(--spacing-s);
  border-radius: var(--radius-small);
  word-break: break-all;
}

@media (max-width: 767px) {
  .settings-view__app-header {
    padding: var(--spacing-l);
  }

  .settings-view__app-actions {
    width: 100%;
    justify-content: flex-end;
  }
}
</style>
