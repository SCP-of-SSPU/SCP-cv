<script setup lang="ts">
/**
 * Drawer / Sheet 双形态：
 *   - 桌面（≥ md）右侧滑入，宽度可配置；
 *   - 移动端（xs / sm）自动改为底部上拉 Sheet，全屏或半屏可调。
 *
 * DESIGN.md §12.11 + 设计稿 §5.9：
 *   - Drawer 内长表单需有底部固定操作栏；
 *   - Sheet 顶部带拖动手柄；
 *   - 不在 Drawer 内打开复杂二级 Drawer。
 */
import { computed, ref, toRef, watch } from 'vue';

import FButton from './FButton.vue';
import FIcon from './FIcon.vue';
import { useFocusTrap } from '@/composables/useFocusTrap';
import { useBreakpoint } from '@/composables/useBreakpoint';

interface FDrawerProps {
  open: boolean;
  /** 标题，必填，写明任务。 */
  title: string;
  /** 副标题/说明，可选。 */
  description?: string;
  /** 桌面端宽度；移动端自动忽略。 */
  width?: number | string;
  /** 移动端 Sheet 的高度策略；默认 auto = 内容高度，full = 占满 88vh。 */
  mobileHeight?: 'auto' | 'full';
  /** 是否允许 Esc / 遮罩点击关闭。 */
  cancellable?: boolean;
  /** 当为 true 时，不渲染默认的「取消 / 确定」操作栏（外部自己用 actions 插槽接管）。 */
  hideDefaultActions?: boolean;
  /** 主操作文案。 */
  primaryLabel?: string;
  /** 次操作文案。 */
  secondaryLabel?: string;
  /** 主操作 loading。 */
  loading?: boolean;
  /** 主操作风格。 */
  primaryVariant?: 'primary' | 'danger';
}

const props = withDefaults(defineProps<FDrawerProps>(), {
  description: undefined,
  width: 480,
  mobileHeight: 'full',
  cancellable: true,
  hideDefaultActions: false,
  primaryLabel: '保存',
  secondaryLabel: '取消',
  loading: false,
  primaryVariant: 'primary',
});

const emit = defineEmits<{
  (event: 'update:open', value: boolean): void;
  (event: 'confirm'): void;
  (event: 'cancel'): void;
}>();

const drawerRef = ref<HTMLElement | null>(null);
const isOpen = toRef(props, 'open');
const { isMobile } = useBreakpoint();

useFocusTrap({
  container: drawerRef,
  active: isOpen,
});

const inlineWidth = computed(() => {
  if (typeof props.width === 'number') return `${props.width}px`;
  return props.width;
});

