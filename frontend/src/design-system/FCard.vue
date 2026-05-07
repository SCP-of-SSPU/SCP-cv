<script setup lang="ts">
/**
 * 通用卡片容器：默认无阴影，靠 `border.subtle` 区分；hover 可以提升到 shadow.2。
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

interface FCardProps {
  /** 是否在 hover 时浮起一档；常用于「整张可点击」的预案卡。 */
  interactive?: boolean;
  /** 提供 padding 预设；compact 适用于嵌套卡片或紧凑列表项。 */
  padding?: 'none' | 'compact' | 'normal' | 'cozy';
  /** 直接选中态（如预案预览中的当前选中卡片）。 */
  selected?: boolean;
  /** 危险态（仅用于关键删除确认 / 错误兜底卡）。 */
  variant?: 'default' | 'subtle';
}

const props = withDefaults(defineProps<FCardProps>(), {
  interactive: false,
  padding: 'normal',
  selected: false,
  variant: 'default',
});

const rootClass = computed(() =>
  cls(
    'f-card',
    `f-card--${props.variant}`,
    `f-card--pad-${props.padding}`,
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
  display: flex;
  flex-direction: column;
  background: var(--color-background-card);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-large);
  color: var(--color-text-primary);
  /*
   * 加入 transform 过渡目标，让 interactive 变体在 hover 时可以轻微上浮；
   * duration 提升到 medium(160ms) 避免视觉突兀。
   */
  transition:
    border-color var(--motion-duration-medium) var(--motion-curve-ease),
    box-shadow var(--motion-duration-medium) var(--motion-curve-ease),
    transform var(--motion-duration-medium) var(--motion-curve-ease);
}

.f-card--subtle {
  background: var(--color-background-subtle);
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
  border-color: var(--color-border-default);
  box-shadow: var(--shadow-8);
  /* 1 px 上浮让交互卡片在悬浮时形成清晰层次；移动端 @media 下还原以避免 touch 残留。 */
  transform: translateY(-1px);
}

@media (hover: none) {
  .f-card--interactive:hover {
    transform: none;
  }
}

.f-card--selected {
  border-color: var(--color-background-brand);
  box-shadow: 0 0 0 1px var(--color-background-brand);
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
  letter-spacing: 0.08em;
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
