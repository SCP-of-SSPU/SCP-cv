<script setup lang="ts">
/**
 * AppShell 导航区域：桌面 rail/drawer 与 compact bottom navigation。
 * 通过 props 接收已按运行态过滤/命名的导航条目，保持父组件只负责布局状态。
 */
import { useI18n } from 'vue-i18n';
import { RouterLink } from 'vue-router';
import { NDivider } from 'naive-ui';

import MoreSheet from './MoreSheet.vue';
import { DESKTOP_SECONDARY_NAV, MOBILE_TAB_BAR } from './navItems';
import type { NavItemDef } from './types';
import FIcon from '@/design-system/FIcon.vue';

interface AppNavigationProps {
  compact: boolean;
  navVariant: 'bottom' | 'rail' | 'drawer';
  primaryItems: NavItemDef[];
  moreOpen: boolean;
  isActive: (path: string) => boolean;
}

defineProps<AppNavigationProps>();

const emit = defineEmits<{
  (event: 'update:moreOpen', value: boolean): void;
  (event: 'bottomClick', path: string, value: MouseEvent): void;
}>();

const { t } = useI18n();
</script>

<template>
  <nav
    v-if="!compact"
    class="app-shell__nav sticky top-14 flex h-[calc(var(--app-height,100dvh)-3.5rem)] shrink-0 self-start flex-col gap-4 overflow-y-auto py-4"
    :class="navVariant === 'drawer' ? 'w-60 bg-surface-subtle px-4' : 'w-[5.5rem] items-center bg-surface px-2'"
    :data-variant="navVariant"
    :aria-label="t('app.primaryNav')"
  >
    <ul class="app-shell__nav-list m-0 flex w-full list-none flex-col gap-1 p-0">
      <li v-for="item in primaryItems" :key="item.path">
        <RouterLink
          :to="item.path"
          class="app-shell__nav-item flex min-h-12 items-center rounded-md py-2 font-semibold text-foreground-muted no-underline"
          :class="[
            navVariant === 'rail' ? 'w-full flex-col gap-1 px-1 text-center' : 'gap-4 px-4',
            { 'app-shell__nav-item--active': isActive(item.path) },
          ]"
          :aria-current="isActive(item.path) ? 'page' : undefined"
        >
          <span
            class="app-shell__nav-indicator grid shrink-0 place-items-center"
            :class="navVariant === 'rail' ? 'h-8 w-14 rounded-md' : ''"
          >
            <FIcon
              class="app-shell__nav-icon text-2xl"
              :name="(isActive(item.path) && item.iconSelected) || item.icon"
            />
          </span>
          <span
            class="app-shell__nav-label max-w-full truncate whitespace-nowrap"
            :class="navVariant === 'rail' ? 'text-xs' : ''"
          >{{ item.label }}</span>
        </RouterLink>
      </li>
    </ul>

    <n-divider />

    <ul class="app-shell__nav-list m-0 flex w-full list-none flex-col gap-1 p-0">
      <li v-for="item in DESKTOP_SECONDARY_NAV" :key="item.path">
        <RouterLink
          :to="item.path"
          class="app-shell__nav-item flex min-h-12 items-center rounded-md py-2 font-semibold text-foreground-muted no-underline"
          :class="[
            navVariant === 'rail' ? 'w-full flex-col gap-1 px-1 text-center' : 'gap-4 px-4',
            { 'app-shell__nav-item--active': isActive(item.path) },
          ]"
          :aria-current="isActive(item.path) ? 'page' : undefined"
        >
          <span
            class="app-shell__nav-indicator grid shrink-0 place-items-center"
            :class="navVariant === 'rail' ? 'h-8 w-14 rounded-md' : ''"
          >
            <FIcon
              class="app-shell__nav-icon text-2xl"
              :name="(isActive(item.path) && item.iconSelected) || item.icon"
            />
          </span>
          <span
            class="app-shell__nav-label max-w-full truncate whitespace-nowrap"
            :class="navVariant === 'rail' ? 'text-xs' : ''"
          >{{ item.label }}</span>
        </RouterLink>
      </li>
    </ul>
  </nav>

  <nav
    v-if="compact"
    class="app-shell__bottom sticky bottom-0 z-[var(--z-sticky)] grid grid-cols-5 gap-1 bg-surface-subtle px-1 pt-2 pb-[calc(0.5rem+env(safe-area-inset-bottom,0px))] shadow-panel"
    :aria-label="t('app.primaryNav')"
  >
    <a
      v-for="item in MOBILE_TAB_BAR"
      :key="item.path"
      :href="item.path"
      class="app-shell__bottom-item flex min-h-[3.25rem] flex-col items-center justify-center gap-0.5 py-1 text-foreground-muted no-underline"
      :class="{ 'app-shell__bottom-item--active': isActive(item.path) }"
      :aria-current="isActive(item.path) ? 'page' : undefined"
      @click.prevent="(event) => emit('bottomClick', item.path, event)"
    >
      <span class="app-shell__bottom-indicator grid h-8 w-16 place-items-center rounded-md">
        <FIcon
          class="app-shell__bottom-icon text-2xl"
          :name="(isActive(item.path) && item.iconSelected) || item.icon"
        />
      </span>
      <span class="app-shell__bottom-label text-xs font-semibold">{{ item.label }}</span>
    </a>
  </nav>

  <MoreSheet :open="moreOpen" @update:open="(value) => emit('update:moreOpen', value)" />
</template>