watch(
  () => props.open,
  (open) => {
    if (open) {
      document.body.style.overflow = 'hidden';
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
  if (event.target !== event.currentTarget || !props.cancellable) return;
  onCancel();
}
</script>

<template>
  <Teleport to="body">
    <Transition :name="isMobile ? 'f-sheet' : 'f-drawer'">
      <div
        v-if="open"
        class="f-drawer__overlay"
        :class="{ 'f-drawer__overlay--mobile': isMobile }"
        role="presentation"
        @mousedown="onOverlayClick"
      >
        <aside
          ref="drawerRef"
          class="f-drawer"
          :class="[isMobile && 'f-drawer--mobile', `f-drawer--mh-${mobileHeight}`]"
          role="dialog"
          aria-modal="true"
          :aria-labelledby="$.uid + '-title'"
          :style="!isMobile ? { width: inlineWidth, maxWidth: inlineWidth } : undefined"
        >
          <span v-if="isMobile" class="f-drawer__handle" aria-hidden="true" />
          <header class="f-drawer__header">
            <div class="f-drawer__heading">
              <h2 :id="$.uid + '-title'" class="f-drawer__title">{{ title }}</h2>
              <p v-if="description" class="f-drawer__description">{{ description }}</p>
            </div>
            <button
              v-if="cancellable"
              type="button"
              class="f-drawer__close"
              aria-label="关闭"
              @click="onCancel"
            >
              <FIcon name="dismiss_24_regular" />
            </button>
          </header>
          <div class="f-drawer__body">
            <slot />
          </div>
          <footer class="f-drawer__footer">
            <slot name="actions" :confirm="onConfirm" :cancel="onCancel">
              <template v-if="!hideDefaultActions">
                <FButton appearance="secondary" :full-width="isMobile" @click="onCancel">
                  {{ secondaryLabel }}
                </FButton>
                <FButton
                  :appearance="primaryVariant"
                  :loading="loading"
                  :full-width="isMobile"
                  @click="onConfirm"
                >
                  {{ primaryLabel }}
                </FButton>
              </template>
            </slot>
          </footer>
        </aside>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.f-drawer__overlay {
  position: fixed;
  inset: 0;
  background: var(--color-background-overlay);
  z-index: var(--z-drawer);
  display: flex;
  align-items: stretch;
  justify-content: flex-end;
}

.f-drawer__overlay--mobile {
  align-items: flex-end;
  justify-content: stretch;
}

.f-drawer {
  position: relative;
  background: var(--color-background-card);
  color: var(--color-text-primary);
  display: flex;
  flex-direction: column;
  box-shadow: var(--shadow-16);
  height: 100%;
  max-height: 100%;
}

.f-drawer--mobile {
  width: 100%;
  height: auto;
  max-height: 88vh;
  border-radius: var(--radius-xlarge) var(--radius-xlarge) 0 0;
  padding-bottom: env(safe-area-inset-bottom);
}

.f-drawer--mobile.f-drawer--mh-full {
  height: 88vh;
}

.f-drawer--mobile.f-drawer--mh-auto {
  height: auto;
  min-height: 50vh;
}

.f-drawer__handle {
  width: 36px;
  height: 4px;
  background: var(--color-border-default);
  border-radius: var(--radius-circular);
  margin: var(--spacing-s) auto 0;
}

.f-drawer__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--spacing-m);
  padding: var(--spacing-2xl) var(--spacing-2xl) var(--spacing-l);
  border-bottom: 1px solid var(--color-border-subtle);
}

.f-drawer__heading {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
  min-width: 0;
}

.f-drawer__title {
  margin: 0;
  font-size: var(--type-title3-size);
  line-height: var(--type-title3-line);
  font-weight: 600;
}

.f-drawer__description {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: var(--type-caption1-size);
  line-height: var(--type-caption1-line);
}

.f-drawer__close {
  border: none;
  background: transparent;
  cursor: pointer;
  color: var(--color-text-secondary);
  padding: var(--spacing-xs);
  border-radius: var(--radius-medium);
  transition: background var(--motion-duration-fast) var(--motion-curve-ease);
  flex-shrink: 0;
}

.f-drawer__close:hover {
  background: var(--color-background-subtle);
  color: var(--color-text-primary);
}

.f-drawer__body {
  flex: 1 1 auto;
  overflow: auto;
  padding: var(--spacing-l) var(--spacing-2xl);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-l);
}

.f-drawer__footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-s);
  padding: var(--spacing-l) var(--spacing-2xl) var(--spacing-2xl);
  border-top: 1px solid var(--color-border-subtle);
  background: var(--color-background-subtle);
}

.f-drawer--mobile .f-drawer__footer {
  flex-direction: column-reverse;
  padding-bottom: calc(var(--spacing-2xl) + env(safe-area-inset-bottom));
}

.f-drawer-enter-active,
.f-drawer-leave-active,
.f-sheet-enter-active,
.f-sheet-leave-active {
  transition: opacity var(--motion-duration-fast) var(--motion-curve-ease);
}

.f-drawer-enter-active .f-drawer,
.f-drawer-leave-active .f-drawer {
  transition: transform var(--motion-duration-normal) var(--motion-curve-decelerate);
}

.f-sheet-enter-active .f-drawer,
.f-sheet-leave-active .f-drawer {
  transition: transform var(--motion-duration-slow) var(--motion-curve-decelerate);
}

.f-drawer-enter-from,
.f-drawer-leave-to,
.f-sheet-enter-from,
.f-sheet-leave-to {
  opacity: 0;
}

.f-drawer-enter-from .f-drawer,
.f-drawer-leave-to .f-drawer {
  transform: translateX(16px);
}

.f-sheet-enter-from .f-drawer,
.f-sheet-leave-to .f-drawer {
  transform: translateY(16px);
}
</style>
