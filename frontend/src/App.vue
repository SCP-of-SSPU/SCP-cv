<script setup lang="ts">
/**
 * 应用根组件。
 *  - meta.focus = true：全屏专注内容（PPT 专注模式），替换整个外壳；
 *  - 其余路由：单一 Fluent 2 自适应外壳 AppShell（按窗口尺寸类自切换导航形态）；
 *  - 初始化主题（system/light/dark）、应用高度变量、全局 Toast / Dialog 宿主；
 *  - 顶层注入 NConfigProvider，将 @fluentui/tokens 派生的 themeOverrides 应用到
 *    Naive UI 全量组件（DESIGN.md §4.3 主题落地路径 + §5 明暗主题）。
 */
import { computed, onMounted, onUnmounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { RouterView, useRoute } from 'vue-router';
import {
  NConfigProvider,
  NDialogProvider,
  NLoadingBarProvider,
  NMessageProvider,
  NNotificationProvider,
  darkTheme,
  dateZhCN,
  zhCN,
  type GlobalThemeOverrides,
} from 'naive-ui';

import AppShell from '@/layouts/AppShell.vue';
import FDialogHost from '@/design-system/FDialogHost.vue';
import FToastHost from '@/design-system/FToastHost.vue';
import {
  fluentDarkOverrides,
  fluentLightOverrides,
} from '@/design-system/theme/naive-overrides';
import { useReducedMotion } from '@/composables/useReducedMotion';
import { useTheme } from '@/composables/useTheme';
import { bindAppHeight } from '@/composables/useAppHeight';
import { bootstrapStores } from '@/stores';
import { useToast } from '@/composables/useToast';
import { useAuthStore } from '@/stores/auth';
import { useRuntimeStore } from '@/stores/runtime';
import { watch } from 'vue';

const route = useRoute();
const { t } = useI18n();
const toast = useToast();
const auth = useAuthStore();
const runtime = useRuntimeStore();

const { effective } = useTheme();
useReducedMotion();

const isFocusMode = computed(() => route.meta?.focus === true);

// effective 是三态（system/light/dark）；system 时按 prefers-color-scheme 解析为二值。
const isDarkResolved = computed<boolean>(() => {
  if (effective.value === 'dark') return true;
  if (effective.value === 'light') return false;
  if (typeof window === 'undefined') return false;
  return window.matchMedia('(prefers-color-scheme: dark)').matches;
});

const naiveTheme = computed(() => (isDarkResolved.value ? darkTheme : null));
const naiveThemeOverrides = computed<GlobalThemeOverrides>(() =>
  isDarkResolved.value ? fluentDarkOverrides : fluentLightOverrides,
);

let unbindHeight: (() => void) | null = null;
let bootstrapped = false;

async function bootstrapWhenReady(): Promise<void> {
  if (bootstrapped || !auth.isAuthenticated) return;
  bootstrapped = true;
  try {
    await bootstrapStores();
  } catch (error) {
    toast.error(t('bootstrap.initFail'), error instanceof Error ? error.message : t('bootstrap.initFailDetail'));
  }
}

onMounted(async () => {
  unbindHeight = bindAppHeight();
  await auth.ensureInitialized();
  await bootstrapWhenReady();
});

// 用户登录后才拉业务数据；退出登录时断开 SSE，避免后端 401 风暴。
watch(
  () => auth.isAuthenticated,
  (next, prev) => {
    if (next) {
      void bootstrapWhenReady();
    } else if (prev) {
      bootstrapped = false;
      runtime.disconnectEvents();
    }
  },
);

onUnmounted(() => {
  unbindHeight?.();
  runtime.disconnectEvents();
});
</script>

<template>
  <n-config-provider
    :theme="naiveTheme"
    :theme-overrides="naiveThemeOverrides"
    :locale="zhCN"
    :date-locale="dateZhCN"
    inline-theme-disabled
  >
    <n-loading-bar-provider>
      <n-message-provider>
        <n-notification-provider placement="bottom-right">
          <n-dialog-provider>
            <RouterView v-if="isFocusMode" />
            <AppShell v-else />
            <FDialogHost />
            <FToastHost />
          </n-dialog-provider>
        </n-notification-provider>
      </n-message-provider>
    </n-loading-bar-provider>
  </n-config-provider>
</template>
