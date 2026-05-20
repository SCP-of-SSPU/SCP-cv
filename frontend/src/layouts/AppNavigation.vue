<script setup lang="ts">
/**
 * AppShell 导航区域：桌面 rail/drawer 与 compact bottom navigation。
 * 通过 props 接收已按运行态过滤/命名的导航条目，保持父组件只负责布局状态。
 */
import { useI18n } from 'vue-i18n';
import { RouterLink } from 'vue-router';

import MoreSheet from './MoreSheet.vue';
import { DESKTOP_SECONDARY_NAV, MOBILE_TAB_BAR } from './navItems';
import type { NavItemDef } from './types';
import { FDivider, FIcon } from '@/design-system';

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
    class="app-shell__nav"
    :data-variant="navVariant"
    :aria-label="t('app.primaryNav')"
  >
    <ul class="app-shell__nav-list">
      <li v-for="item in primaryItems" :key="item.path">
        <RouterLink
          :to="item.path"
          class="app-shell__nav-item"
          :class="{ 'app-shell__nav-item--active': isActive(item.path) }"
          :aria-current="isActive(item.path) ? 'page' : undefined"
        >
          <span class="app-shell__nav-indicator">
            <FIcon
              class="app-shell__nav-icon"
              :name="(isActive(item.path) && item.iconSelected) || item.icon"
            />
          </span>
          <span class="app-shell__nav-label">{{ item.label }}</span>
        </RouterLink>
      </li>
    </ul>

    <FDivider />

    <ul class="app-shell__nav-list">
      <li v-for="item in DESKTOP_SECONDARY_NAV" :key="item.path">
        <RouterLink
          :to="item.path"
          class="app-shell__nav-item"
          :class="{ 'app-shell__nav-item--active': isActive(item.path) }"
          :aria-current="isActive(item.path) ? 'page' : undefined"
        >
          <span class="app-shell__nav-indicator">
            <FIcon
              class="app-shell__nav-icon"
              :name="(isActive(item.path) && item.iconSelected) || item.icon"
            />
          </span>
          <span class="app-shell__nav-label">{{ item.label }}</span>
        </RouterLink>
      </li>
    </ul>
  </nav>

  <nav v-if="compact" class="app-shell__bottom" :aria-label="t('app.primaryNav')">
    <RouterLink
      v-for="item in MOBILE_TAB_BAR"
      :key="item.path"
      :to="item.path"
      class="app-shell__bottom-item"
      :class="{ 'app-shell__bottom-item--active': isActive(item.path) }"
      :aria-current="isActive(item.path) ? 'page' : undefined"
      @click="(event) => emit('bottomClick', item.path, event)"
    >
      <span class="app-shell__bottom-indicator">
        <FIcon
          class="app-shell__bottom-icon"
          :name="(isActive(item.path) && item.iconSelected) || item.icon"
        />
      </span>
      <span class="app-shell__bottom-label">{{ item.label }}</span>
    </RouterLink>
  </nav>

  <MoreSheet :open="moreOpen" @update:open="(value) => emit('update:moreOpen', value)" />
</template>
