<script setup lang="ts">
/**
 * Fluent 2 RadioGroup：互斥单选容器。
 *
 * 使用：
 *   <FRadioGroup v-model="value" name="big-screen-mode" label="大屏模式">
 *     <FRadio value="single">单屏</FRadio>
 *     <FRadio value="double">双屏</FRadio>
 *   </FRadioGroup>
 *
 * 与 FSegmented 的取舍：
 *   - 选项 < 5 且短 → FSegmented（视觉更紧凑、状态更直观）；
 *   - 选项 ≥ 5 或需要 description / icon → FRadioGroup；
 *
 * 通过 provide/inject 给子 FRadio 注入 group 上下文；不依赖 native form 提交流。
 */
import { computed, provide, ref, type Ref } from 'vue';

import { useLocalId } from './utils';

interface FRadioGroupProps {
  modelValue: string | number | null;
  /** form name；同组 Radio 共用，便于浏览器无障碍栈合并。 */
  name?: string;
  /** 仅作为可访问名称；视觉上不渲染（通常由外层 FField label 提供可见 label）。 */
  ariaLabel?: string;
  /** 布局方向；默认竖排（垂直堆叠）。 */
  layout?: 'vertical' | 'horizontal';
  disabled?: boolean;
}

const props = withDefaults(defineProps<FRadioGroupProps>(), {
  name: undefined,
  ariaLabel: undefined,
  layout: 'vertical',
  disabled: false,
});

const emit = defineEmits<{
  (event: 'update:modelValue', value: string | number): void;
}>();

const internalName = useLocalId('f-radio-group');
const groupName = computed(() => props.name ?? internalName);
const modelRef: Ref<string | number | null> = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value as string | number),
}) as Ref<string | number | null>;
const disabledRef = computed(() => props.disabled);

function select(value: string | number): void {
  if (props.disabled) return;
  emit('update:modelValue', value);
}

provide('f-radio-group', {
  name: groupName.value,
  modelValue: modelRef,
  disabled: disabledRef,
  select,
});

const containerClass = computed(() => [
  'f-radio-group',
  `f-radio-group--${props.layout}`,
]);

// 仅用于将 ref 真正"挂到"组件，避免 vue-tsc 标记未使用变量
void modelRef;
void disabledRef;
</script>

<template>
  <div :class="containerClass" role="radiogroup" :aria-label="ariaLabel" :aria-disabled="disabled || undefined">
    <slot />
  </div>
</template>

<style scoped>
.f-radio-group {
  display: flex;
  gap: var(--spacing-m);
  min-width: 0;
}

.f-radio-group--vertical {
  flex-direction: column;
  gap: var(--spacing-s);
}

.f-radio-group--horizontal {
  flex-direction: row;
  flex-wrap: wrap;
}
</style>
