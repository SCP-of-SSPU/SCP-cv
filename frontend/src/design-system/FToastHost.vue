<script setup lang="ts">
/**
 * 全局 Toast 宿主：在 layout 顶层挂一次即可。
 * 移动端 sm/xs 自动改顶部居中（避开底部 TabBar），并使用 safe-area-inset-top 兜底。
 */
import { computed } from 'vue';

import FButton from './FButton.vue';
import FIcon from './FIcon.vue';
import { useBreakpoint } from '@/composables/useBreakpoint';
import { useToastStore } from '@/composables/useToast';
import type { ToastLevel } from '@/composables/useToast';
import type { FluentIconName } from './icons';

const toastStore = useToastStore();
const { isMobile } = useBreakpoint();

const items = computed(() => toastStore.items);

const placementClass = computed(() => (isMobile.value ? 'f-toast-host--top' : 'f-toast-host--bottom-right'));

function levelIcon(level: ToastLevel): FluentIconName {
  switch (level) {
    case 'success':
      return 'checkmark_circle_24_filled';
    case 'warning':
      return 'warning_24_filled';
    case 'error':
      return 'error_circle_24_filled';
    default:
      return 'info_24_regular';
  }
}

async function triggerAction(id: number, action?: { onTrigger: () => void | Promise<void> }): Promise<void> {
  if (!action) return;
  try {
    await action.onTrigger();
  } finally {
    toastStore.dismiss(id);
  }
}
</script>

<template>
  <Teleport to="body">
    <div :class="['f-toast-host', placementClass]" aria-live="polite" aria-atomic="true">
      <TransitionGroup name="f-toast" tag="div" class="f-toast-host__list">
        <article v-for="item in items" :key="item.id" class="f-toast" :class="`f-toast--${item.level}`" role="status">
          <FIcon class="f-toast__icon" :name="levelIcon(item.level)" />
          <div class="f-toast__body">
            <p class="f-toast__message">{{ item.message }}</p>
            <p v-if="item.description" class="f-toast__description">{{ item.description }}</p>
          </div>
          <div class="f-toast__actions">
            <FButton v-if="item.action" appearance="subtle" size="compact" @click="triggerAction(item.id, item.action)">
              {{ item.action.label }}
            </FButton>
            <FButton appearance="transparent" size="compact" icon-only :icon-start="'dismiss_20_regular'"
              aria-label="关闭通知" @click="toastStore.dismiss(item.id)" />
          </div>
        </article>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<style scoped>
.f-toast-host {
  position: fixed;
  z-index: var(--z-toast);
  pointer-events: none;
  display: flex;
  flex-direction: column;
}

.f-toast-host--bottom-right {
  right: var(--spacing-2xl);
  bottom: var(--spacing-2xl);
  align-items: flex-end;
}

.f-toast-host--top {
  top: calc(env(safe-area-inset-top, 0px) + var(--spacing-s));
  left: var(--spacing-l);
  right: var(--spacing-l);
  align-items: stretch;
}

.f-toast-host__list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-s);
}

.f-toast {
  pointer-events: auto;
  display: flex;
  align-items: flex-start;
  gap: var(--spacing-m);
  width: min(360px, 100%);
  padding: var(--spacing-m) var(--spacing-l);
  background: var(--color-background-card);
  color: var(--color-text-primary);
  border-radius: var(--radius-large);
  border: 1px solid var(--color-border-subtle);
  box-shadow: var(--shadow-16);
}

.f-toast-host--top .f-toast {
  width: 100%;
}

.f-toast__icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
  margin-top: 2px;
}

.f-toast--success .f-toast__icon {
  color: var(--color-status-success-foreground);
}

.f-toast--warning .f-toast__icon {
  color: var(--color-status-warning-foreground);
}

.f-toast--error .f-toast__icon {
  color: var(--color-status-error-foreground);
}

.f-toast--info .f-toast__icon {
  color: var(--color-status-info-foreground);
}

.f-toast__body {
  flex: 1 1 auto;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xxs);
  min-width: 0;
}

.f-toast__message {
  margin: 0;
  font-weight: 600;
}

.f-toast__description {
  margin: 0;
  font-size: var(--type-caption1-size);
  line-height: var(--type-caption1-line);
  color: var(--color-text-secondary);
}

.f-toast__actions {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-xs);
  flex-shrink: 0;
}

/*
 * Toast 进入用 spring 曲线（≤5% 过冲），让通知"轻轻弹"；离场用 accelerate 淡出，
 * 避免长时间停留遮挡操作。位移幅度也加大到 12 px 让"出现感"更明确。
 */
.f-toast-enter-active {
  transition: opacity var(--motion-duration-normal) var(--motion-curve-ease),
    transform var(--motion-duration-normal) var(--motion-curve-spring);
}

.f-toast-leave-active {
  transition: opacity var(--motion-duration-fast) var(--motion-curve-ease),
    transform var(--motion-duration-fast) var(--motion-curve-accelerate);
}

.f-toast-enter-from {
  opacity: 0;
  transform: translateY(12px);
}

.f-toast-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}

.f-toast-host--top .f-toast-enter-from {
  transform: translateY(-8px);
}

.f-toast-host--top .f-toast-leave-to {
  transform: translateY(-12px);
}
</style>
