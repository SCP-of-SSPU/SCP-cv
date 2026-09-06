<script setup lang="ts">
/**
 * 应用顶栏：品牌、运行态标签、主题切换与应急菜单。
 * 从 AppShell 拆出以降低外壳组件复杂度。
 */
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { NTag } from 'naive-ui';

import EmergencyMenu from './EmergencyMenu.vue';
import ThemeToggle from './ThemeToggle.vue';
import { useRuntimeStore } from '@/stores/runtime';
import { useSessionStore } from '@/stores/sessions';

interface AppTopBarProps {
  scrolled: boolean;
}

defineProps<AppTopBarProps>();

const { t } = useI18n();
const runtime = useRuntimeStore();
const sessions = useSessionStore();

type NTagType = 'default' | 'primary' | 'info' | 'success' | 'warning' | 'error';

const sseType = computed<NTagType>(() => {
  switch (runtime.sseStatus) {
    case 'connected':
      return 'success';
    case 'reconnecting':
      return 'warning';
    case 'closed':
      return 'error';
    default:
      return 'default';
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

const playerType = computed<NTagType>(() => (sessions.hasOnlinePlayer ? 'success' : 'error'));
const playerLabel = computed(() => (sessions.hasOnlinePlayer
  ? t('app.player.online', { count: sessions.onlinePlayerCount })
  : t('app.player.offline')));
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
      <n-tag :type="runtime.isDoubleScreen ? 'info' : 'default'" round size="small">
        {{ runtime.bigScreenLabel }}
      </n-tag>
      <n-tag :type="sseType" round size="small">
        {{ sseLabel }}
      </n-tag>
      <n-tag :type="playerType" round size="small">
        {{ playerLabel }}
      </n-tag>
      <span v-if="runtime.systemVolume.muted" class="app-shell__mute">
        <span class="app-shell__mute-full">{{ t('app.systemMuted') }}</span>
        <span class="app-shell__mute-compact">{{ t('app.systemMutedCompact') }}</span>
      </span>
      <ThemeToggle />
      <EmergencyMenu />
    </div>
  </header>
</template>
