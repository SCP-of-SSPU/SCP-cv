<script setup lang="ts">
/**
 * 通用卡片容器：默认带轻量阴影；hover / focus-within 会提升层级。
 *
 * 设计稿 §5.6：
 *   - 容器层级：canvas → card → 嵌套 subtle；
 *   - 卡片整体可点击时（如预案卡），内部不再放独立点击目标，附属操作收到 ActionSheet。
 *
 * Slot：
 *   - eyebrow：可选，渲染为 12 px caption + uppercase tracking
 *   - title：可选，渲染为 type.title3
 *   - actions：可选，标题右侧操作区
 *   - default：卡片正文
 */
import { computed } from 'vue';

import { cls } from './utils';

type CardAccent = 'none' | 'brand' | 'success' | 'warning' | 'danger';

interface FCardProps {
  /** 是否在 hover 时浮起一档；常用于「整张可点击」的预案卡。 */
  interactive?: boolean;
  /** 提供 padding 预设；compact 适用于嵌套卡片或紧凑列表项。 */
  padding?: 'none' | 'compact' | 'normal' | 'cozy';
  /** 直接选中态（如预案预览中的当前选中卡片）。 */
  selected?: boolean;
  /** 视觉变体：default 卡片层；subtle 嵌套层；glass 半透明顶栏卡。 */
  variant?: 'default' | 'subtle' | 'glass';
  /**
   * 左侧 4 px 状态指示条，用于强调卡片语义。
   * 例如：brand=置顶 / success=正常运行 / warning=待恢复 / danger=异常。
   */
  accent?: CardAccent;
}

const props = withDefaults(defineProps<FCardProps>(), {
  interactive: false,
  padding: 'normal',
  selected: false,
  variant: 'default',
  accent: 'none',
});

const rootClass = computed(() =>
  cls(
    'f-card',
    `f-card--${props.variant}`,
    `f-card--pad-${props.padding}`,
    props.accent !== 'none' && `f-card--accent-${props.accent}`,
    props.interactive && 'f-card--interactive',
    props.selected && 'f-card--selected',
  ),
);
</script>

<template>
  <article :class="rootClass">
    <header v-if="$slots.eyebrow || $slots.title || $slots.actions" class="f-card__header">
      <div class="f-card__heading">
        <p v-if="$slots.eyebrow" class="f-card__eyebrow">
          <slot name="eyebrow" />
        </p>
        <h3 v-if="$slots.title" class="f-card__title">
          <slot name="title" />
        </h3>
      </div>
      <div v-if="$slots.actions" class="f-card__actions">
        <slot name="actions" />
      </div>
    </header>
    <div class="f-card__body">
      <slot />
    </div>
    <footer v-if="$slots.footer" class="f-card__footer">
      <slot name="footer" />
    </footer>
  </article>
</template>

<style scoped>
.f-card {
  position: relative;
  display: flex;
  flex-direction: column;
  background: var(--color-background-card);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-large);
  color: var(--color-text-primary);
  box-shadow: var(--shadow-card);
  overflow: clip;
  transform: translateY(0);
  animation: f-rise var(--motion-duration-entrance) var(--motion-curve-emphasized) both;
  /*
   * 卡片承载信息密度高，默认只调整阴影；interactive 变体再增加位移，
   * 避免普通表单卡在鼠标经过时产生过强的可点击暗示。
   * transition 中加入「after pseudo opacity」用于 Reveal 高光（::after）平滑显隐。
   */
  transition:
    border-color var(--motion-duration-medium) var(--motion-curve-ease),
    background-color var(--motion-duration-medium) var(--motion-curve-ease),
    box-shadow var(--motion-duration-entrance) var(--motion-curve-ease),
    transform var(--motion-duration-entrance) var(--motion-curve-emphasized);
}

/*
 * Reveal 风格内描边高光：模拟 Fluent 2「light from above」，
 * 用于提升卡片质感而不占用 box-shadow 通道。
 */
