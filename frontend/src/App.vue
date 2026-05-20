<script setup lang="ts">
/**
 * 应用根组件。
 *  - meta.focus = true：全屏专注内容（PPT 专注模式），替换整个外壳；
 *  - 其余路由：单一 M3 自适应外壳 AppShell（按窗口尺寸类自切换导航形态）；
 *  - 初始化主题（system/light/dark）、应用高度变量、全局 Toast / Dialog 宿主。
 */
import { computed, onMounted, onUnmounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { RouterView, useRoute } from 'vue-router';

import AppShell from '@/layouts/AppShell.vue';
import { FDialogHost, FToastHost } from '@/design-system';
import { useReducedMotion } from '@/composables/useReducedMotion';
import { useTheme } from '@/composables/useTheme';
import { bindAppHeight } from '@/composables/useAppHeight';
import { bootstrapStores } from '@/stores';
import { useToast } from '@/composables/useToast';
import { useRuntimeStore } from '@/stores/runtime';

const route = useRoute();
const { t } = useI18n();
const toast = useToast();
const runtime = useRuntimeStore();

// 建立 data-theme 同步副作用；CSS 媒体查询负责 system 模式兜底。
useTheme();
// 暂保留 reduced 状态，便于未来在 JS 端联动；CSS 层已通过媒体查询兜底。
useReducedMotion();

const isFocusMode = computed(() => route.meta?.focus === true);

let unbindHeight: (() => void) | null = null;

onMounted(async () => {
  unbindHeight = bindAppHeight();
  try {
    await bootstrapStores();
  } catch (error) {
    toast.error(t('bootstrap.initFail'), error instanceof Error ? error.message : t('bootstrap.initFailDetail'));
  }
});

onUnmounted(() => {
  unbindHeight?.();
  runtime.disconnectEvents();
});
</script>

<template>
  <RouterView v-if="isFocusMode" />
  <AppShell v-else />
  <FDialogHost />
  <FToastHost />
</template>
