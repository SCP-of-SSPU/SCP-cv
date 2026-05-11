<script setup lang="ts">
/**
 * 单一 Radio 项；通常不单独使用，由 FRadioGroup 注入 group 上下文。
 *
 * 设计要点（Fluent 2 v9 Radio）：
 *   - 视觉：圆点描边 + 选中态内嵌实心圆（颜色取自 brand）；
 *   - 仅在 FRadioGroup 内有效；脱离 group 时退化为 disabled。
 */
import { computed, inject, type Ref } from 'vue';

import { useLocalId } from './utils';

interface FRadioProps {
  /** 当前选项的值；FRadioGroup 通过 group.modelValue 比对决定选中态。 */
  value: string | number;
  label?: string;
  /** 不可见 label 时的辅助名称。 */
  ariaLabel?: string;
  disabled?: boolean;
}

const props = withDefaults(defineProps<FRadioProps>(), {
  label: undefined,
  ariaLabel: undefined,
  disabled: false,
});

interface RadioGroupContext {
  name: string;
  modelValue: Ref<string | number | null>;
  disabled: Ref<boolean>;
  select: (value: string | number) => void;
}

const group = inject<RadioGroupContext | null>('f-radio-group', null);

const radioId = useLocalId('f-radio');
const checked = computed(() => group?.modelValue.value === props.value);
const finalDisabled = computed(() => props.disabled || Boolean(group?.disabled.value));

const rootClass = computed(() => [
  'f-radio',
  checked.value && 'f-radio--checked',
  finalDisabled.value && 'f-radio--disabled',
]);

function onChange(): void {
  if (finalDisabled.value || !group) return;
  group.select(props.value);
}
</script>

<template>
  <label :for="radioId" :class="rootClass">
    <input :id="radioId" type="radio" class="visually-hidden" :name="group?.name" :checked="checked"
      :disabled="finalDisabled" :aria-label="ariaLabel ?? label" @change="onChange" />
    <span class="f-radio__circle" aria-hidden="true">
      <span class="f-radio__dot" />
    </span>
    <span v-if="label || $slots.default" class="f-radio__label">
      <slot>{{ label }}</slot>
    </span>
  </label>
</template>

<style scoped>
.f-radio {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-s);
  cursor: pointer;
  user-select: none;
  font-size: var(--type-body1-size);
  color: var(--color-text-primary);
}

.f-radio--disabled {
  cursor: not-allowed;
  color: var(--color-text-disabled);
}

.f-radio__circle {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  flex-shrink: 0;
  border-radius: var(--radius-circular);
  border: var(--stroke-width-thin) solid var(--color-border-strong);
  background: var(--color-background-card);
  transition: border-color var(--motion-duration-medium) var(--motion-curve-ease),
    box-shadow var(--motion-duration-medium) var(--motion-curve-ease),
    transform var(--motion-duration-fast) var(--motion-curve-ease);
}

.f-radio__dot {
  width: 8px;
  height: 8px;
  border-radius: var(--radius-circular);
  background: var(--color-background-brand);
  transform: scale(0);
  /* 选中时圆点 spring 弹出，未选时缩回。 */
  transition: transform var(--motion-duration-medium) var(--motion-curve-spring);
}

.f-radio--checked .f-radio__circle {
  border-color: var(--color-background-brand);
}

.f-radio--checked .f-radio__dot {
  transform: scale(1);
}

.f-radio:hover:not(.f-radio--disabled) .f-radio__circle {
  border-color: var(--color-background-brand);
  box-shadow: var(--shadow-2);
}

.f-radio:active:not(.f-radio--disabled) .f-radio__circle {
  transform: scale(var(--motion-press-scale));
  transition-duration: var(--motion-duration-ultra-fast);
}

.f-radio:focus-within .f-radio__circle {
  box-shadow: var(--shadow-focus), var(--shadow-2);
}

.f-radio--disabled .f-radio__circle {
  background: var(--color-background-disabled);
  border-color: var(--color-border-disabled);
}

.f-radio--disabled .f-radio__dot {
  background: var(--color-text-disabled);
}

.f-radio__label {
  flex: 1 1 auto;
}

@media (max-width: 767px) {
  .f-radio__circle {
    width: 22px;
    height: 22px;
  }

  .f-radio__dot {
    width: 10px;
    height: 10px;
  }
}
</style>
