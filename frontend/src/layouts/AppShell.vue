<script setup lang="ts">
/**
 * 桌面端 Application Shell：TitleBar + NavPane + Page Content。
 * 设计稿 §3.1（已调整）：
 *   - TitleBar 32-56 px 高，承载品牌、SSE 状态、应急；
 *   - NavPane 在所有桌面断点（md / lg / xl / 2xl）始终全展显示文字；
 *     旧的 1024–1280 px Compact 仅图标模式已下线，便于操作员快速识别功能项；
 *   - 内容区 24 px 边距；超宽屏时主内容居中。
 */
import { computed } from 'vue';
import { RouterLink, RouterView, useRoute } from 'vue-router';

import EmergencyMenu from './EmergencyMenu.vue';
import {
  DESKTOP_PRIMARY_NAV,
  DESKTOP_SECONDARY_NAV,
  resolveDisplayLabel,
} from './navItems';
import { useRuntimeStore } from '@/stores/runtime';
import { FIcon, FTag } from '@/design-system';
import type { NavItemDef } from './types';

const runtime = useRuntimeStore();
const route = useRoute();

const visiblePrimary = computed<NavItemDef[]>(() =>
  DESKTOP_PRIMARY_NAV.filter((item) => !(item.doubleScreenOnly && !runtime.isDoubleScreen)).map((item) => ({
    ...item,
    label: item.path.startsWith('/display/')
      ? resolveDisplayLabel(item.path, runtime.isDoubleScreen)
      : item.label,
  })),
);

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
      return '实时已连接';
    case 'connecting':
      return '建立连接…';
    case 'reconnecting':
      return '断开重连中';
    case 'closed':
    default:
      return '连接已关闭';
  }
});

function isPathActive(path: string): boolean {
  if (path === '/dashboard' && route.path === '/') return true;
  return route.path === path;
}
</script>

<template>
  <div class="app-shell">
    <header class="app-shell__title-bar" role="banner">
      <div class="app-shell__brand">
        <span class="app-shell__brand-mark" aria-hidden="true">S</span>
        <div class="app-shell__brand-meta">
          <p class="app-shell__brand-eyebrow">SCP-cv</p>
          <h1 class="app-shell__brand-title">播放控制台</h1>
        </div>
      </div>
      <div class="app-shell__title-meta">
        <FTag :tone="runtime.isDoubleScreen ? 'info' : 'subtle'">
          {{ runtime.bigScreenLabel }}
        </FTag>
        <FTag :tone="sseTone" :dot="runtime.sseStatus === 'reconnecting'">
          {{ sseLabel }}
        </FTag>
        <span v-if="runtime.systemVolume.muted" class="app-shell__title-mute">系统静音</span>
        <EmergencyMenu />
      </div>
    </header>

    <div class="app-shell__body">
      <nav class="app-shell__nav" :aria-label="'主导航'">
        <ul class="app-shell__nav-list">
          <li v-for="item in visiblePrimary" :key="item.path">
            <RouterLink :to="item.path" class="app-shell__nav-item"
              :class="{ 'app-shell__nav-item--active': isPathActive(item.path) }">
              <FIcon class="app-shell__nav-icon" :name="(isPathActive(item.path) && item.iconSelected) || item.icon" />
              <span class="app-shell__nav-label">{{ item.label }}</span>
            </RouterLink>
          </li>
        </ul>
        <div class="app-shell__nav-divider" aria-hidden="true" />
        <ul class="app-shell__nav-list">
          <li v-for="item in DESKTOP_SECONDARY_NAV" :key="item.path">
            <RouterLink :to="item.path" class="app-shell__nav-item"
              :class="{ 'app-shell__nav-item--active': isPathActive(item.path) }">
              <FIcon class="app-shell__nav-icon" :name="(isPathActive(item.path) && item.iconSelected) || item.icon" />
              <span class="app-shell__nav-label">{{ item.label }}</span>
            </RouterLink>
          </li>
        </ul>
      </nav>

      <main class="app-shell__content">
        <RouterView />
      </main>
    </div>
  </div>
</template>

<style scoped>
.app-shell {
  display: flex;
  flex-direction: column;
  flex: 1 1 auto;
  min-height: var(--app-height, 100vh);
}

.app-shell__title-bar {
  position: sticky;
  top: 0;
  z-index: var(--z-sticky);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-l);
  height: 56px;
  padding: 0 var(--spacing-2xl);
  /* glass-strong 在浅色画布上保留可读对比度，避免顶栏内容"浮在画布"。 */
  background: var(--color-background-glass-strong);
  border-bottom: 1px solid var(--color-border-subtle);
  box-shadow: var(--shadow-chrome);
  -webkit-backdrop-filter: blur(18px) saturate(1.1);
  backdrop-filter: blur(18px) saturate(1.1);
}

