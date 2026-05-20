<script setup lang="ts">
/**
 * Spinner 圆环加载指示器，使用纯 CSS 实现（避免引入额外 SVG 资源）。
 * 仅在 300 ms – 1 s 区间使用；> 1 s 改用 Skeleton。
 */
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';

interface FSpinnerProps {
  size?: number | string;
  ariaLabel?: string;
}

const props = withDefaults(defineProps<FSpinnerProps>(), {
  size: 20,
  ariaLabel: undefined,
});

const { t } = useI18n();
const inlineSize = computed(() => (typeof props.size === 'number' ? `${props.size}px` : props.size));
const label = computed(() => props.ariaLabel ?? t('ds.spinnerLoading'));
</script>

<template>
  <span
    class="f-spinner"
    role="status"
    :aria-label="label"
    :style="{ width: inlineSize, height: inlineSize, fontSize: inlineSize }"
  />
</template>

<style scoped>
.f-spinner {
  display: inline-block;
  border-radius: var(--radius-circular);
  border: 2px solid var(--color-border-default);
  border-top-color: var(--color-background-brand);
  animation: f-spinner-rotate 600ms linear infinite;
  vertical-align: middle;
}

@keyframes f-spinner-rotate {
  to {
    transform: rotate(360deg);
  }
}
</style>
