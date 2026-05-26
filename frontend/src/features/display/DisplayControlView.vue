<script setup lang="ts">
/**
 * 显示控制视图：单窗口源切换 + 播放控制。
 * 路由参数 :target 决定当前窗口；移动端额外使用 SegmentedControl 替代左侧 Nav。
 */
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRoute, useRouter } from 'vue-router';
import {
  NCard,
  NEmpty,
  NRadio,
  NRadioGroup,
  NTabs,
  NTabPane,
} from 'naive-ui';

import FIcon from '@/design-system/FIcon.vue';
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

const currentSession = computed(() => {
  if (!targetMeta.value) return undefined;
  return sessionStore.byWindowId(targetMeta.value.windowId);
});

const blocksForSingleMode = computed(
  () => targetMeta.value?.doubleScreenOnly && !runtime.isDoubleScreen,
);

const availableTargets = computed(() =>
  DISPLAY_TARGETS.filter((target) => !(target.doubleScreenOnly && !runtime.isDoubleScreen)),
);

type TabId = 'source' | 'control';
const mobileTab = ref<TabId>('source');

function changeTarget(value: string): void {
  void router.push(`/display/${value}`);
}

async function switchToDouble(): Promise<void> {
  await runtime.setBigScreenMode('double');
}

const segmentValue = computed({
  get: () => targetParam.value,
  set: (value: string) => changeTarget(value),
});
</script>

<template>
  <div class="display-view">
    <n-radio-group
      v-if="isMobile"
      v-model:value="segmentValue"
      :aria-label="t('display.windowSelectAria')"
    >
      <n-radio v-for="target in availableTargets" :key="target.param" :value="target.param">
        {{ target.title }}
      </n-radio>
    </n-radio-group>

    <header class="display-view__hero">
      <p class="display-view__eyebrow">{{ t('display.windowEyebrow', { id: targetMeta?.windowId ?? '?' }) }}</p>
      <h2 class="display-view__title">{{ targetMeta?.title ?? t('display.windowUnknown') }}{{ t('display.titleSuffix') }}</h2>
      <p class="display-view__caption">
        {{ targetMeta?.subtitle || (currentSession ? t('display.currentSource', { name: currentSession.source_name || t('display.idle') }) : t('display.loadingSession')) }}
      </p>
    </header>

    <n-card v-if="blocksForSingleMode">
      <n-empty :description="t('display.blockedDesc')">
        <template #icon>
          <FIcon name="tv_24_regular" />
        </template>
        <template #extra>
          <button class="display-view__cta" @click="switchToDouble">{{ t('display.switchToDouble') }}</button>
        </template>
      </n-empty>
    </n-card>

    <template v-else-if="!currentSession">
      <n-card>
        <n-empty :description="t('display.loadingDesc')">
          <template #icon>
            <FIcon name="info_24_regular" />
          </template>
        </n-empty>
      </n-card>
    </template>

    <template v-else-if="isMobile">
      <n-tabs v-model:value="mobileTab" type="line" :aria-label="t('display.viewSwitchAria')">
        <n-tab-pane name="source" :tab="t('display.tabSource')">
          <SourcePicker :window-id="currentSession.window_id" />
        </n-tab-pane>
        <n-tab-pane name="control" :tab="t('display.tabControl')">
          <PlaybackControl :session="currentSession" />
        </n-tab-pane>
      </n-tabs>
    </template>

    <template v-else>
      <div class="display-view__columns">
        <SourcePicker :window-id="currentSession.window_id" />
        <n-card class="display-view__playback">
          <PlaybackControl :session="currentSession" />
        </n-card>
      </div>
    </template>
  </div>
</template>

<style scoped>
.display-view {
  display: flex;
  flex-direction: column;
  gap: var(--spacingVerticalL);
  max-width: 1440px;
}

.display-view__hero {
  position: relative;
  padding: var(--spacingVerticalXXL) var(--spacingHorizontalXXXL);
  background: linear-gradient(135deg, var(--colorBrandBackground2) 0%, var(--colorNeutralBackground1) 100%);
  border-radius: var(--borderRadiusXLarge);
  border: 1px solid var(--colorNeutralStroke2);
  box-shadow: var(--shadow4);
  overflow: hidden;
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

.display-view__hero > * {
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
  margin: var(--spacingVerticalXS) 0;
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
  gap: var(--spacingHorizontalL);
  align-items: start;
}

.display-view__playback {
  min-width: 0;
}

.display-view__cta {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0 var(--spacingHorizontalL);
  height: 40px;
  border: none;
  border-radius: var(--borderRadiusMedium);
  background: var(--colorBrandBackground);
  color: #ffffff;
  font-weight: 600;
  cursor: pointer;
  box-shadow: var(--shadow2);
}

.display-view__cta:hover {
  background: var(--colorBrandBackgroundHover);
}

@media (max-width: 1023px) {
  .display-view__columns {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 767px) {
  .display-view__hero {
    padding: var(--spacingVerticalL) var(--spacingHorizontalL) var(--spacingVerticalXL);
  }

  .display-view__title {
    font-size: var(--fontSizeBase600);
    line-height: var(--lineHeightBase600);
  }
}
</style>