.app-shell__brand {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-m);
  min-width: 0;
}

.app-shell__brand-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: var(--radius-medium);
  background: var(--gradient-brand-mark);
  color: var(--color-text-inverse);
  font-weight: 700;
  font-size: var(--type-subtitle2-size);
  box-shadow: var(--shadow-brand);
  /* 1 px 内描边模拟 Fluent 2 上沿高光，避免 logo 与背景"贴皮"。 */
  position: relative;
}

.app-shell__brand-mark::after {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  box-shadow: inset 0 1px 0 color-mix(in srgb, var(--color-text-inverse) 30%, transparent);
  pointer-events: none;
}

.app-shell__brand-meta {
  display: flex;
  flex-direction: column;
  line-height: 1;
  min-width: 0;
}

.app-shell__brand-eyebrow {
  margin: 0;
  font-size: var(--type-caption2-size);
  letter-spacing: 0.08em;
  color: var(--color-text-tertiary);
  text-transform: uppercase;
}

.app-shell__brand-title {
  margin: 0;
  font-size: var(--type-subtitle2-size);
  line-height: var(--type-subtitle2-line);
  font-weight: 600;
  color: var(--color-text-primary);
}

.app-shell__title-meta {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-s);
}

.app-shell__title-mute {
  display: inline-flex;
  align-items: center;
  font-size: var(--type-caption1-size);
  font-weight: 600;
  color: var(--color-status-warning-foreground);
  background: var(--color-status-warning-background);
  padding: 2px var(--spacing-s);
  border-radius: var(--radius-circular);
  border: 1px solid color-mix(in srgb, var(--color-status-warning-foreground) 28%, transparent);
}

.app-shell__body {
  display: flex;
  flex: 1 1 auto;
  min-height: 0;
}

.app-shell__nav {
  position: sticky;
  top: 56px;
  align-self: flex-start;
  width: 240px;
  height: calc(var(--app-height, 100vh) - 56px);
  padding: var(--spacing-l) var(--spacing-m);
  /* 侧边栏改为带轻微 elevated 的卡片层，与画布拉开层级。 */
  background: var(--color-background-elevated);
  border-right: 1px solid var(--color-border-subtle);
  box-shadow: var(--shadow-chrome);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-l);
  overflow-y: auto;
}

.app-shell__nav-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.app-shell__nav-divider {
  border-top: 1px solid var(--color-border-subtle);
  margin: var(--spacing-s) 0;
}

.app-shell__nav-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: var(--spacing-m);
  padding: var(--spacing-s) var(--spacing-m);
  border-radius: var(--radius-medium);
  color: var(--color-text-secondary);
  font-weight: 500;
  text-decoration: none;
  transition:
    background var(--motion-duration-medium) var(--motion-curve-ease),
    color var(--motion-duration-medium) var(--motion-curve-ease),
    transform var(--motion-duration-medium) var(--motion-curve-ease),
    box-shadow var(--motion-duration-medium) var(--motion-curve-ease);
}

.app-shell__nav-item:hover {
  background: var(--color-background-subtle);
  color: var(--color-text-primary);
  transform: translateX(2px);
}

.app-shell__nav-item:focus-visible {
  outline: none;
  background: var(--color-background-subtle);
  box-shadow: var(--shadow-focus);
}

.app-shell__nav-item--active {
  background: var(--color-background-brand-selected);
  color: var(--color-text-brand);
  font-weight: 600;
  box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--color-background-brand) 18%, transparent);
}

/*
 * Active 指示条：4 px 圆头条置于 NavItem 左侧（绝对定位）。
 * Fluent 2 推荐做法：始终预留位置但仅 active 时显形，避免列表整体在选中态时左右抖动。
 */
.app-shell__nav-item::before {
  content: '';
  position: absolute;
  left: -4px;
  top: 50%;
  width: 3px;
  height: 0;
  border-radius: var(--radius-circular);
  background: var(--color-background-brand);
  transform: translateY(-50%);
  transition:
    height var(--motion-duration-medium) var(--motion-curve-emphasized),
    opacity var(--motion-duration-medium) var(--motion-curve-ease);
  opacity: 0;
}

.app-shell__nav-item--active::before {
  height: 18px;
  opacity: 1;
}

.app-shell__nav-icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
}

.app-shell__nav-label {
  flex: 1 1 auto;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.app-shell__content {
  flex: 1 1 auto;
  min-width: 0;
  padding: var(--spacing-2xl) var(--spacing-2xl) var(--spacing-4xl);
  overflow-x: hidden;
  background: var(--color-background-canvas);
}

@media (min-width: 1920px) {
  .app-shell__content {
    padding: var(--spacing-3xl) var(--spacing-4xl) var(--spacing-5xl);
  }
}
</style>
