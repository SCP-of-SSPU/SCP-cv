<script setup lang="ts">
/**
 * 空状态：「当前没什么 / 为什么没有 / 可以做什么」三要素。
 * DESIGN.md §13.3 / 设计稿 §6.3。
 */
import FIcon from './FIcon.vue';
import type { FluentIconName } from './icons';

interface FEmptyProps {
  /** 主图标，默认 alert 图标。 */
  icon?: FluentIconName | string;
  /** 主标题。 */
  title: string;
  /** 描述：解释为什么没有 + 可以做什么。 */
  description?: string;
}

withDefaults(defineProps<FEmptyProps>(), {
  icon: 'apps_list_24_regular',
  description: undefined,
});
</script>

<template>
  <div class="f-empty">
    <FIcon class="f-empty__icon" :name="icon" />
    <h3 class="f-empty__title">{{ title }}</h3>
    <p v-if="description" class="f-empty__description">{{ description }}</p>
    <div v-if="$slots.actions" class="f-empty__actions">
      <slot name="actions" />
    </div>
  </div>
</template>

<style scoped>
.f-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  gap: var(--spacing-m);
  padding: var(--spacing-3xl) var(--spacing-2xl);
  color: var(--color-text-primary);
}

.f-empty__icon {
  width: 48px;
  height: 48px;
  color: var(--color-text-tertiary);
  background: var(--color-background-subtle);
  border-radius: var(--radius-circular);
  padding: var(--spacing-m);
  box-sizing: content-box;
}

.f-empty__title {
  margin: 0;
  font-size: var(--type-title3-size);
  line-height: var(--type-title3-line);
  font-weight: 600;
}

.f-empty__description {
  margin: 0;
  max-width: 360px;
  color: var(--color-text-secondary);
}

.f-empty__actions {
  margin-top: var(--spacing-s);
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-s);
}
</style>
