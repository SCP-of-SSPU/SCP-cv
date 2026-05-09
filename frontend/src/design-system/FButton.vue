<script setup lang="ts">
/**
 * Fluent 2 风格按钮。
 * 状态：rest / hover / pressed / focused / disabled / loading。
 * 类型：primary / secondary / subtle / transparent / danger / ghost。
 * Icon-only 时 props.iconOnly = true 必须配合 ariaLabel；不会强制要求文本。
 *
 * 内置 loading 占位：保留按钮宽度避免抖动；禁用重复点击。
 */
import { computed, useSlots } from 'vue';

import FIcon from './FIcon.vue';
import { cls } from './utils';
import type { FluentIconName } from './icons';
import type { ButtonAppearance, ButtonSize } from './types';

interface FButtonProps {
  /** 视觉强调级别。 */
  appearance?: ButtonAppearance;
  /** 尺寸；移动端布局可配合 fullWidth 撑满父容器。 */
  size?: ButtonSize;
  /** HTML type，默认 button 防止误提交表单。 */
  type?: 'button' | 'submit' | 'reset';
  /** 是否禁用。 */
  disabled?: boolean;
  /** Loading：禁用并叠加 spinner。 */
  loading?: boolean;
  /** 仅图标按钮，必须带 ariaLabel。 */
  iconOnly?: boolean;
  /** 撑满父容器宽度（移动端常用）。 */
  fullWidth?: boolean;
  /** 头部图标。 */
  iconStart?: FluentIconName | string;
  /** 尾部图标，用于「下拉箭头」「跳转」等语义。 */
  iconEnd?: FluentIconName | string;
  /** 屏幕阅读器名称：iconOnly 时必填。 */
  ariaLabel?: string;
}

const props = withDefaults(defineProps<FButtonProps>(), {
  appearance: 'secondary',
  size: 'medium',
  type: 'button',
  disabled: false,
  loading: false,
  iconOnly: false,
  fullWidth: false,
  iconStart: undefined,
  iconEnd: undefined,
  ariaLabel: undefined,
});

const slots = useSlots();
// 可访问性兜底：iconOnly 必须有可访问名称。
const computedAriaLabel = computed(() => props.ariaLabel ?? undefined);

const isDisabled = computed(() => props.disabled || props.loading);

const rootClass = computed(() =>
  cls(
    'f-button',
    `f-button--${props.appearance}`,
    `f-button--${props.size}`,
    props.iconOnly && 'f-button--icon-only',
    props.fullWidth && 'f-button--full',
    props.loading && 'f-button--loading',
  ),
);

defineEmits<(event: 'click', payload: MouseEvent) => void>();
</script>

<template>
  <button :class="rootClass" :type="type" :disabled="isDisabled" :aria-label="computedAriaLabel"
    :aria-busy="loading || undefined" @click="(event) => $emit('click', event)">
    <span v-if="loading" class="f-button__spinner" aria-hidden="true">
      <FIcon name="spinner_ios_20_regular" />
    </span>
    <FIcon v-if="iconStart && !loading" class="f-button__icon f-button__icon--start" :name="iconStart" />
    <span v-if="!iconOnly && slots.default" class="f-button__label">
      <slot />
    </span>
    <FIcon v-if="iconEnd && !loading" class="f-button__icon f-button__icon--end" :name="iconEnd" />
    <span v-if="iconOnly && !iconStart && !loading" class="f-button__label">
      <slot />
    </span>
  </button>
</template>

<style scoped>
.f-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-s);
  height: 32px;
  padding: 0 var(--spacing-l);
  border-radius: var(--radius-medium);
  border: 1px solid transparent;
  font-family: inherit;
  font-size: var(--type-body1-size);
  line-height: 1;
  font-weight: 600;
  color: var(--color-text-primary);
  background: transparent;
  cursor: pointer;
  user-select: none;
  box-shadow: var(--shadow-control);
  /*
   * 过渡时间统一到 medium(160ms)：比原 fast(100ms) 略柔，
   * 避免 hover 闪现过于"机械"；同时把 transform 加入过渡目标，
   * 配合 :active 轻按压反馈生效。
   */
  transition:
    background-color var(--motion-duration-medium) var(--motion-curve-ease),
    color var(--motion-duration-medium) var(--motion-curve-ease),
    border-color var(--motion-duration-medium) var(--motion-curve-ease),
    box-shadow var(--motion-duration-medium) var(--motion-curve-ease),
    transform var(--motion-duration-fast) var(--motion-curve-ease);
}

