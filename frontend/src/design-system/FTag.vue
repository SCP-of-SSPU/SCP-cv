<script setup lang="ts">
/**
 * Tag / Chip / Badge：仅作展示，不承担筛选触发（设计稿 §5.7）。
 * 状态由 tone 决定：playing 用 success；loading 用 warning；error 用 error；
 * idle 用 neutral；info 用 info；pinned 用 brand。
 */
import { computed } from 'vue';

import FIcon from './FIcon.vue';
import type { FluentIconName } from './icons';
import type { TagTone } from './types';

interface FTagProps {
  tone?: TagTone;
  icon?: FluentIconName | string;
  /** 是否在左侧绘制状态点：用于 loading（动效）/ live 等场景。 */
  dot?: boolean;
  /** 紧凑模式：表格内、列表项内常用。 */
  size?: 'compact' | 'medium';
}

const props = withDefaults(defineProps<FTagProps>(), {
  tone: 'neutral',
  icon: undefined,
  dot: false,
  size: 'medium',
});

const rootClass = computed(() => [
  'f-tag',
  `f-tag--${props.tone}`,
  `f-tag--${props.size}`,
  props.dot && 'f-tag--with-dot',
]);
</script>

<template>
  <span :class="rootClass">
    <span v-if="dot" class="f-tag__dot" aria-hidden="true" />
    <FIcon v-if="icon && !dot" class="f-tag__icon" :name="icon" />
    <span class="f-tag__label">
      <slot />
    </span>
  </span>
</template>

<style scoped>
.f-tag {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-xs);
  padding: 2px var(--spacing-s);
  /* Pill 形状比方块徽章更接近 Fluent 2 badge 语义。 */
  border-radius: var(--radius-circular);
  font-size: var(--type-caption1-size);
  line-height: var(--type-caption1-line);
  font-weight: 600;
  white-space: nowrap;
  border: 1px solid transparent;
  animation: f-pop var(--motion-duration-medium) var(--motion-curve-spring) both;
}

.f-tag--compact {
  padding: 1px var(--spacing-xs);
  font-size: var(--type-caption2-size);
  line-height: var(--type-caption2-line);
}

.f-tag__icon {
  width: 12px;
  height: 12px;
}

.f-tag--neutral {
  color: var(--color-text-tertiary);
  background: var(--color-background-subtle);
}

.f-tag--subtle {
  color: var(--color-text-secondary);
  background: transparent;
  border-color: var(--color-border-default);
}

.f-tag--info {
  color: var(--color-status-info-foreground);
  background: var(--color-status-info-background);
}

.f-tag--success {
  color: var(--color-status-success-foreground);
  background: var(--color-status-success-background);
}

.f-tag--warning {
  color: var(--color-status-warning-foreground);
  background: var(--color-status-warning-background);
}

.f-tag--error {
  color: var(--color-status-error-foreground);
  background: var(--color-status-error-background);
}

.f-tag--brand {
  color: var(--color-text-inverse);
  background: var(--color-background-brand);
}

.f-tag__dot {
  width: 6px;
  height: 6px;
  border-radius: var(--radius-circular);
  background: currentColor;
  flex-shrink: 0;
}

.f-tag--warning .f-tag__dot {
  animation: f-tag-blink 1500ms var(--motion-curve-ease) infinite;
}

@keyframes f-tag-blink {

  0%,
  100% {
    opacity: 1;
  }

  50% {
    opacity: 0.45;
  }
}
</style>
