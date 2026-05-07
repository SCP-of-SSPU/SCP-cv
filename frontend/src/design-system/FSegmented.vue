<script setup lang="ts">
/**
 * SegmentedControl：2-4 个互斥选项之间即时切换。
 * 设计稿 §5.5：用于「大屏模式」「源状态」「窗口选择」等场景。
 *
 * 使用方式：v-model 绑定当前 value，options 提供 label/value/icon/disabled。
 */
import { computed } from 'vue';

import FIcon from './FIcon.vue';
import type { FSegmentedOption } from './types';

interface FSegmentedProps {
  modelValue: string | number;
  options: ReadonlyArray<FSegmentedOption<string | number>>;
  /** 整组禁用。 */
  disabled?: boolean;
  /** 仅显示图标，节省宽度（如窗口选择器）。 */
  iconOnly?: boolean;
  /** 在窄屏占满父容器宽度。 */
  fullWidth?: boolean;
  size?: 'compact' | 'medium' | 'large';
  ariaLabel?: string;
}

const props = withDefaults(defineProps<FSegmentedProps>(), {
  disabled: false,
  iconOnly: false,
  fullWidth: false,
  size: 'medium',
  ariaLabel: undefined,
});

const emit = defineEmits<{
  (event: 'update:modelValue', value: string | number): void;
}>();

const containerClass = computed(() => [
  'f-segmented',
  `f-segmented--${props.size}`,
  props.fullWidth && 'f-segmented--full',
  props.disabled && 'f-segmented--disabled',
]);

function pick(option: FSegmentedOption<string | number>): void {
  if (props.disabled || option.disabled || option.value === props.modelValue) return;
  emit('update:modelValue', option.value);
}
</script>

<template>
  <div :class="containerClass" role="tablist" :aria-label="ariaLabel">
    <button v-for="option in options" :key="String(option.value)" type="button" role="tab" class="f-segmented__item"
      :class="{
        'f-segmented__item--selected': option.value === modelValue,
        'f-segmented__item--icon-only': iconOnly,
      }" :disabled="disabled || option.disabled" :aria-selected="option.value === modelValue"
      :aria-label="option.ariaLabel ?? (iconOnly ? option.label : undefined)" @click="pick(option)">
      <FIcon v-if="option.icon" :name="option.icon" class="f-segmented__icon" />
      <span v-if="!iconOnly" class="f-segmented__label">{{ option.label }}</span>
    </button>
  </div>
</template>

<style scoped>
.f-segmented {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 2px;
  border-radius: var(--radius-medium);
  background: var(--color-background-subtle);
  border: 1px solid var(--color-border-subtle);
}

.f-segmented--full {
  display: flex;
  width: 100%;
}

.f-segmented--disabled {
  opacity: 0.55;
  pointer-events: none;
}

.f-segmented__item {
  flex: 1 1 auto;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-xs);
  height: 28px;
  padding: 0 var(--spacing-m);
  border: none;
  border-radius: calc(var(--radius-medium) - 2px);
  background: transparent;
  color: var(--color-text-secondary);
  font-family: inherit;
  font-size: var(--type-body1-size);
  font-weight: 500;
  cursor: pointer;
  /*
   * 切换分段时同时过渡背景、文字色与字重；duration 升到 medium 让 indicator 滑动更柔。
   * 选中态用 inset box-shadow 模拟"轻陷下"，避免突变。
   */
  transition: background var(--motion-duration-medium) var(--motion-curve-ease),
    color var(--motion-duration-medium) var(--motion-curve-ease),
    box-shadow var(--motion-duration-medium) var(--motion-curve-ease);
}

.f-segmented--compact .f-segmented__item {
  height: 24px;
  padding: 0 var(--spacing-s);
  font-size: var(--type-caption1-size);
}

.f-segmented--large .f-segmented__item {
  height: 36px;
  padding: 0 var(--spacing-l);
  font-size: var(--type-body1-size);
}

.f-segmented__item:hover:not(:disabled):not(.f-segmented__item--selected) {
  background: var(--color-background-card);
  color: var(--color-text-primary);
}

.f-segmented__item--selected {
  background: var(--color-background-card);
  color: var(--color-text-primary);
  font-weight: 600;
  /* 浮起感：边框 1 px + 微阴影；不再用强品牌底色，避免与 NavList Active 混淆。 */
  box-shadow: 0 0 0 1px var(--color-border-default), 0 1px 2px rgb(0 0 0 / 0.06);
}

.f-segmented__item--icon-only {
  padding: 0;
  width: 28px;
}

.f-segmented__item:disabled {
  cursor: not-allowed;
  color: var(--color-text-disabled);
}

.f-segmented__icon {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
}

.f-segmented__label {
  white-space: nowrap;
}

@media (max-width: 767px) {
  .f-segmented__item {
    min-height: var(--touch-target-min);
    height: var(--touch-target-min);
  }
}
</style>
