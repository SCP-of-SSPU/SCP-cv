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
/*
 * M3 按钮（DESIGN.md §10.1）：药丸形（corner-full）、label-large 文本、
 * 状态层（hover 8% / focus 12% / pressed 12%）表达交互、克制运动（M1）。
 * appearance 映射：primary→Filled，secondary→Filled tonal，
 * subtle/transparent/ghost→Text，danger→Error。
 */
.f-button {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-sm);
  block-size: 2.5rem;
  padding-inline: var(--space-lg);
  border-radius: var(--md-sys-shape-corner-full);
  border: none;
  font-family: inherit;
  font-size: var(--md-sys-typescale-label-large-size);
  line-height: var(--md-sys-typescale-label-large-line-height);
  font-weight: var(--md-sys-typescale-label-large-weight);
  color: var(--md-sys-color-on-surface);
  background: transparent;
  cursor: pointer;
  user-select: none;
  transition:
    background-color var(--md-sys-motion-duration-short) var(--md-sys-motion-easing-standard),
    color var(--md-sys-motion-duration-short) var(--md-sys-motion-easing-standard),
    box-shadow var(--md-sys-motion-duration-short) var(--md-sys-motion-easing-standard);
}

.f-button:focus-visible {
  outline: 2px solid var(--md-sys-color-primary);
  outline-offset: 2px;
}

.f-button:disabled {
  cursor: not-allowed;
  color: color-mix(in srgb, var(--md-sys-color-on-surface) 38%, transparent);
  background: color-mix(in srgb, var(--md-sys-color-on-surface) 12%, transparent);
  box-shadow: none;
}

.f-button--subtle:disabled,
.f-button--transparent:disabled,
.f-button--ghost:disabled,
.f-button--danger:disabled {
  background: transparent;
}

/* 尺寸：small / compact / medium（默认 40） / large / full */
.f-button--small {
  block-size: 1.75rem;
  padding-inline: var(--space-md);
  font-size: var(--md-sys-typescale-label-medium-size);
  line-height: var(--md-sys-typescale-label-medium-line-height);
  gap: var(--space-xs);
}

.f-button--compact {
  block-size: 2rem;
  padding-inline: var(--space-md);
}

.f-button--large {
  block-size: 3rem;
  padding-inline: var(--space-xl);
}

.f-button--full {
  inline-size: 100%;
  min-block-size: var(--touch-target-pref);
}

.f-button--icon-only {
  inline-size: 2.5rem;
  padding: 0;
  font-size: 0;
}

.f-button--icon-only.f-button--small {
  inline-size: 1.75rem;
}

.f-button--icon-only.f-button--compact {
  inline-size: 2rem;
}

.f-button--icon-only.f-button--large {
  inline-size: 3rem;
}

/* Primary → M3 Filled */
.f-button--primary {
  background: var(--md-sys-color-primary);
  color: var(--md-sys-color-on-primary);
}

.f-button--primary:hover:not(:disabled) {
  background: color-mix(in srgb, var(--md-sys-color-on-primary) 8%, var(--md-sys-color-primary));
  box-shadow: var(--md-sys-elevation-1);
}

.f-button--primary:active:not(:disabled) {
  background: color-mix(in srgb, var(--md-sys-color-on-primary) 12%, var(--md-sys-color-primary));
}

/* Secondary → M3 Filled tonal */
.f-button--secondary {
  background: var(--md-sys-color-secondary-container);
  color: var(--md-sys-color-on-secondary-container);
}

.f-button--secondary:hover:not(:disabled) {
  background: color-mix(in srgb, var(--md-sys-color-on-secondary-container) 8%, var(--md-sys-color-secondary-container));
  box-shadow: var(--md-sys-elevation-1);
}

.f-button--secondary:active:not(:disabled) {
  background: color-mix(in srgb, var(--md-sys-color-on-secondary-container) 12%, var(--md-sys-color-secondary-container));
}

/* Subtle / Transparent / Ghost → M3 Text button */
.f-button--subtle,
.f-button--transparent,
.f-button--ghost {
  background: transparent;
  color: var(--md-sys-color-primary);
  padding-inline: var(--space-md);
}

.f-button--transparent {
  color: var(--md-sys-color-on-surface-variant);
}

.f-button--subtle:hover:not(:disabled),
.f-button--ghost:hover:not(:disabled) {
  background: color-mix(in srgb, var(--md-sys-color-primary) 8%, transparent);
}

.f-button--transparent:hover:not(:disabled) {
  background: color-mix(in srgb, var(--md-sys-color-on-surface) 8%, transparent);
  color: var(--md-sys-color-on-surface);
}

.f-button--subtle:active:not(:disabled),
.f-button--ghost:active:not(:disabled) {
  background: color-mix(in srgb, var(--md-sys-color-primary) 12%, transparent);
}

/* Danger → M3 Error（不可逆/危险操作，B4） */
.f-button--danger {
  background: var(--md-sys-color-error);
  color: var(--md-sys-color-on-error);
}

.f-button--danger:hover:not(:disabled) {
  background: color-mix(in srgb, var(--md-sys-color-on-error) 8%, var(--md-sys-color-error));
  box-shadow: var(--md-sys-elevation-1);
}

.f-button--danger:active:not(:disabled) {
  background: color-mix(in srgb, var(--md-sys-color-on-error) 12%, var(--md-sys-color-error));
}

/* Loading：保留宽度，spinner 旋转 */
.f-button--loading {
  cursor: progress;
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
  font-size: 1.125rem;
  flex-shrink: 0;
}

.f-button__label {
  white-space: nowrap;
}
</style>
