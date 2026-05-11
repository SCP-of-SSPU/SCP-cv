<script setup lang="ts">
/**
 * 输入框组件：
 *   - 可独立使用（自带 placeholder，但不替代 Label，建议外层套 FField）。
 *   - 支持 prefix / suffix 插槽，用于搜索图标、单位提示等。
 *   - 自动从 FField 注入 id / aria-describedby / aria-invalid。
 */
import { computed, inject, ref, watch, type Ref } from 'vue';

interface FInputProps {
  modelValue: string;
  placeholder?: string;
  /** HTML input type，限定常用项避免误用。 */
  type?: 'text' | 'search' | 'url' | 'number' | 'password' | 'email' | 'tel';
  disabled?: boolean;
  readonly?: boolean;
  /** 显式 id；若处于 FField 内会被覆盖。 */
  id?: string;
  /** 显式 aria-label；当无 FField 包裹且没有可见 label 时必填。 */
  ariaLabel?: string;
  /** 不变长输入字段（如「跳页」数字框），影响样式但不强制限位。 */
  maxLength?: number;
  /** 不显示边框，常用于嵌入到工具条的紧凑场景。 */
  appearance?: 'outline' | 'filled';
  /** 控件视觉尺寸；默认按 32 px，桌面紧凑表单可选 compact。 */
  size?: 'compact' | 'medium' | 'large';
  /** 自动获取焦点（仅在显式需要时启用，避免对话框打开后劫持焦点）。 */
  autofocus?: boolean;
}

const props = withDefaults(defineProps<FInputProps>(), {
  placeholder: '',
  type: 'text',
  disabled: false,
  readonly: false,
  id: undefined,
  ariaLabel: undefined,
  maxLength: undefined,
  appearance: 'outline',
  size: 'medium',
  autofocus: false,
});

const emit = defineEmits<{
  (event: 'update:modelValue', value: string): void;
  (event: 'enter'): void;
}>();

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

const innerEl = ref<HTMLInputElement | null>(null);

watch(
  () => props.autofocus,
  (val) => {
    if (val) requestAnimationFrame(() => innerEl.value?.focus());
  },
  { immediate: true },
);

function onInput(event: Event): void {
  emit('update:modelValue', (event.target as HTMLInputElement).value);
}

function onKeyDown(event: KeyboardEvent): void {
  if (event.key === 'Enter') emit('enter');
}

defineExpose({
  focus: (): void => {
    innerEl.value?.focus();
  },
  el: innerEl,
});
</script>

<template>
  <div class="f-input" :class="[
    `f-input--${appearance}`,
    `f-input--${size}`,
    isInvalid && 'f-input--invalid',
    disabled && 'f-input--disabled',
  ]">
    <span v-if="$slots.prefix" class="f-input__prefix">
      <slot name="prefix" />
    </span>
    <input ref="innerEl" :id="inputId" class="f-input__inner" :type="type" :value="modelValue"
      :placeholder="placeholder" :disabled="disabled" :readonly="readonly" :maxlength="maxLength"
      :aria-label="ariaLabel" :aria-describedby="describedBy" :aria-invalid="isInvalid || undefined"
      :aria-required="field?.required.value || undefined" @input="onInput" @keydown="onKeyDown" />
    <span v-if="$slots.suffix" class="f-input__suffix">
      <slot name="suffix" />
    </span>
  </div>
</template>

<style scoped>
.f-input {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-s);
  width: 100%;
  min-height: 32px;
  padding: 0 var(--spacing-m);
  border-radius: var(--radius-medium);
  border: 1px solid var(--color-border-default);
  background: var(--color-background-card);
  color: var(--color-text-primary);
  box-shadow: var(--shadow-control);
  /* 过渡用 medium(160ms) 让 hover/focus 切换更柔，配合 box-shadow 双层光晕。 */
  transition:
    border-color var(--motion-duration-medium) var(--motion-curve-ease),
    background-color var(--motion-duration-medium) var(--motion-curve-ease),
    box-shadow var(--motion-duration-medium) var(--motion-curve-ease);
}

.f-input--filled {
  background: var(--color-background-subtle);
  border-color: transparent;
}

.f-input--compact {
  min-height: 28px;
}

.f-input--large {
  min-height: 40px;
}

.f-input:hover:not(.f-input--disabled) {
  border-color: var(--color-border-strong);
  box-shadow: var(--shadow-2);
}

.f-input:focus-within {
  border-color: var(--color-border-focus);
  /* 2 px 光晕比 1 px 更柔和，避免硬边导致的"实色描边"观感。 */
  box-shadow: var(--shadow-focus), var(--shadow-2);
}

.f-input--invalid {
  border-color: var(--color-border-error);
  background: color-mix(in srgb, var(--color-status-error-background) 32%, var(--color-background-card));
}

.f-input--invalid:focus-within {
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--color-border-error) 28%, transparent), var(--shadow-2);
}

.f-input--disabled {
  background: var(--color-background-disabled);
  color: var(--color-text-disabled);
  border-color: var(--color-border-disabled);
  cursor: not-allowed;
  box-shadow: none;
}

.f-input__prefix,
.f-input__suffix {
  display: inline-flex;
  align-items: center;
  color: var(--color-text-tertiary);
  font-size: var(--type-body1-size);
}

.f-input__inner {
  flex: 1 1 auto;
  width: 100%;
  height: 100%;
  border: none;
  outline: none;
  background: transparent;
  color: inherit;
  font: inherit;
  padding: 0;
}

.f-input__inner::placeholder {
  color: var(--color-text-tertiary);
}

.f-input__inner:disabled {
  cursor: not-allowed;
  color: inherit;
}

@media (max-width: 767px) {
  .f-input {
    min-height: var(--touch-target-min);
  }
}
</style>
