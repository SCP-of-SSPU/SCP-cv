<script setup lang="ts">
/**
 * 多行文本输入。与 FInput 共享同一套 token；支持 minRows / maxRows 自动撑高。
 */
import { computed, inject, ref, type Ref } from 'vue';

interface FTextareaProps {
  modelValue: string;
  placeholder?: string;
  disabled?: boolean;
  readonly?: boolean;
  id?: string;
  ariaLabel?: string;
  rows?: number;
  maxLength?: number;
}

const props = withDefaults(defineProps<FTextareaProps>(), {
  placeholder: '',
  disabled: false,
  readonly: false,
  id: undefined,
  ariaLabel: undefined,
  rows: 3,
  maxLength: undefined,
});

const emit = defineEmits<(event: 'update:modelValue', value: string) => void>();

interface FieldContext {
  id: string;
  describedBy: Ref<string | undefined>;
  required: Ref<boolean>;
  invalid: Ref<boolean>;
}

const field = inject<FieldContext | null>('f-field', null);
const inputId = computed(() => props.id ?? field?.id);
const describedBy = computed(() => field?.describedBy.value);
const isInvalid = computed(() => Boolean(field?.invalid.value));

const innerEl = ref<HTMLTextAreaElement | null>(null);

function onInput(event: Event): void {
  emit('update:modelValue', (event.target as HTMLTextAreaElement).value);
}

defineExpose({
  focus: (): void => innerEl.value?.focus(),
});
</script>

<template>
  <textarea
    ref="innerEl"
    :id="inputId"
    class="f-textarea"
    :class="{
      'f-textarea--invalid': isInvalid,
      'f-textarea--disabled': disabled,
    }"
    :value="modelValue"
    :rows="rows"
    :placeholder="placeholder"
    :disabled="disabled"
    :readonly="readonly"
    :maxlength="maxLength"
    :aria-label="ariaLabel"
    :aria-describedby="describedBy"
    :aria-invalid="isInvalid || undefined"
    :aria-required="field?.required.value || undefined"
    @input="onInput"
  />
</template>

<style scoped>
.f-textarea {
  display: block;
  width: 100%;
  min-height: calc(var(--type-body1-line) * 3 + 16px);
  padding: var(--spacing-s) var(--spacing-m);
  border-radius: var(--radius-medium);
  border: 1px solid var(--color-border-default);
  background: var(--color-background-card);
  color: var(--color-text-primary);
  font: inherit;
  resize: vertical;
  transition:
    border-color var(--motion-duration-fast) var(--motion-curve-ease),
    box-shadow var(--motion-duration-fast) var(--motion-curve-ease);
}

.f-textarea:hover:not(:disabled) {
  border-color: var(--color-border-strong);
}

.f-textarea:focus-visible {
  outline: none;
  border-color: var(--color-border-focus);
  box-shadow: 0 0 0 1px var(--color-border-focus);
}

.f-textarea--invalid {
  border-color: var(--color-border-error);
}

.f-textarea--disabled,
.f-textarea:disabled {
  background: var(--color-background-disabled);
  color: var(--color-text-disabled);
  cursor: not-allowed;
}
</style>
