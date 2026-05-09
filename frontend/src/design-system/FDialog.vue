<script setup lang="ts">
/**
 * 对话框（Dialog）。
 * DESIGN.md §12.10 + 设计稿 §5.8：
 *   - 焦点：进入 Dialog 内合理位置，关闭后回到触发元素；
 *   - 危险按钮风格由 variant=danger 决定；
 *   - Esc 仅关闭非危险 Dialog（由调用方 cancellable 控制）。
 *
 * 外部使用时建议绑定 v-model:open 和 events，亦可结合 useDialog() 全局 confirm 流。
 */
import { ref, toRef, watch } from 'vue';

import FButton from './FButton.vue';
import FIcon from './FIcon.vue';
import { useFocusTrap } from '@/composables/useFocusTrap';

interface FDialogProps {
  /** 当前是否显示。 */
  open: boolean;
  /** 标题：写明任务/后果。 */
  title: string;
  /** 描述：写清对象、范围、不可逆性。 */
  description?: string;
  /** 主按钮文案。 */
  confirmLabel?: string;
  /** 次按钮文案。 */
  cancelLabel?: string;
  /** danger 用于不可逆操作。 */
  variant?: 'default' | 'danger';
  /** 是否允许 Esc / 遮罩点击关闭；危险确认默认 false。 */
  cancellable?: boolean;
  /** 主按钮处于 loading 时禁用并显示 spinner。 */
  loading?: boolean;
}

const props = withDefaults(defineProps<FDialogProps>(), {
  description: undefined,
  confirmLabel: '确定',
  cancelLabel: '取消',
  variant: 'default',
  cancellable: true,
  loading: false,
});

const emit = defineEmits<{
  (event: 'update:open', value: boolean): void;
  (event: 'confirm'): void;
  (event: 'cancel'): void;
}>();

const dialogRef = ref<HTMLElement | null>(null);
const isOpen = toRef(props, 'open');

useFocusTrap({
  container: dialogRef,
  active: isOpen,
});

watch(
  () => props.open,
  (open) => {
    if (open) {
      // 打开时锁定 body 滚动，避免后景跟随滚动。
      document.body.style.overflow = 'hidden';
      // 注册 Esc 监听
      window.addEventListener('keydown', handleKey);
    } else {
      document.body.style.overflow = '';
      window.removeEventListener('keydown', handleKey);
    }
  },
  { immediate: true },
);

function handleKey(event: KeyboardEvent): void {
  if (event.key === 'Escape' && props.cancellable) {
    event.preventDefault();
    onCancel();
  }
}

function onConfirm(): void {
  if (props.loading) return;
  emit('confirm');
}

function onCancel(): void {
  emit('cancel');
  emit('update:open', false);
}

function onOverlayClick(event: MouseEvent): void {
  // 仅在点击遮罩本身、且允许取消时关闭。
  if (event.target !== event.currentTarget || !props.cancellable) return;
  onCancel();
}
</script>

<template>
  <Teleport to="body">
    <Transition name="f-dialog">
      <div v-if="open" class="f-dialog__overlay" role="presentation" @mousedown="onOverlayClick">
        <div ref="dialogRef" class="f-dialog" role="dialog" aria-modal="true" :aria-labelledby="$.uid + '-title'"
          :aria-describedby="description ? $.uid + '-desc' : undefined">
          <header class="f-dialog__header">
            <h2 :id="$.uid + '-title'" class="f-dialog__title">{{ title }}</h2>
            <button v-if="cancellable" type="button" class="f-dialog__close" aria-label="关闭对话框" @click="onCancel">
              <FIcon name="dismiss_24_regular" />
            </button>
          </header>
          <div v-if="description || $slots.default" class="f-dialog__body">
            <p v-if="description" :id="$.uid + '-desc'" class="f-dialog__description">{{ description }}</p>
            <slot />
          </div>
          <footer class="f-dialog__footer">
            <slot name="actions" :confirm="onConfirm" :cancel="onCancel">
              <FButton appearance="secondary" @click="onCancel">{{ cancelLabel }}</FButton>
              <FButton :appearance="variant === 'danger' ? 'danger' : 'primary'" :loading="loading" @click="onConfirm">
                {{ confirmLabel }}
              </FButton>
            </slot>
          </footer>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.f-dialog__overlay {
  position: fixed;
  inset: 0;
  background: var(--color-background-overlay);
  z-index: var(--z-dialog);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-2xl);
  -webkit-backdrop-filter: blur(2px);
  backdrop-filter: blur(2px);
}

.f-dialog {
  position: relative;
  width: min(480px, 100%);
  max-height: calc(100% - var(--spacing-4xl));
  background: var(--color-background-card);
  color: var(--color-text-primary);
  border-radius: var(--radius-large);
  box-shadow: var(--shadow-modal);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.f-dialog__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--spacing-m);
  padding: var(--spacing-2xl) var(--spacing-2xl) 0;
}

.f-dialog__title {
  margin: 0;
  font-size: var(--type-title3-size);
  line-height: var(--type-title3-line);
  font-weight: 600;
}

.f-dialog__close {
  border: none;
  background: transparent;
  cursor: pointer;
  color: var(--color-text-secondary);
  padding: var(--spacing-xs);
  border-radius: var(--radius-medium);
  transition: background var(--motion-duration-fast) var(--motion-curve-ease);
}

.f-dialog__close:hover {
  background: var(--color-background-subtle);
  color: var(--color-text-primary);
}

.f-dialog__body {
  padding: var(--spacing-m) var(--spacing-2xl);
  overflow: auto;
}

.f-dialog__description {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: var(--type-body1-size);
  line-height: var(--type-body1-line);
}

.f-dialog__footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-s);
  padding: var(--spacing-l) var(--spacing-2xl) var(--spacing-2xl);
  border-top: 1px solid var(--color-border-subtle);
  background: color-mix(in srgb, var(--color-background-subtle) 86%, var(--color-background-card));
}

/*
 * 进入 / 退出节奏：
 *  - 遮罩淡入 160ms；
 *  - 对话框本体 translateY(16) + scale(0.96) 走 decelerate 曲线，进入更有"重量感"；
 *  - 离场用 accelerate 收尾，视觉上"弹开"。
 */
.f-dialog-enter-active,
.f-dialog-leave-active {
  transition: opacity var(--motion-duration-medium) var(--motion-curve-ease);
}

.f-dialog-enter-active .f-dialog {
  transition: transform var(--motion-duration-entrance) var(--motion-curve-emphasized);
}

.f-dialog-leave-active .f-dialog {
  transition: transform var(--motion-duration-fast) var(--motion-curve-accelerate);
}

.f-dialog-enter-from,
.f-dialog-leave-to {
  opacity: 0;
}

.f-dialog-enter-from .f-dialog,
.f-dialog-leave-to .f-dialog {
  transform: translateY(16px) scale(0.96);
}

@media (max-width: 767px) {
  .f-dialog__overlay {
    padding: 0;
    align-items: flex-end;
  }

  .f-dialog {
    width: 100%;
    max-width: 100%;
    border-radius: var(--radius-large) var(--radius-large) 0 0;
    max-height: 88vh;
  }

  .f-dialog__footer {
    padding-bottom: calc(var(--spacing-2xl) + env(safe-area-inset-bottom));
  }

  .f-dialog__footer :deep(.f-button) {
    flex: 1 1 0;
    min-height: var(--touch-target-pref);
  }
}
</style>
