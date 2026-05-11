<script setup lang="ts">
/**
 * 移动端 Shell：顶部精简栏 + 底部固定 TabBar + 「更多」Sheet。
 * 设计稿 §7.2：5 项底部 Tab，最右一项「更多」展开 Sheet。
 */
import { computed, ref } from 'vue';
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router';

import EmergencyMenu from './EmergencyMenu.vue';
import MoreSheet from './MoreSheet.vue';
import { MOBILE_TAB_BAR } from './navItems';
import { FIcon, FTag } from '@/design-system';
import { useRuntimeStore } from '@/stores/runtime';

const runtime = useRuntimeStore();
const route = useRoute();
const router = useRouter();

const moreOpen = ref(false);

const titleHint = computed(() => {
  const sse = runtime.sseStatus === 'connected' ? '实时已连接'
    : runtime.sseStatus === 'reconnecting' ? '断开重连中'
      : runtime.sseStatus === 'connecting' ? '建立连接…'
        : '连接已关闭';
  return `${runtime.bigScreenLabel} · ${sse}`;
});

function isPathActive(path: string): boolean {
  if (path === '/dashboard' && route.path === '/') return true;
  if (path === '/display/big-left' && route.path.startsWith('/display/')) return true;
  return route.path === path;
}

function onTabClick(path: string, event: MouseEvent): void {
  if (path === '/more') {
    event.preventDefault();
    moreOpen.value = true;
    return;
  }
  void router.push(path);
}
</script>

<template>
  <div class="mobile-shell">
    <header class="mobile-shell__top-bar" role="banner">
      <RouterLink to="/dashboard" class="mobile-shell__brand">
        <span class="mobile-shell__brand-mark" aria-hidden="true">S</span>
        <span class="mobile-shell__brand-title">SCP-cv</span>
      </RouterLink>
      <div class="mobile-shell__top-meta">
        <FTag
          :tone="runtime.sseStatus === 'connected' ? 'success' : runtime.sseStatus === 'reconnecting' ? 'warning' : 'subtle'">
          {{ runtime.bigScreenLabel }}
        </FTag>
        <EmergencyMenu />
      </div>
    </header>
    <p class="mobile-shell__top-caption">{{ titleHint }}</p>

    <main class="mobile-shell__content">
      <RouterView />
    </main>

    <nav class="mobile-shell__tab-bar" :aria-label="'主导航'">
      <RouterLink v-for="item in MOBILE_TAB_BAR" :key="item.path" :to="item.path" class="mobile-shell__tab"
        :class="{ 'mobile-shell__tab--active': isPathActive(item.path) }"
        @click="(event) => onTabClick(item.path, event)">
        <FIcon class="mobile-shell__tab-icon" :name="(isPathActive(item.path) && item.iconSelected) || item.icon" />
        <span class="mobile-shell__tab-label">{{ item.label }}</span>
      </RouterLink>
    </nav>

    <MoreSheet v-model:open="moreOpen" />
  </div>
</template>

<style scoped>
.mobile-shell {
  display: flex;
  flex-direction: column;
  flex: 1 1 auto;
  min-height: var(--app-height, 100vh);
}

.mobile-shell__top-bar {
  position: sticky;
  top: 0;
  z-index: var(--z-sticky);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-l);
  height: 48px;
  padding: 0 var(--spacing-l);
  padding-top: env(safe-area-inset-top, 0px);
  background: var(--color-background-glass-strong);
  border-bottom: 1px solid var(--color-border-subtle);
  box-shadow: var(--shadow-chrome);
  -webkit-backdrop-filter: blur(18px) saturate(1.1);
  backdrop-filter: blur(18px) saturate(1.1);
}

.mobile-shell__brand {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-s);
  text-decoration: none;
  color: inherit;
}

.mobile-shell__brand-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: var(--radius-medium);
  background: var(--gradient-brand-mark);
  color: var(--color-text-inverse);
  font-weight: 700;
  font-size: var(--type-body1-size);
  box-shadow: var(--shadow-brand);
}

