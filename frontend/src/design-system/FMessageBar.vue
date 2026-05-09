<script setup lang="ts">
/**
 * Message Bar：页面内上下文提示。
 * 设计稿 §5.12 + DESIGN.md §12.14：
 *   - 错误必须给出修复方式；
 *   - 可关闭后不影响完成任务；
 *   - 用于 SSE 断开（顶部）、上传失败（卡片底部）、设备 TCP 失败（电源卡底部）。
 */
import { computed } from 'vue';

import FButton from './FButton.vue';
import FIcon from './FIcon.vue';
import type { FluentIconName } from './icons';
import type { MessageTone } from './types';

interface FMessageBarProps {
  tone?: MessageTone;
  title?: string;
  /** 是否显示关闭按钮。 */
  dismissible?: boolean;
  /** 自定义图标，缺省按 tone 选用。 */
  icon?: FluentIconName | string;
}

const props = withDefaults(defineProps<FMessageBarProps>(), {
  tone: 'info',
  title: undefined,
  dismissible: false,
  icon: undefined,
});

const emit = defineEmits<{
  (event: 'dismiss'): void;
}>();

const toneIcon = computed<FluentIconName | string>(() => {
  if (props.icon) return props.icon;
  switch (props.tone) {
    case 'success':
      return 'checkmark_circle_24_filled';
    case 'warning':
      return 'warning_24_filled';
    case 'error':
      return 'error_circle_24_filled';
    default:
      return 'info_24_regular';
  }
});
</script>

<template>
  <div class="f-message-bar" :class="`f-message-bar--${tone}`" role="status"
    :aria-live="tone === 'error' ? 'assertive' : 'polite'">
    <FIcon class="f-message-bar__icon" :name="toneIcon" />
    <div class="f-message-bar__content">
      <p v-if="title" class="f-message-bar__title">{{ title }}</p>
      <p class="f-message-bar__body">
        <slot />
      </p>
    </div>
    <div v-if="$slots.actions || dismissible" class="f-message-bar__actions">
      <slot name="actions" />
      <FButton v-if="dismissible" appearance="transparent" size="compact" icon-only aria-label="关闭提示"
        :icon-start="'dismiss_20_regular'" @click="emit('dismiss')" />
    </div>
  </div>
</template>

<style scoped>
.f-message-bar {
  display: flex;
  align-items: flex-start;
  gap: var(--spacing-m);
  padding: var(--spacing-m) var(--spacing-l);
  border-radius: var(--radius-medium);
  border: 1px solid transparent;
  font-size: var(--type-body1-size);
  line-height: var(--type-body1-line);
  box-shadow: var(--shadow-control);
}

.f-message-bar__icon {
  flex-shrink: 0;
  width: 20px;
  height: 20px;
  margin-top: 2px;
}

.f-message-bar__content {
  flex: 1 1 auto;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
  min-width: 0;
}

.f-message-bar__title {
  margin: 0;
  font-weight: 600;
  color: inherit;
}

.f-message-bar__body {
  margin: 0;
  color: inherit;
}

.f-message-bar__actions {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-xs);
  flex-shrink: 0;
}

.f-message-bar--info {
  background: var(--color-status-info-background);
  color: var(--color-status-info-foreground);
  border-color: var(--color-status-info-foreground);
}

.f-message-bar--success {
  background: var(--color-status-success-background);
  color: var(--color-status-success-foreground);
  border-color: var(--color-status-success-foreground);
}

.f-message-bar--warning {
  background: var(--color-status-warning-background);
  color: var(--color-status-warning-foreground);
  border-color: var(--color-status-warning-foreground);
}

.f-message-bar--error {
  background: var(--color-status-error-background);
  color: var(--color-status-error-foreground);
  border-color: var(--color-status-error-foreground);
}
</style>
