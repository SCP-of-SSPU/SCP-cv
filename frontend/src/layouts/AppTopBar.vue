<script setup lang="ts">
/**
 * 应用顶栏：品牌、运行态标签、主题切换与应急菜单。
 * 从 AppShell 拆出以降低外壳组件复杂度。
 */
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';

import EmergencyMenu from './EmergencyMenu.vue';
import ThemeToggle from './ThemeToggle.vue';
import { FTag } from '@/design-system';
import { useRuntimeStore } from '@/stores/runtime';

interface AppTopBarProps {
  scrolled: boolean;
}

defineProps<AppTopBarProps>();

const { t } = useI18n();
const runtime = useRuntimeStore();

const sseTone = computed<'success' | 'warning' | 'subtle' | 'error'>(() => {
  switch (runtime.sseStatus) {
    case 'connected':
      return 'success';
    case 'reconnecting':
      return 'warning';
    case 'closed':
      return 'error';
    default:
      return 'subtle';
  }
});

const sseLabel = computed(() => {
  switch (runtime.sseStatus) {
    case 'connected':
      return t('app.sse.connected');
    case 'connecting':
      return t('app.sse.connecting');
    case 'reconnecting':
      return t('app.sse.reconnecting');
    default:
      return t('app.sse.closed');
  }
});
</script>

<template>
  <header class="app-shell__bar" :class="{ 'app-shell__bar--scrolled': scrolled }" role="banner">
    <div class="app-shell__brand">
      <span class="app-shell__brand-mark" aria-hidden="true">S</span>
      <div class="app-shell__brand-meta">
        <p class="app-shell__brand-eyebrow">{{ t('app.brandEyebrow') }}</p>
        <h1 class="app-shell__brand-title">{{ t('app.brandTitle') }}</h1>
      </div>
    </div>

    <div class="app-shell__bar-meta">
      <FTag :tone="runtime.isDoubleScreen ? 'info' : 'subtle'">
        {{ runtime.bigScreenLabel }}
      </FTag>
      <FTag :tone="sseTone" :dot="runtime.sseStatus === 'reconnecting'">
        {{ sseLabel }}
      </FTag>
      <span v-if="runtime.systemVolume.muted" class="app-shell__mute">{{ t('app.systemMuted') }}</span>
      <ThemeToggle />
      <EmergencyMenu />
    </div>
  </header>
</template>