.mobile-shell__brand-title {
  font-weight: 600;
}

.mobile-shell__top-meta {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-s);
}

.mobile-shell__top-caption {
  position: sticky;
  top: calc(48px + env(safe-area-inset-top, 0px));
  z-index: calc(var(--z-sticky) - 1);
  margin: 0;
  padding: var(--spacing-xs) var(--spacing-l);
  background: var(--color-background-glass);
  font-size: var(--type-caption1-size);
  color: var(--color-text-tertiary);
  border-bottom: 1px solid var(--color-border-subtle);
  -webkit-backdrop-filter: blur(18px) saturate(1.1);
  backdrop-filter: blur(18px) saturate(1.1);
}

.mobile-shell__content {
  flex: 1 1 auto;
  /* 底部留白覆盖 fixed TabBar 高度（≥ 64 px）+ 设备安全区，避免内容被遮挡。 */
  padding: var(--spacing-l) var(--spacing-l) calc(80px + env(safe-area-inset-bottom));
  min-width: 0;
}

/*
 * 移动端底部 TabBar 改为 fixed：
 *   - 摆脱父级 overflow / sticky 容器约束，避免在 iOS Safari 动态地址栏、虚拟键盘
 *     或 Drawer 锁 body 滚动时底栏被裁掉；
 *   - 永远悬浮在视口底部，配合内容 padding-bottom 保持可点击区域；
 *   - 适配刘海 / Home Bar 安全区，并叠加轻微毛玻璃保持 Fluent acrylic 质感。
 */
.mobile-shell__tab-bar {
  position: fixed;
  inset: auto 0 0 0;
  z-index: var(--z-sticky);
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: var(--spacing-xs);
  padding: var(--spacing-xs) var(--spacing-xs) calc(var(--spacing-xs) + env(safe-area-inset-bottom));
  background: color-mix(in srgb, var(--color-background-card) 92%, transparent);
  border-top: 1px solid var(--color-border-subtle);
  box-shadow: var(--shadow-tabbar);
  -webkit-backdrop-filter: blur(12px);
  backdrop-filter: blur(12px);
}

@supports not (backdrop-filter: blur(12px)) {
  .mobile-shell__tab-bar {
    background: var(--color-background-card);
  }
}

.mobile-shell__tab {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  min-height: 56px;
  padding: var(--spacing-xs);
  text-decoration: none;
  color: var(--color-text-secondary);
  border-radius: var(--radius-medium);
  transition:
    background var(--motion-duration-medium) var(--motion-curve-ease),
    color var(--motion-duration-medium) var(--motion-curve-ease),
    transform var(--motion-duration-medium) var(--motion-curve-ease);
}

.mobile-shell__tab:active {
  transform: scale(var(--motion-press-scale));
  transition-duration: var(--motion-duration-fast);
}

.mobile-shell__tab:focus-visible {
  outline: none;
  box-shadow: var(--shadow-focus);
}

.mobile-shell__tab--active {
  background: var(--color-background-brand-selected);
  color: var(--color-text-brand);
  transform: translateY(-1px);
}

/* 顶部 2 px brand 指示条，与桌面 Nav 选中态语义保持一致。 */
.mobile-shell__tab--active::before {
  content: '';
  position: absolute;
  top: 4px;
  left: 50%;
  width: 18px;
  height: 2px;
  border-radius: var(--radius-circular);
  background: var(--color-background-brand);
  transform: translateX(-50%);
  animation: f-rise var(--motion-duration-entrance) var(--motion-curve-emphasized) both;
}

.mobile-shell__tab-icon {
  width: 22px;
  height: 22px;
}

.mobile-shell__tab-label {
  font-size: var(--type-caption2-size);
  font-weight: 600;
}

@media (max-width: 359px) {
  .mobile-shell__top-caption {
    display: none;
  }
}
</style>
