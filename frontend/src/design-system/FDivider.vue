<script setup lang="ts">
/**
 * Fluent 2 Divider：分组、章节、内嵌列表的视觉分隔。
 *
 * 设计稿 §5.x / Fluent 2 v9 Divider：
 *   - default：1 px 浅边线，列表项之间或卡片内分组；
 *   - strong：1 px 中性强边线，区分主要内容块；
 *   - subtle：0.5 px 半透明，密集表单中的轻分隔。
 *
 * 支持横向（默认）/ 纵向；可附中文 label，居中于线条上（如「危险操作」「最近使用」）。
 * 渲染为 <div role="separator">，复合控件中作为视觉分隔不进入键盘 Tab 序列。
 */
import { computed } from 'vue';

interface FDividerProps {
  /** 视觉强度；默认 default。 */
  appearance?: 'default' | 'strong' | 'subtle';
  /** 朝向；vertical 需要父容器为 flex / inline-flex 才能撑出可见高度。 */
  orientation?: 'horizontal' | 'vertical';
  /** 居中标签文字，仅水平方向生效。 */
  label?: string;
  /** label 对齐方式；center 默认。 */
  align?: 'start' | 'center' | 'end';
}

const props = withDefaults(defineProps<FDividerProps>(), {
  appearance: 'default',
  orientation: 'horizontal',
  label: undefined,
  align: 'center',
});

const rootClass = computed(() => [
  'f-divider',
  `f-divider--${props.orientation}`,
  `f-divider--${props.appearance}`,
  props.label && `f-divider--with-label`,
  props.label && `f-divider--align-${props.align}`,
]);
</script>

<template>
  <div :class="rootClass" role="separator" :aria-orientation="orientation" :aria-label="label || undefined">
    <span v-if="label && orientation === 'horizontal'" class="f-divider__label">{{ label }}</span>
  </div>
</template>

<style scoped>
.f-divider {
  /*
   * 横向：撑满父容器并居中绘制。
   * 当带 label 时，使用 grid 在文字两侧绘制独立线段，避免重叠产生模糊。
   */
  flex-shrink: 0;
}

.f-divider--horizontal {
  width: 100%;
  height: var(--stroke-width-thin);
  background: var(--color-border-subtle);
  margin: var(--spacing-s) 0;
  border: none;
}

.f-divider--horizontal.f-divider--strong {
  background: var(--color-border-default);
}

.f-divider--horizontal.f-divider--subtle {
  height: var(--stroke-width-thin);
  background: color-mix(in srgb, var(--color-border-subtle) 60%, transparent);
}

.f-divider--vertical {
  width: var(--stroke-width-thin);
  align-self: stretch;
  min-height: 1em;
  background: var(--color-border-subtle);
  margin: 0 var(--spacing-s);
}

.f-divider--vertical.f-divider--strong {
  background: var(--color-border-default);
}

.f-divider--vertical.f-divider--subtle {
  background: color-mix(in srgb, var(--color-border-subtle) 60%, transparent);
}

/*
 * 带 label 的水平分隔线：用 grid 三列布局
 *   [line · label · line]
 * align 控制 label 在水平方向的位置（start/center/end）。
 */
.f-divider--with-label {
  display: grid;
  align-items: center;
  gap: var(--spacing-s);
  height: auto;
  margin: var(--spacing-m) 0;
  background: transparent;
}

.f-divider--with-label.f-divider--align-center {
  grid-template-columns: 1fr auto 1fr;
}

.f-divider--with-label.f-divider--align-start {
  grid-template-columns: var(--spacing-2xl) auto 1fr;
}

.f-divider--with-label.f-divider--align-end {
  grid-template-columns: 1fr auto var(--spacing-2xl);
}

.f-divider--with-label::before,
.f-divider--with-label::after {
  content: '';
  height: var(--stroke-width-thin);
  background: var(--color-border-subtle);
}

.f-divider--with-label.f-divider--strong::before,
.f-divider--with-label.f-divider--strong::after {
  background: var(--color-border-default);
}

.f-divider__label {
  font-size: var(--type-caption1-size);
  line-height: var(--type-caption1-line);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-tertiary);
  letter-spacing: 0.04em;
  text-transform: uppercase;
  white-space: nowrap;
}
</style>
