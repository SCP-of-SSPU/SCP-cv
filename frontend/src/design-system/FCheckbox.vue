<script setup lang="ts">
/**
 * Fluent 2 Checkbox：表单类多选 / 单一确认的二态控件。
 *
 * 与 FSwitch 的语义区分（重要）：
 *   - FSwitch：即时生效的二元状态（如「启用静音」「循环播放」），切换即上报；
 *   - FCheckbox：表单一组选择，提交时才统一应用，可以全选 / 半选；
 *
 * 当前业务多数场景仍应使用 FSwitch；本组件作为 Fluent 2 标准补齐，
 * 用于未来批量操作面板、表单同意条款等。
 */
import { computed, inject, type Ref } from 'vue';

import FIcon from './FIcon.vue';
import { useLocalId } from './utils';

interface FCheckboxProps {
  modelValue: boolean;
  /** indeterminate：所谓"半选"，用于全选父项指示部分子项已选。 */
  indeterminate?: boolean;
  label?: string;
  /** label 不可见时（仅图标场景）必须提供，用于辅助技术。 */
  ariaLabel?: string;
  disabled?: boolean;
  size?: 'medium' | 'large';
  /** 显式 id；处于 FField 内会被自动注入。 */
  id?: string;
}

const props = withDefaults(defineProps<FCheckboxProps>(), {
  indeterminate: false,
  label: undefined,
  ariaLabel: undefined,
  disabled: false,
  size: 'medium',
  id: undefined,
});

const emit = defineEmits<{
  (event: 'update:modelValue', value: boolean): void;
}>();

interface FieldContext {
  id: string;
  describedBy: Ref<string | undefined>;
  required: Ref<boolean>;
  invalid: Ref<boolean>;
}

// 与 FInput / FCombobox 一致：在 FField 内时自动接管 aria 关联。
const field = inject<FieldContext | null>('f-field', null);

const internalId = useLocalId('f-checkbox');
const checkboxId = computed(() => props.id ?? field?.id ?? internalId);
const describedBy = computed(() => field?.describedBy.value);
const isInvalid = computed(() => Boolean(field?.invalid.value));

const rootClass = computed(() => [
  'f-checkbox',
  `f-checkbox--${props.size}`,
  props.modelValue && 'f-checkbox--checked',
  props.indeterminate && 'f-checkbox--indeterminate',
  props.disabled && 'f-checkbox--disabled',
  isInvalid.value && 'f-checkbox--invalid',
]);

function toggle(): void {
  if (props.disabled) return;
  // indeterminate 状态点击后默认进入 checked，与 Fluent 2 行为一致。
  emit('update:modelValue', !props.modelValue);
}

function onKey(event: KeyboardEvent): void {
  if (event.key === ' ') {
    event.preventDefault();
    toggle();
  }
}
</script>

<template>
  <label :for="checkboxId" :class="rootClass">
    <input :id="checkboxId" type="checkbox" class="visually-hidden" :checked="modelValue"
      :aria-checked="indeterminate ? 'mixed' : modelValue" :disabled="disabled" :aria-label="ariaLabel ?? label"
      :aria-describedby="describedBy" :aria-invalid="isInvalid || undefined"
      :aria-required="field?.required.value || undefined" @change="toggle" @keydown="onKey" />
    <span class="f-checkbox__box" aria-hidden="true">
      <FIcon v-if="indeterminate" class="f-checkbox__icon" name="subtract_16_filled" />
      <FIcon v-else-if="modelValue" class="f-checkbox__icon" name="checkmark_16_filled" />
    </span>
    <span v-if="label" class="f-checkbox__label">{{ label }}</span>
  </label>
</template>

<style scoped>
.f-checkbox {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-s);
  cursor: pointer;
  user-select: none;
  font-size: var(--type-body1-size);
  color: var(--color-text-primary);
}

.f-checkbox--disabled {
  cursor: not-allowed;
  color: var(--color-text-disabled);
}

.f-checkbox__box {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  flex-shrink: 0;
  border-radius: var(--radius-small);
  border: var(--stroke-width-thin) solid var(--color-border-strong);
  background: var(--color-background-card);
  /* hover/checked/focus 颜色与底色一并 medium(160ms) 过渡，状态切换更柔。 */
  transition: background var(--motion-duration-medium) var(--motion-curve-ease),
    border-color var(--motion-duration-medium) var(--motion-curve-ease),
    box-shadow var(--motion-duration-medium) var(--motion-curve-ease),
    transform var(--motion-duration-fast) var(--motion-curve-ease);
}

.f-checkbox--large .f-checkbox__box {
  width: 20px;
  height: 20px;
  border-radius: var(--radius-medium);
}

.f-checkbox:hover:not(.f-checkbox--disabled) .f-checkbox__box {
  border-color: var(--color-background-brand);
  box-shadow: var(--shadow-2);
}

.f-checkbox--checked .f-checkbox__box,
.f-checkbox--indeterminate .f-checkbox__box {
  background: var(--color-background-brand);
  border-color: var(--color-background-brand);
  color: var(--color-text-inverse);
}

.f-checkbox--checked:hover:not(.f-checkbox--disabled) .f-checkbox__box,
.f-checkbox--indeterminate:hover:not(.f-checkbox--disabled) .f-checkbox__box {
  background: var(--color-background-brand-hover);
  border-color: var(--color-background-brand-hover);
  box-shadow: var(--halo-brand);
}

.f-checkbox:active:not(.f-checkbox--disabled) .f-checkbox__box {
  /* 按下时轻微下沉 + 微缩，与 FButton 节奏一致。 */
  transform: scale(var(--motion-press-scale));
  transition-duration: var(--motion-duration-ultra-fast);
}

.f-checkbox:focus-within .f-checkbox__box {
  box-shadow: var(--shadow-focus), var(--shadow-2);
}

.f-checkbox--invalid .f-checkbox__box {
  border-color: var(--color-border-error);
}

.f-checkbox--invalid:focus-within .f-checkbox__box {
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--color-border-error) 28%, transparent);
}

.f-checkbox--disabled .f-checkbox__box {
  background: var(--color-background-disabled);
  border-color: var(--color-border-disabled);
  opacity: 0.8;
}

.f-checkbox__icon {
  width: 14px;
  height: 14px;
  /* 勾选图标 pop 入场：≤ 5% 过冲；与 FToast 同款 spring。 */
  animation: f-pop var(--motion-duration-medium) var(--motion-curve-spring) both;
}

.f-checkbox--large .f-checkbox__icon {
  width: 16px;
  height: 16px;
}

.f-checkbox__label {
  flex: 1 1 auto;
}

@media (max-width: 767px) {
  .f-checkbox__box {
    width: 22px;
    height: 22px;
  }

  .f-checkbox__icon {
    width: 18px;
    height: 18px;
  }
}
</style>
