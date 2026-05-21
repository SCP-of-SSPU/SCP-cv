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
 * Fluent 2 按钮（DESIGN.md §6.1）。
 *   形状  borderRadiusMedium = 4px（替代 M3 的药丸）
 *   尺寸  small 24 / medium 32 / large 40
 *   外观  primary / secondary / outline / subtle / transparent + 项目扩展 danger / ghost / compact
 *   交互  使用 *Hover / *Pressed 令牌，禁用走 *Disabled；过渡 --durationFaster
 *   焦点  outline = --strokeWidthThick + --colorBrandStroke1 + 1 px offset
 */
.f-button {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacingHorizontalXS);
  block-size: 32px;
  padding-inline: var(--spacingHorizontalM);
  border: var(--strokeWidthThin) solid transparent;
  border-radius: var(--borderRadiusMedium);
  font-family: var(--fontFamilyBase);
  font-size: var(--fontSizeBase300);
  line-height: var(--lineHeightBase300);
  font-weight: var(--fontWeightSemibold);
  color: var(--colorNeutralForeground1);
  background: transparent;
  cursor: pointer;
  user-select: none;
  transition:
    background-color var(--durationFaster) var(--curveEasyEase),
    color var(--durationFaster) var(--curveEasyEase),
    border-color var(--durationFaster) var(--curveEasyEase),
    box-shadow var(--durationFaster) var(--curveEasyEase);
}

.f-button:focus-visible {
  outline: var(--strokeWidthThick) solid var(--colorBrandStroke1);
  outline-offset: 1px;
}

.f-button:disabled {
  cursor: not-allowed;
  color: var(--colorNeutralForegroundDisabled);
  background: var(--colorNeutralBackgroundDisabled);
  border-color: var(--colorNeutralStrokeDisabled);
  box-shadow: none;
}

.f-button--subtle:disabled,
.f-button--transparent:disabled,
.f-button--ghost:disabled {
  background: transparent;
  border-color: transparent;
}

/* —— 尺寸 —— */
.f-button--small {
  block-size: 24px;
  padding-inline: var(--spacingHorizontalS);
  font-size: var(--fontSizeBase200);
  line-height: var(--lineHeightBase200);
}

.f-button--compact {
  block-size: 28px;
  padding-inline: var(--spacingHorizontalSNudge);
}

.f-button--large {
  block-size: 40px;
  padding-inline: var(--spacingHorizontalL);
  font-size: var(--fontSizeBase400);
  line-height: var(--lineHeightBase400);
}

.f-button--full {
  inline-size: 100%;
}

.f-button--icon-only {
  inline-size: 32px;
  padding: 0;
}

.f-button--icon-only.f-button--small {
  inline-size: 24px;
}

.f-button--icon-only.f-button--compact {
  inline-size: 28px;
}

.f-button--icon-only.f-button--large {
  inline-size: 40px;
}

/* —— Primary（主操作，一屏至多一个） —— */
.f-button--primary {
  background: var(--colorBrandBackground);
  color: var(--colorNeutralForegroundOnBrand);
  border-color: transparent;
}

.f-button--primary:hover:not(:disabled) {
  background: var(--colorBrandBackgroundHover);
}

.f-button--primary:active:not(:disabled) {
  background: var(--colorBrandBackgroundPressed);
}

/* —— Secondary（默认） —— */
.f-button--secondary {
  background: var(--colorNeutralBackground1);
  color: var(--colorNeutralForeground1);
  border-color: var(--colorNeutralStroke1);
}

.f-button--secondary:hover:not(:disabled) {
  background: var(--colorNeutralBackground1Hover);
  border-color: var(--colorNeutralStroke1Hover);
}

.f-button--secondary:active:not(:disabled) {
  background: var(--colorNeutralBackground1Pressed);
  border-color: var(--colorNeutralStroke1Pressed);
}

/* —— Outline（次要操作） —— */
.f-button--outline {
  background: transparent;
  color: var(--colorNeutralForeground1);
  border-color: var(--colorNeutralStroke1);
}

.f-button--outline:hover:not(:disabled) {
  background: var(--colorSubtleBackgroundHover);
  border-color: var(--colorNeutralStroke1Hover);
}

.f-button--outline:active:not(:disabled) {
  background: var(--colorSubtleBackgroundPressed);
}

/* —— Subtle / Ghost：低强调 —— */
.f-button--subtle,
.f-button--ghost {
  background: transparent;
  color: var(--colorNeutralForeground2);
  border-color: transparent;
}

.f-button--subtle:hover:not(:disabled),
.f-button--ghost:hover:not(:disabled) {
  background: var(--colorSubtleBackgroundHover);
  color: var(--colorNeutralForeground2Hover);
}

.f-button--subtle:active:not(:disabled),
.f-button--ghost:active:not(:disabled) {
  background: var(--colorSubtleBackgroundPressed);
  color: var(--colorNeutralForeground2Pressed);
}

/* —— Transparent：类链接操作 —— */
.f-button--transparent {
  background: transparent;
  color: var(--colorBrandForeground1);
  border-color: transparent;
}

.f-button--transparent:hover:not(:disabled) {
  background: var(--colorSubtleBackgroundHover);
  color: var(--colorBrandForeground2Hover);
}

.f-button--transparent:active:not(:disabled) {
  background: var(--colorSubtleBackgroundPressed);
  color: var(--colorBrandForeground2Pressed);
}

/* —— Danger：危险/不可逆操作（项目扩展） —— */
.f-button--danger {
  background: var(--colorStatusDangerBackground3);
  color: var(--colorNeutralForegroundOnBrand);
  border-color: transparent;
}

.f-button--danger:hover:not(:disabled) {
  background: var(--colorStatusDangerBackground3Hover);
}

.f-button--danger:active:not(:disabled) {
  background: var(--colorStatusDangerBackground3Pressed);
}

/* —— Loading：保留宽度，spinner 旋转 —— */
.f-button--loading {
  cursor: progress;
}

.f-button__spinner {
  display: inline-flex;
  width: 16px;
  height: 16px;
  animation: f-button-spin 600ms linear infinite;
}

@keyframes f-button-spin {
  to {
    transform: rotate(360deg);
  }
}

.f-button__icon {
  font-size: 16px;
  flex-shrink: 0;
}

.f-button--large .f-button__icon {
  font-size: 20px;
}

.f-button__label {
  white-space: nowrap;
}
</style>
