<script setup lang="ts">
/**
 * M3 自适应应用外壳（DESIGN.md §12.3 规范导航）。
 *  - Compact：底部导航栏（3–5 项，溢出走「更多」Sheet）；
 *  - Medium / Expanded：导航轨道（navigation rail，图标 + 短标签）；
 *  - Large / Extra-large：持久导航抽屉（navigation drawer，图标 + 标签）；
 *  - 选中目的地与 aria-current 随导航形态切换保持一致（N2 / N3）；
 *  - 顶部 App bar：唯一 <h1>、运行态 Tag、主题切换、应急菜单；
 *    内容滚动时由 0 级升至 2 级（E3）；
 *  - 首个可聚焦元素为「跳到主内容」（A4），landmark 完整（R14）。
 */
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { RouterView, useRoute, useRouter } from 'vue-router';

import AppNavigation from './AppNavigation.vue';
import AppTopBar from './AppTopBar.vue';
import {
  DESKTOP_PRIMARY_NAV,
  resolveDisplayLabel,
} from './navItems';
import type { NavItemDef } from './types';
import { useWindowSizeClass } from '@/composables/useWindowSizeClass';
import { useRuntimeStore } from '@/stores/runtime';

const { t } = useI18n();
const route = useRoute();
const router = useRouter();
const runtime = useRuntimeStore();
const { sizeClass, isCompact, isLargeUp } = useWindowSizeClass();

const moreOpen = ref(false);
const scrolled = ref(false);
const mainRef = ref<HTMLElement | null>(null);

/** 导航形态：compact 底栏 / rail 轨道 / drawer 抽屉。 */
const navVariant = computed<'bottom' | 'rail' | 'drawer'>(() =>
  isCompact.value ? 'bottom' : isLargeUp.value ? 'drawer' : 'rail',
);

const primaryItems = computed<NavItemDef[]>(() =>
  DESKTOP_PRIMARY_NAV.filter(
    (item) => !(item.doubleScreenOnly && !runtime.isDoubleScreen),
  ).map((item) => ({
    ...item,
    label: item.path.startsWith('/display/')
      ? resolveDisplayLabel(item.path, runtime.isDoubleScreen)
      : item.label,
  })),
);

function isActive(path: string): boolean {
  if (path === '/dashboard') return route.path === '/' || route.path === '/dashboard';
  if (path === '/display/big-left' && isCompact.value) {
    return route.path.startsWith('/display/');
  }
  return route.path === path;
}

function onBottomClick(path: string, event: MouseEvent): void {
  if (path === '/more') {
    event.preventDefault();
    moreOpen.value = true;
    return;
  }
  void router.push(path);
}

function onMainScroll(): void {
  scrolled.value = (mainRef.value?.scrollTop ?? 0) > 4;
}

onMounted(() => {
  mainRef.value?.addEventListener('scroll', onMainScroll, { passive: true });
});

onBeforeUnmount(() => {
  mainRef.value?.removeEventListener('scroll', onMainScroll);
});
</script>

<template>
  <a class="skip-link" href="#main-content">{{ t('app.skipToMain') }}</a>

  <div class="app-shell" :data-size="sizeClass" :data-nav="navVariant">
    <AppTopBar :scrolled="scrolled" />

    <div class="app-shell__body">
      <AppNavigation
        v-if="!isCompact"
        v-model:more-open="moreOpen"
        :compact="false"
        :nav-variant="navVariant"
        :primary-items="primaryItems"
        :is-active="isActive"
        @bottom-click="onBottomClick"
      />

      <main id="main-content" ref="mainRef" class="app-shell__content" tabindex="-1">
        <RouterView />
      </main>
    </div>

    <AppNavigation
      v-if="isCompact"
      v-model:more-open="moreOpen"
      compact
      :nav-variant="navVariant"
      :primary-items="primaryItems"
      :is-active="isActive"
      @bottom-click="onBottomClick"
    />
  </div>
</template>

<style src="./AppShell.css"></style>
