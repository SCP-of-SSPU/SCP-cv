<script setup lang="ts">
/**
 * 主题切换按钮（DESIGN.md §4.3 + §13）。
 * 单个原生 <button>，循环 system → light → dark；
 * aria-label 始终描述「下一步动作」，图标与状态成对（非仅颜色，R8）。
 * ≥ 48×48 命中区域、可见焦点环（R7 / A24）。
 */
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';

import { FIcon } from '@/design-system';
import { useTheme, type ThemeMode } from '@/composables/useTheme';

const { t } = useI18n();
const { mode } = useTheme();

const NEXT: Record<ThemeMode, ThemeMode> = {
  system: 'light',
  light: 'dark',
  dark: 'system',
};

const ICON: Record<ThemeMode, string> = {
  system: 'dark_theme_24_regular',
  light: 'weather_sunny_24_regular',
  dark: 'weather_moon_24_regular',
};

const LABEL: Record<ThemeMode, string> = {
  system: 'theme.system',
  light: 'theme.light',
  dark: 'theme.dark',
};

const icon = computed(() => ICON[mode.value]);
const ariaLabel = computed(() =>
  t('theme.toggleAria', {
    current: t(LABEL[mode.value]),
    next: t(LABEL[NEXT[mode.value]]),
  }),
);

function cycle(): void {
  mode.value = NEXT[mode.value];
}
</script>

<template>
  <button type="button" class="theme-toggle" :aria-label="ariaLabel" @click="cycle">
    <FIcon class="theme-toggle__icon" :name="icon" />
  </button>
</template>

<style scoped>
.theme-toggle {
  inline-size: 3rem;
  block-size: 3rem;
  display: inline-grid;
  place-items: center;
  border: none;
  border-radius: var(--borderRadiusCircular);
  background: transparent;
  color: var(--colorNeutralForeground2);
  cursor: pointer;
  transition: background var(--durationFast)
    var(--curveEasyEase);
}

.theme-toggle:hover {
  background: color-mix(in srgb, var(--colorNeutralForeground1) 8%, transparent);
}

.theme-toggle:focus-visible {
  outline: 2px solid var(--colorBrandBackground);
  outline-offset: 2px;
}

.theme-toggle__icon {
  font-size: 1.5rem;
}
</style>
