<script setup lang="ts">
/**
 * 表单字段包装：Label + Required + Hint/Error。
 * DESIGN.md §12.3：placeholder 不替代 Label；必填项不仅依赖红色星号。
 *
 * Slot 用于放置任何可控输入（FInput / FCombobox / FSwitch 等）。
 * 通过 provide/inject 给子组件注入 id / aria-describedby 关联。
 */
import { computed, provide, useSlots } from 'vue';

import { useLocalId } from './utils';

interface FFieldProps {
  /** 必填字段：会渲染「（必填）」文本，不仅靠红星。 */
  required?: boolean;
  /** 字段标签，必填属性。空 label 仅在 visually-hidden 场景使用。 */
  label: string;
  /** 辅助说明，渲染在 Hint 区。 */
  hint?: string;
  /** 错误信息：非空时高亮边框并发出 aria-invalid 关联。 */
  error?: string;
  /** Label 是否仅对 SR 可见（如 Search 字段）。 */
  visuallyHiddenLabel?: boolean;
}

const props = withDefaults(defineProps<FFieldProps>(), {
  required: false,
  hint: undefined,
  error: undefined,
  visuallyHiddenLabel: false,
});

const slots = useSlots();
const fieldId = useLocalId('f-field');
const hintId = useLocalId('f-hint');
const errorId = useLocalId('f-error');

const describedBy = computed(() => {
  const parts: string[] = [];
  if (props.hint) parts.push(hintId);
  if (props.error) parts.push(errorId);
  return parts.length > 0 ? parts.join(' ') : undefined;
});

// 把上下文给到子组件（FInput 等）会自动挂上 id / aria-describedby
provide('f-field', {
  id: fieldId,
  describedBy,
  required: computed(() => props.required),
  invalid: computed(() => Boolean(props.error)),
});

void slots; // 显式标记 slots 已使用（仅占位，模板中用 $slots）
</script>

<template>
  <div class="f-field" :class="{ 'f-field--invalid': !!error }">
    <label
      :for="fieldId"
      class="f-field__label"
      :class="{ 'visually-hidden': visuallyHiddenLabel }"
    >
      <span>{{ label }}</span>
      <span v-if="required" class="f-field__required" aria-hidden="true">（必填）</span>
    </label>

    <div class="f-field__control">
      <slot :id="fieldId" :describedBy="describedBy" />
    </div>

    <p v-if="hint && !error" :id="hintId" class="f-field__hint">{{ hint }}</p>
    <p v-if="error" :id="errorId" class="f-field__error" role="alert">{{ error }}</p>
  </div>
</template>

<style scoped>
.f-field {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
  min-width: 0;
}

.f-field__label {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-xs);
  font-size: var(--type-caption1-size);
  line-height: var(--type-caption1-line);
  font-weight: 600;
  color: var(--color-text-secondary);
}

.f-field__required {
  font-weight: 400;
  color: var(--color-text-tertiary);
}

.f-field__control {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.f-field__hint {
  margin: 0;
  font-size: var(--type-caption1-size);
  line-height: var(--type-caption1-line);
  color: var(--color-text-tertiary);
}

.f-field__error {
  margin: 0;
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-xs);
  font-size: var(--type-caption1-size);
  line-height: var(--type-caption1-line);
  color: var(--color-text-error);
}
</style>