/* 按下瞬间轻微下沉 + 微缩，增强点击手感。 */
.f-button:active:not(:disabled):not(.f-button--loading) {
  transform: translateY(1px) scale(0.99);
}

/* 键盘聚焦时显示 2 px 品牌色外环，鼠标点击不触发（:focus-visible 规范）。 */
.f-button:focus-visible {
  outline: 2px solid var(--color-border-focus);
  outline-offset: 2px;
}

.f-button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
  box-shadow: none;
  transform: none;
}

/* 尺寸：紧凑 / 默认 / 大 / 移动端 100% 宽 */
.f-button--compact {
  height: 28px;
  padding: 0 var(--spacing-m);
}

.f-button--large {
  height: 40px;
  padding: 0 var(--spacing-xl);
}

.f-button--full {
  width: 100%;
  min-height: var(--touch-target-pref);
  padding: 0 var(--spacing-l);
}

.f-button--icon-only {
  width: 32px;
  padding: 0;
  font-size: 0;
}

.f-button--icon-only.f-button--compact {
  width: 28px;
}

.f-button--icon-only.f-button--large {
  width: 40px;
}

/* Primary：品牌实心，主操作 */
.f-button--primary {
  background: var(--color-background-brand);
  color: var(--color-text-inverse);
  border-color: var(--color-background-brand);
  box-shadow: var(--shadow-brand);
}

.f-button--primary:hover:not(:disabled) {
  background: var(--color-background-brand-hover);
  border-color: var(--color-background-brand-hover);
  box-shadow: var(--shadow-brand-hover);
  transform: translateY(-1px);
}

.f-button--primary:active:not(:disabled) {
  background: var(--color-background-brand-pressed);
  border-color: var(--color-background-brand-pressed);
  box-shadow: var(--shadow-brand);
}

/* Secondary：透明底 + 边框 */
.f-button--secondary {
  background: var(--color-background-card);
  color: var(--color-text-primary);
  border-color: var(--color-border-default);
}

.f-button--secondary:hover:not(:disabled) {
  background: var(--color-background-subtle);
  border-color: var(--color-border-strong);
  box-shadow: var(--shadow-4);
  transform: translateY(-1px);
}

.f-button--secondary:active:not(:disabled) {
  background: var(--color-background-disabled);
}

/* Subtle：透明底 + 品牌文字，工具栏低强调 */
.f-button--subtle {
  background: transparent;
  color: var(--color-text-brand);
  border-color: transparent;
  box-shadow: none;
}

.f-button--subtle:hover:not(:disabled) {
  background: var(--color-background-brand-selected);
}

/* Transparent：极低强调，仅作 icon-only 工具按钮 */
.f-button--transparent {
  background: transparent;
  color: var(--color-text-secondary);
  border-color: transparent;
  box-shadow: none;
}

.f-button--transparent:hover:not(:disabled) {
  background: var(--color-background-subtle);
  color: var(--color-text-primary);
}

/* Ghost：与 transparent 类似，但 hover 用品牌选中底色 */
.f-button--ghost {
  background: transparent;
  color: var(--color-text-primary);
  border-color: transparent;
  box-shadow: none;
}

.f-button--ghost:hover:not(:disabled) {
  background: var(--color-background-brand-selected);
  color: var(--color-text-brand);
}

/* Danger：红色轮廓 + 红字，仅用于不可逆/危险操作 */
.f-button--danger {
  background: transparent;
  color: var(--color-status-error-foreground);
  border-color: var(--color-status-error-foreground);
  box-shadow: none;
}

.f-button--danger:hover:not(:disabled) {
  background: var(--color-status-error-background);
  box-shadow: var(--shadow-4);
  transform: translateY(-1px);
}

.f-button--danger:active:not(:disabled) {
  background: var(--color-status-error-background);
  border-color: var(--color-status-error-foreground);
}

/* Loading：保留宽度，spinner 旋转 */
.f-button--loading {
  cursor: progress;
  transform: none;
}

@media (hover: none) {
  .f-button--primary:hover:not(:disabled),
  .f-button--secondary:hover:not(:disabled),
  .f-button--danger:hover:not(:disabled) {
    transform: none;
  }
}

.f-button__spinner {
  display: inline-flex;
  width: 18px;
  height: 18px;
  animation: f-button-spin 600ms linear infinite;
}

@keyframes f-button-spin {
  to {
    transform: rotate(360deg);
  }
}

.f-button__icon {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
}

.f-button__label {
  white-space: nowrap;
}
</style>
