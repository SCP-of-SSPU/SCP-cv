<script setup lang="ts">
/**
 * 显示控制视图：单窗口源切换 + 播放控制。
 * 路由参数 :target 决定当前窗口；移动端额外使用 SegmentedControl 替代左侧 Nav。
 */
import { computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import {
  FCard,
  FEmpty,
  FSegmented,
  FTabs,
} from '@/design-system';
import type { FSegmentedOption, FTabsItem } from '@/design-system';
import PlaybackControl from './PlaybackControl.vue';
import SourcePicker from './SourcePicker.vue';
import { DISPLAY_TARGETS, resolveDisplayTarget } from './displayTargets';
import { useBreakpoint } from '@/composables/useBreakpoint';
import { useRuntimeStore } from '@/stores/runtime';
import { useSessionStore } from '@/stores/sessions';

const route = useRoute();
const router = useRouter();
const runtime = useRuntimeStore();
const sessionStore = useSessionStore();
const { isMobile } = useBreakpoint();

const targetParam = computed(() => String(route.params.target ?? 'big-left'));
const targetMeta = computed(() => resolveDisplayTarget(targetParam.value));

/** 当前窗口的会话；可能为 undefined（启动初期未拉到数据时）。 */
const currentSession = computed(() => {
  if (!targetMeta.value) return undefined;
  return sessionStore.byWindowId(targetMeta.value.windowId);
});

const blocksForSingleMode = computed(
  () => targetMeta.value?.doubleScreenOnly && !runtime.isDoubleScreen,
);

const segmentOptions = computed<FSegmentedOption<string>[]>(() => {
  const options = DISPLAY_TARGETS.filter((target) => !(target.doubleScreenOnly && !runtime.isDoubleScreen)).map(
    (target) => ({
      label: target.title,
      value: target.param,
    }),
  );
  return options;
});

type TabId = 'source' | 'control';
const activeTab = computed({
  get: (): TabId => 'source',
  set: () => undefined,
});

const tabItems: FTabsItem<TabId>[] = [
  { label: '切换源', value: 'source' },
  { label: '播放控制', value: 'control' },
];

const mobileActiveTab = computed({
  get: () => (activeTab.value as TabId),
  set: (value: TabId) => {
    void value;
  },
});

const localTab = computed({
  get: (): TabId => 'source',
  set: () => undefined,
});

void localTab; // 保留以备未来扩展持久化

import { ref } from 'vue';
const mobileTab = ref<TabId>('source');

function changeTarget(value: string): void {
  void router.push(`/display/${value}`);
}

async function switchToDouble(): Promise<void> {
  await runtime.setBigScreenMode('double');
}

void tabItems;
</script>

<template>
  <div class="display-view">
    <FSegmented
      v-if="isMobile"
      :model-value="targetParam"
      :options="segmentOptions"
      full-width
      aria-label="窗口选择"
      @update:modelValue="(value) => changeTarget(value as string)"
    />

    <header class="display-view__hero">
      <p class="display-view__eyebrow">Window {{ targetMeta?.windowId ?? '?' }}</p>
      <h2 class="display-view__title">{{ targetMeta?.title ?? '未知窗口' }}显示控制</h2>
      <p class="display-view__caption">
        {{ targetMeta?.subtitle || (currentSession ? `当前：${currentSession.source_name || '空闲'}` : '正在加载会话…') }}
      </p>
    </header>

    <FCard v-if="blocksForSingleMode" padding="cozy">
      <FEmpty
        title="单屏模式下「大屏右」不可控"
        description="当前运行态为单屏；窗口 2 由系统自动静音。如需独立控制，请切换到双屏模式。"
        icon="tv_24_regular"
      >
        <template #actions>
          <button class="display-view__cta" @click="switchToDouble">切换到双屏</button>
        </template>
      </FEmpty>
    </FCard>

    <template v-else-if="!currentSession">
      <FCard padding="cozy">
        <FEmpty
          title="正在加载会话状态"
          description="若长时间无响应，请检查后端服务或在「应急 → 重置全部窗口」恢复。"
          icon="info_24_regular"
        />
      </FCard>
    </template>

    <template v-else-if="isMobile">
      <FTabs v-model="mobileTab" :items="tabItems" appearance="line" full-width aria-label="显示控制视图切换" />
      <SourcePicker v-if="mobileTab === 'source'" :window-id="currentSession.window_id" />
      <PlaybackControl v-else :session="currentSession" />
    </template>

    <template v-else>
      <div class="display-view__columns">
        <SourcePicker :window-id="currentSession.window_id" />
        <FCard padding="cozy" class="display-view__playback">
          <PlaybackControl :session="currentSession" />
        </FCard>
      </div>
    </template>
  </div>
</template>

<style scoped>
.display-view {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-l);
  max-width: 1440px;
}

.display-view__hero {
  padding: var(--spacing-2xl) var(--spacing-3xl);
  background: var(--color-background-brand-selected);
  border-radius: var(--radius-large);
  border: 1px solid var(--color-border-subtle);
}

.display-view__eyebrow {
  margin: 0;
  font-size: var(--type-caption1-size);
  font-weight: 600;
  color: var(--color-text-brand);
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.display-view__title {
  margin: var(--spacing-xs) 0;
  font-size: var(--type-title2-size);
  line-height: var(--type-title2-line);
  font-weight: 600;
}

.display-view__caption {
  margin: 0;
  color: var(--color-text-secondary);
}

.display-view__columns {
  display: grid;
  grid-template-columns: minmax(320px, 5fr) minmax(360px, 7fr);
  gap: var(--spacing-l);
  align-items: start;
}

.display-view__playback {
  min-width: 0;
}

.display-view__cta {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0 var(--spacing-l);
  height: 40px;
  border: none;
  border-radius: var(--radius-medium);
  background: var(--color-background-brand);
  color: var(--color-text-inverse);
  font-weight: 600;
  cursor: pointer;
}

.display-view__cta:hover {
  background: var(--color-background-brand-hover);
}

@media (max-width: 1023px) {
  .display-view__columns {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 767px) {
  .display-view__hero {
    padding: var(--spacing-l) var(--spacing-l) var(--spacing-xl);
  }

  .display-view__title {
    font-size: var(--type-title3-size);
    line-height: var(--type-title3-line);
  }
}
</style>
