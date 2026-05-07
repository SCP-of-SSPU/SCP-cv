<script setup lang="ts">
/**
 * 应用根组件：根据路由 meta.focus 与当前断点切换 Shell。
 *  - meta.focus = true：完全替换 Shell 为全屏专注内容（PPT 专注模式）；
 *  - 桌面（≥ md）：AppShell；
 *  - 移动（< md）：MobileShell；
 *  - 全局挂载 ToastHost 与 DialogHost。
 */
import { computed, onMounted, onUnmounted } from 'vue';
import { RouterView, useRoute } from 'vue-router';

import AppShell from '@/layouts/AppShell.vue';
import MobileShell from '@/layouts/MobileShell.vue';
import { FDialogHost, FToastHost } from '@/design-system';
import { useBreakpoint } from '@/composables/useBreakpoint';
import { useReducedMotion } from '@/composables/useReducedMotion';
import { bindAppHeight } from '@/composables/useAppHeight';
import { bootstrapStores } from '@/stores';
import { useToast } from '@/composables/useToast';
import { useRuntimeStore } from '@/stores/runtime';

const route = useRoute();
const { isMobile } = useBreakpoint();
const toast = useToast();
const runtime = useRuntimeStore();

// 暂保留 reduced 状态，便于未来在 JS 端联动；CSS 层已通过媒体查询兜底。
useReducedMotion();

const isFocusMode = computed(() => route.meta?.focus === true);

let unbindHeight: (() => void) | null = null;

onMounted(async () => {
  unbindHeight = bindAppHeight();
  try {
    await bootstrapStores();
  } catch (error) {
    toast.error('初始化失败', error instanceof Error ? error.message : '请刷新页面或检查后端');
  }
});

onUnmounted(() => {
  unbindHeight?.();
  runtime.disconnectEvents();
});
</script>

<template>
  <RouterView v-if="isFocusMode" />
  <AppShell v-else-if="!isMobile" />
  <MobileShell v-else />
  <FDialogHost />
  <FToastHost />
</template>

<style>
@import '@/styles/base.css';
</style>
