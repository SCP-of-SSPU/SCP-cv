<script setup lang="ts">
/**
 * Switch 开关。仅用于即时生效的二元状态（DESIGN.md §12.7）。
 * Label 描述「开启状态」；当切换会带来不可逆/重大后果时由调用方自行加 Confirm。
 */
import { computed } from 'vue';

import { useLocalId } from './utils';

interface FSwitchProps {
  modelValue: boolean;
  label?: string;
  disabled?: boolean;
  /** 当 label 不可见时（如设置卡内手动放标题）必填，用于辅助技术。 */
  ariaLabel?: string;
  /** 紧凑模式：表单分组中节省垂直空间。 */
  size?: 'default' | 'compact';
}

const props = withDefaults(defineProps<FSwitchProps>(), {
  label: undefined,
  disabled: false,
  ariaLabel: undefined,
  size: 'default',
});

const emit = defineEmits<(event: 'update:modelValue', value: boolean) => void>();

const switchId = useLocalId('f-switch');
const isOn = computed(() => props.modelValue);

function toggle(): void {
  if (props.disabled) return;
  emit('update:modelValue', !isOn.value);
}

function onKey(event: KeyboardEvent): void {
  if (event.key === ' ' || event.key === 'Enter') {
    event.preventDefault();
    toggle();
  }
}
</script>

<template>
  <label :for="switchId" class="f-switch" :class="{
    'f-switch--on': isOn,
    'f-switch--disabled': disabled,
    'f-switch--compact': size === 'compact',
  }">
    <input :id="switchId" type="checkbox" class="visually-hidden" role="switch" :checked="isOn" :disabled="disabled"
      :aria-label="ariaLabel ?? label" @change="toggle" @keydown="onKey" />
    <span class="f-switch__track" aria-hidden="true">
      <span class="f-switch__thumb" />
    </span>
    <span v-if="label" class="f-switch__label">{{ label }}</span>
  </label>
</template>

<style scoped>
.f-switch {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-s);
  cursor: pointer;
  user-select: none;
  font-size: var(--type-body1-size);
  color: var(--color-text-primary);
}

.f-switch--disabled {
  cursor: not-allowed;
  color: var(--color-text-disabled);
}

.f-switch__track {
  position: relative;
  width: 40px;
  height: 20px;
  border-radius: var(--radius-circular);
  background: var(--color-background-disabled);
  border: 1px solid var(--color-border-default);
  /* 拨动时背景与边框过渡走 medium(160ms) ease，让深色 / 浅色对比有"逐渐变化"的观感。 */
  transition: background var(--motion-duration-medium) var(--motion-curve-ease),
    border-color var(--motion-duration-medium) var(--motion-curve-ease),
    box-shadow var(--motion-duration-medium) var(--motion-curve-ease);
}

.f-switch:hover:not(.f-switch--disabled) .f-switch__track {
  border-color: var(--color-border-strong);
}

.f-switch--on:hover:not(.f-switch--disabled) .f-switch__track {
  background: var(--color-background-brand-hover);
  border-color: var(--color-background-brand-hover);
  box-shadow: var(--halo-brand);
}

.f-switch--compact .f-switch__track {
  width: 32px;
  height: 18px;
}

.f-switch__thumb {
  position: absolute;
  top: 50%;
  left: 2px;
  width: 14px;
  height: 14px;
  border-radius: var(--radius-circular);
  background: var(--color-text-secondary);
  transform: translateY(-50%);
  /* 拇指位移采用 spring 曲线，弹性更明显但仅 ≤5% 过冲；duration 提升到 medium。 */
  transition: transform var(--motion-duration-medium) var(--motion-curve-spring),
    background var(--motion-duration-medium) var(--motion-curve-ease);
}

.f-switch--compact .f-switch__thumb {
  width: 12px;
  height: 12px;
}

.f-switch--on .f-switch__track {
  background: var(--color-background-brand);
  border-color: var(--color-background-brand);
}

.f-switch--on .f-switch__thumb {
  transform: translate(20px, -50%);
  background: var(--color-text-inverse);
}

.f-switch--compact.f-switch--on .f-switch__thumb {
  transform: translate(14px, -50%);
}

.f-switch:focus-within .f-switch__track {
  box-shadow: 0 0 0 2px var(--color-border-focus);
}

.f-switch--disabled .f-switch__track {
  opacity: 0.55;
}

.f-switch__label {
  flex: 1 1 auto;
}

@media (max-width: 767px) {
  .f-switch__track {
    width: 44px;
    height: 24px;
  }

  .f-switch__thumb {
    width: 18px;
    height: 18px;
    left: 3px;
  }

  .f-switch--on .f-switch__thumb {
    transform: translate(20px, -50%);
  }
}
</style>
