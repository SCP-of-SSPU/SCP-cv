<script setup lang="ts">
/**
 * 显示控制视图：单窗口源切换 + 播放控制。
 * 路由参数 :target 决定当前窗口；移动端额外使用 SegmentedControl 替代左侧 Nav。
 */
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
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

const { t } = useI18n();
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

const tabItems = computed<FTabsItem<TabId>[]>(() => [
  { label: t('display.tabSource'), value: 'source' },
  { label: t('display.tabControl'), value: 'control' },
]);

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
    <FSegmented v-if="isMobile" :model-value="targetParam" :options="segmentOptions" full-width :aria-label="t('display.windowSelectAria')"
      @update:modelValue="(value) => changeTarget(value as string)" />

    <header class="display-view__hero">
      <p class="display-view__eyebrow">{{ t('display.windowEyebrow', { id: targetMeta?.windowId ?? '?' }) }}</p>
      <h2 class="display-view__title">{{ targetMeta?.title ?? t('display.windowUnknown') }}{{ t('display.titleSuffix') }}</h2>
      <p class="display-view__caption">
        {{ targetMeta?.subtitle || (currentSession ? t('display.currentSource', { name: currentSession.source_name || t('display.idle') }) : t('display.loadingSession')) }}
      </p>
    </header>

    <FCard v-if="blocksForSingleMode" padding="cozy">
      <FEmpty :title="t('display.blockedTitle')" :description="t('display.blockedDesc')" icon="tv_24_regular">
        <template #actions>
          <button class="display-view__cta" @click="switchToDouble">{{ t('display.switchToDouble') }}</button>
        </template>
      </FEmpty>
    </FCard>

    <template v-else-if="!currentSession">
      <FCard padding="cozy">
        <FEmpty :title="t('display.loadingTitle')" :description="t('display.loadingDesc')" icon="info_24_regular" />
      </FCard>
    </template>

    <template v-else-if="isMobile">
      <FTabs v-model="mobileTab" :items="tabItems" appearance="line" full-width :aria-label="t('display.viewSwitchAria')" />
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
  position: relative;
  padding: var(--spacing-2xl) var(--spacing-3xl);
  background: var(--gradient-hero-cool);
  border-radius: var(--borderRadiusXLarge);
  border: 1px solid color-mix(in srgb, var(--colorNeutralStroke2) 70%, transparent);
  box-shadow: var(--shadow-card), var(--ring-accent);
  overflow: hidden;
  animation: f-rise var(--motion-duration-entrance) var(--motion-curve-emphasized) both;
}

.display-view__hero::after {
  content: '';
  position: absolute;
  right: -80px;
  top: -80px;
  width: 220px;
  height: 220px;
  border-radius: var(--borderRadiusCircular);
  background: radial-gradient(circle at center,
      color-mix(in srgb, var(--colorBrandBackground) 22%, transparent),
      transparent 70%);
  pointer-events: none;
}

.display-view__hero>* {
  position: relative;
  z-index: 1;
}

.display-view__eyebrow {
  margin: 0;
  font-size: var(--fontSizeBase200);
  font-weight: 600;
  color: var(--colorBrandForeground1);
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.display-view__title {
  margin: var(--spacing-xs) 0;
  font-size: var(--fontSizeHero700);
  line-height: var(--lineHeightHero700);
  font-weight: 600;
}

.display-view__caption {
  margin: 0;
  color: var(--colorNeutralForeground2);
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
  border-radius: var(--borderRadiusMedium);
  background: var(--colorBrandBackground);
  color: var(--color-text-inverse);
  font-weight: 600;
  cursor: pointer;
  box-shadow: var(--shadow-brand);
  transition:
    background var(--motion-duration-medium) var(--motion-curve-ease),
    box-shadow var(--motion-duration-medium) var(--motion-curve-ease),
    transform var(--motion-duration-fast) var(--motion-curve-ease);
}

.display-view__cta:hover {
  background: var(--colorBrandBackgroundHover);
  box-shadow: var(--shadow-brand-hover);
  transform: translateY(-1px);
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
    font-size: var(--fontSizeBase600);
    line-height: var(--lineHeightBase600);
  }
}
</style>
