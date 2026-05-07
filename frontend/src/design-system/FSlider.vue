<script setup lang="ts">
/**
 * 数值 Slider。
 * 兼容性优先使用原生 input[type=range]，叠加自定义视觉样式：
 *   - 拇指 16 px / 移动端 24 px；
 *   - 轨道 4 px / 移动端 6 px；
 *   - 选中段使用品牌色填充。
 *
 * 暴露百分比派生值给样式（CSS 变量 --f-slider-percent），
 * 用于绘制「已选段」并兼容 iOS Safari。
 */
import { computed } from 'vue';

import { useLocalId } from './utils';

interface FSliderProps {
  modelValue: number;
  min?: number;
  max?: number;
  step?: number;
  disabled?: boolean;
  ariaLabel?: string;
  /** 是否显示当前值的小气泡；默认显示在拇指右侧。 */
  showValue?: boolean;
}

const props = withDefaults(defineProps<FSliderProps>(), {
  min: 0,
  max: 100,
  step: 1,
  disabled: false,
  ariaLabel: undefined,
  showValue: false,
});

/**
 * 双事件契约：
 *  - update:modelValue：拖动过程中持续触发，业务侧应当节流；
 *  - change：抬手或键盘 commit 时触发一次，业务侧用它执行最终落库。
 * 这样的契约让 useThrottledSlider 等高频场景能严格区分「中间值」与「最终值」。
 */
const emit = defineEmits<{
  (event: 'update:modelValue', value: number): void;
  (event: 'change', value: number): void;
}>();

const id = useLocalId('f-slider');
const percent = computed(() => {
  const range = props.max - props.min;
  if (range <= 0) return 0;
  const clamped = Math.min(props.max, Math.max(props.min, props.modelValue));
  return ((clamped - props.min) / range) * 100;
});

function onInput(event: Event): void {
  const value = Number((event.target as HTMLInputElement).value);
  emit('update:modelValue', value);
}

function onChange(event: Event): void {
  const value = Number((event.target as HTMLInputElement).value);
  emit('change', value);
}
</script>

<template>
  <div class="f-slider" :class="{ 'f-slider--disabled': disabled }" :style="{ '--f-slider-percent': `${percent}%` }">
    <input :id="id" type="range" class="f-slider__input" :min="min" :max="max" :step="step" :value="modelValue"
      :disabled="disabled" :aria-label="ariaLabel" :aria-valuenow="modelValue" :aria-valuemin="min" :aria-valuemax="max"
      @input="onInput" @change="onChange" />
    <span v-if="showValue" class="f-slider__value">{{ modelValue }}</span>
  </div>
</template>

<style scoped>
.f-slider {
  --f-slider-track-height: 4px;
  --f-slider-thumb-size: 16px;
  display: flex;
  align-items: center;
  gap: var(--spacing-m);
  width: 100%;
}

.f-slider__input {
  flex: 1 1 auto;
  width: 100%;
  height: var(--f-slider-thumb-size);
  margin: 0;
  background: transparent;
  appearance: none;
  -webkit-appearance: none;
  cursor: pointer;
}

.f-slider__input::-webkit-slider-runnable-track {
  height: var(--f-slider-track-height);
  border-radius: var(--radius-circular);
  background: linear-gradient(to right,
      var(--color-background-brand) var(--f-slider-percent, 0%),
      var(--color-border-default) var(--f-slider-percent, 0%));
}

.f-slider__input::-moz-range-track {
  height: var(--f-slider-track-height);
  border-radius: var(--radius-circular);
  background: var(--color-border-default);
}

.f-slider__input::-moz-range-progress {
  height: var(--f-slider-track-height);
  border-radius: var(--radius-circular);
  background: var(--color-background-brand);
}

.f-slider__input::-webkit-slider-thumb {
  appearance: none;
  -webkit-appearance: none;
  width: var(--f-slider-thumb-size);
  height: var(--f-slider-thumb-size);
  border-radius: var(--radius-circular);
  background: var(--color-text-inverse);
  border: 2px solid var(--color-background-brand);
  box-shadow: var(--shadow-2);
  margin-top: calc((var(--f-slider-track-height) - var(--f-slider-thumb-size)) / 2);
  /* hover/active 缩放走 spring 曲线，按下回弹更"有手感"。 */
  transition: transform var(--motion-duration-medium) var(--motion-curve-spring),
    box-shadow var(--motion-duration-medium) var(--motion-curve-ease);
}

.f-slider__input::-moz-range-thumb {
  width: var(--f-slider-thumb-size);
  height: var(--f-slider-thumb-size);
  border-radius: var(--radius-circular);
  background: var(--color-text-inverse);
  border: 2px solid var(--color-background-brand);
  box-shadow: var(--shadow-2);
}

/* 键盘聚焦时光晕用 4 px color-mix 半透明，与 FInput 同样柔感。 */
.f-slider__input:focus-visible::-webkit-slider-thumb {
  box-shadow: 0 0 0 4px color-mix(in srgb, var(--color-border-focus) 32%, transparent);
}

.f-slider__input:hover:not(:disabled)::-webkit-slider-thumb {
  transform: scale(1.05);
}

.f-slider__input:active:not(:disabled)::-webkit-slider-thumb {
  transform: scale(1.15);
}

.f-slider--disabled {
  opacity: 0.55;
  pointer-events: none;
}

.f-slider__value {
  min-width: 36px;
  font-size: var(--type-body1-size);
  font-variant-numeric: tabular-nums;
  text-align: right;
  color: var(--color-text-primary);
}

@media (max-width: 767px) {
  .f-slider {
    --f-slider-track-height: 6px;
    --f-slider-thumb-size: 24px;
  }
}
</style>