.f-card::after {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  pointer-events: none;
  box-shadow: var(--ring-accent);
  opacity: 0.55;
  transition: opacity var(--motion-duration-medium) var(--motion-curve-ease);
}

.f-card:hover,
.f-card:focus-within {
  border-color: var(--color-border-default);
  box-shadow: var(--shadow-card-hover);
}

.f-card:hover::after,
.f-card:focus-within::after {
  opacity: 1;
}

.f-card--subtle {
  background: var(--color-background-subtle);
  box-shadow: var(--shadow-control);
}

.f-card--glass {
  background: var(--color-background-glass);
  -webkit-backdrop-filter: blur(18px);
  backdrop-filter: blur(18px);
  border-color: color-mix(in srgb, var(--color-border-subtle) 60%, transparent);
  box-shadow: var(--shadow-card);
}

.f-card--pad-none {
  padding: 0;
}

.f-card--pad-compact {
  padding: var(--spacing-m);
  gap: var(--spacing-m);
}

.f-card--pad-normal {
  padding: var(--spacing-l);
  gap: var(--spacing-m);
}

.f-card--pad-cozy {
  padding: var(--spacing-2xl);
  gap: var(--spacing-l);
}

.f-card--interactive {
  cursor: pointer;
}

.f-card--interactive:hover {
  transform: translateY(var(--motion-hover-lift-strong));
  box-shadow: var(--shadow-card-hover), var(--halo-soft);
}

.f-card--interactive:active {
  box-shadow: var(--shadow-card);
  transform: translateY(0) scale(var(--motion-press-scale));
  transition-duration: var(--motion-duration-fast);
}

.f-card--interactive:focus-visible {
  outline: none;
  border-color: var(--color-border-focus);
  box-shadow: var(--shadow-card-hover), var(--shadow-focus);
}

@media (hover: none) {
  .f-card:hover {
    border-color: var(--color-border-subtle);
    box-shadow: var(--shadow-card);
  }

  .f-card--interactive:hover {
    transform: none;
    box-shadow: var(--shadow-card);
  }
}

.f-card--selected {
  border-color: var(--color-background-brand);
  box-shadow:
    var(--shadow-card),
    0 0 0 1px var(--color-background-brand),
    0 0 0 4px color-mix(in srgb, var(--color-background-brand) 14%, transparent);
}

.f-card--selected::after {
  opacity: 1;
  box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--color-background-brand) 28%, transparent);
}

/* 左侧 accent 指示条：4 px 圆头条，按语义着色。 */
.f-card[class*='f-card--accent-']::before {
  content: '';
  position: absolute;
  inset: var(--spacing-m) auto var(--spacing-m) 0;
  width: 3px;
  border-radius: var(--radius-circular);
  background: currentColor;
  opacity: 0.9;
}

.f-card--accent-brand::before {
  background: var(--color-background-brand);
}

.f-card--accent-success::before {
  background: var(--color-status-success-accent);
}

.f-card--accent-warning::before {
  background: var(--color-status-warning-accent);
}

.f-card--accent-danger::before {
  background: var(--color-status-error-accent);
}

.f-card__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--spacing-m);
}

.f-card__heading {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
  min-width: 0;
}

.f-card__eyebrow {
  margin: 0;
  font-size: var(--type-caption1-size);
  line-height: var(--type-caption1-line);
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--color-text-secondary);
}

.f-card__title {
  margin: 0;
  font-size: var(--type-title3-size);
  line-height: var(--type-title3-line);
  font-weight: 600;
  color: var(--color-text-primary);
}

.f-card__actions {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-s);
  flex-shrink: 0;
}

.f-card__body {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-m);
  min-width: 0;
}

.f-card__footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--spacing-s);
  margin-top: var(--spacing-s);
  padding-top: var(--spacing-m);
  border-top: 1px solid var(--color-border-subtle);
}
</style>
