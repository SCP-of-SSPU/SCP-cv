<script setup lang="ts">
/**
 * Pivot Tabs：同上下文内平级内容切换。
 * DESIGN.md §12.15 / 设计稿 §5.13：
 *   - 不超过 7 项；超过应改用导航或筛选；
 *   - 当前 Tab 必须有明确选中态（Brand 下划线 + Brand 文字）；
 *   - 键盘：←/→ 切焦点，Enter 激活；移动端支持手势滑动（这里仅保证视觉与键盘可达）。
 */
import { computed, ref } from 'vue';

import FIcon from './FIcon.vue';
import type { FTabsItem } from './types';

interface FTabsProps<TValue extends string | number = string> {
  modelValue: TValue;
  items: ReadonlyArray<FTabsItem<TValue>>;
  /** 视觉风格：line（下划线，默认）/ pill（Pills 横滑）。 */
  appearance?: 'line' | 'pill';
  /** 整组撑满父容器（移动端）。 */
  fullWidth?: boolean;
  size?: 'compact' | 'medium';
  ariaLabel?: string;
}

const props = withDefaults(defineProps<FTabsProps>(), {
  appearance: 'line',
  fullWidth: false,
  size: 'medium',
  ariaLabel: undefined,
});

const emit = defineEmits<{
  (event: 'update:modelValue', value: string | number): void;
}>();

const tabRefs = ref<Array<HTMLButtonElement | null>>([]);

const containerClass = computed(() => [
  'f-tabs',
  `f-tabs--${props.appearance}`,
  `f-tabs--${props.size}`,
  props.fullWidth && 'f-tabs--full',
]);

function pick(item: FTabsItem, index: number): void {
  if (item.disabled || item.value === props.modelValue) return;
  emit('update:modelValue', item.value);
  tabRefs.value[index]?.focus();
}

function moveFocus(direction: 1 | -1, currentIndex: number): void {
  const total = props.items.length;
  for (let step = 1; step <= total; step += 1) {
    const next = (currentIndex + direction * step + total) % total;
    const target = props.items[next];
    if (target && !target.disabled) {
      tabRefs.value[next]?.focus();
      emit('update:modelValue', target.value);
      return;
    }
  }
}

function onKey(event: KeyboardEvent, index: number): void {
  if (event.key === 'ArrowRight') {
    event.preventDefault();
    moveFocus(1, index);
  } else if (event.key === 'ArrowLeft') {
    event.preventDefault();
    moveFocus(-1, index);
  } else if (event.key === 'Home') {
    event.preventDefault();
    const firstEnabled = props.items.findIndex((item) => !item.disabled);
    if (firstEnabled >= 0) {
      tabRefs.value[firstEnabled]?.focus();
      emit('update:modelValue', props.items[firstEnabled].value);
    }
  } else if (event.key === 'End') {
    event.preventDefault();
    const lastEnabled = [...props.items].reverse().findIndex((item) => !item.disabled);
    if (lastEnabled >= 0) {
      const realIdx = props.items.length - 1 - lastEnabled;
      tabRefs.value[realIdx]?.focus();
      emit('update:modelValue', props.items[realIdx].value);
    }
  }
}
</script>

<template>
  <div :class="containerClass" role="tablist" :aria-label="ariaLabel">
    <button v-for="(item, index) in items" :key="String(item.value)"
      :ref="(el) => (tabRefs[index] = el as HTMLButtonElement)" type="button" role="tab" class="f-tabs__item" :class="{
        'f-tabs__item--selected': item.value === modelValue,
      }" :aria-selected="item.value === modelValue" :tabindex="item.value === modelValue ? 0 : -1"
      :disabled="item.disabled" @click="pick(item, index)" @keydown="onKey($event, index)">
      <FIcon v-if="item.icon" class="f-tabs__icon" :name="item.icon" />
      <span class="f-tabs__label">{{ item.label }}</span>
      <span v-if="item.badge !== undefined" class="f-tabs__badge">{{ item.badge }}</span>
    </button>
  </div>
</template>

<style scoped>
.f-tabs {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-xs);
}

.f-tabs--full {
  width: 100%;
  overflow-x: auto;
  scrollbar-width: none;
}

.f-tabs--full::-webkit-scrollbar {
  display: none;
}

.f-tabs__item {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-xs);
  height: 36px;
  padding: 0 var(--spacing-m);
  border: none;
  background: transparent;
  color: var(--color-text-secondary);
  font-family: inherit;
  font-size: var(--type-body1-size);
  font-weight: 500;
  cursor: pointer;
  white-space: nowrap;
  border-radius: var(--radius-medium);
  /* 颜色与底色一并 medium(160ms) 过渡；下划线本体过渡见 ::after 段。 */
  transition: color var(--motion-duration-medium) var(--motion-curve-ease),
    background var(--motion-duration-medium) var(--motion-curve-ease),
    box-shadow var(--motion-duration-medium) var(--motion-curve-ease),
    transform var(--motion-duration-medium) var(--motion-curve-ease);
}

.f-tabs--compact .f-tabs__item {
  height: 32px;
  padding: 0 var(--spacing-s);
}

.f-tabs__item:hover:not(:disabled):not(.f-tabs__item--selected) {
  color: var(--color-text-primary);
  background: var(--color-background-subtle);
  transform: translateY(-1px);
}

.f-tabs__item:disabled {
  cursor: not-allowed;
  color: var(--color-text-disabled);
}

.f-tabs__icon {
  width: 18px;
  height: 18px;
}

.f-tabs__badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 20px;
  height: 18px;
  padding: 0 var(--spacing-xs);
  border-radius: var(--radius-small);
  background: var(--color-background-subtle);
  color: var(--color-text-tertiary);
  font-size: var(--type-caption2-size);
  font-weight: 600;
}

/* Line（下划线） */
.f-tabs--line {
  border-bottom: 1px solid var(--color-border-subtle);
}

.f-tabs--line .f-tabs__item--selected {
  color: var(--color-text-brand);
  background: transparent;
}

.f-tabs--line .f-tabs__item--selected::after {
  content: '';
  position: absolute;
  left: var(--spacing-m);
  right: var(--spacing-m);
  bottom: -1px;
  height: 2px;
  background: var(--color-background-brand);
  border-radius: var(--radius-circular);
  /* underline 在切换时左右伸缩，配合颜色过渡形成「下划线流动」效果。 */
  animation: f-rise var(--motion-duration-entrance) var(--motion-curve-emphasized) both;
}

.f-tabs__item:focus-visible {
  outline: none;
  box-shadow: var(--shadow-focus);
}

/* Pill（横滑 Pill） */
.f-tabs--pill {
  gap: var(--spacing-s);
}

.f-tabs--pill .f-tabs__item {
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-circular);
}

.f-tabs--pill .f-tabs__item--selected {
  background: var(--color-background-brand);
  border-color: var(--color-background-brand);
  color: var(--color-text-inverse);
  box-shadow: var(--shadow-brand);
  /* selected pill 微微浮起，与 hover 的位移区分，避免选中态视觉"贴底"。 */
  transform: translateY(-1px);
}

.f-tabs--pill .f-tabs__item--selected .f-tabs__badge {
  background: color-mix(in srgb, var(--color-text-inverse) 22%, transparent);
  color: var(--color-text-inverse);
}

@media (max-width: 767px) {
  .f-tabs__item {
    min-height: var(--touch-target-min);
    height: var(--touch-target-min);
  }
}
</style>
