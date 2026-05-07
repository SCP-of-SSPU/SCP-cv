<script setup lang="ts">
/**
 * 进度条：用于上传进度、PPT 翻页进度。
 * 4 px 高、Brand 色填充，符合设计稿 §5.16。
 */
import { computed } from 'vue';

interface FProgressProps {
  value: number;
  /** 最大值，默认 100。 */
  max?: number;
  /** 在右侧显示百分比文本。 */
  showLabel?: boolean;
  /** indeterminate：未知进度的循环动画。 */
  indeterminate?: boolean;
}

const props = withDefaults(defineProps<FProgressProps>(), {
  max: 100,
  showLabel: false,
  indeterminate: false,
});

const percent = computed(() => {
  if (props.max <= 0) return 0;
  const clamped = Math.min(props.max, Math.max(0, props.value));
  return (clamped / props.max) * 100;
});
</script>

<template>
  <div class="f-progress" role="progressbar" :aria-valuenow="value" :aria-valuemax="max" aria-valuemin="0">
    <div class="f-progress__track">
      <div
        class="f-progress__bar"
        :class="{ 'f-progress__bar--indeterminate': indeterminate }"
        :style="indeterminate ? undefined : { width: `${percent}%` }"
      />
    </div>
    <span v-if="showLabel" class="f-progress__label">{{ percent.toFixed(0) }}%</span>
  </div>
</template>

<style scoped>
.f-progress {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-s);
  width: 100%;
}

.f-progress__track {
  flex: 1 1 auto;
  position: relative;
  width: 100%;
  height: 4px;
  background: var(--color-border-subtle);
  border-radius: var(--radius-circular);
  overflow: hidden;
}

.f-progress__bar {
  height: 100%;
  background: var(--color-background-brand);
  border-radius: var(--radius-circular);
  transition: width var(--motion-duration-normal) var(--motion-curve-ease);
}

.f-progress__bar--indeterminate {
  width: 35%;
  animation: f-progress-slide 1200ms var(--motion-curve-ease) infinite;
}

@keyframes f-progress-slide {
  0% {
    transform: translateX(-100%);
  }
  100% {
    transform: translateX(285%);
  }
}

.f-progress__label {
  font-size: var(--type-caption1-size);
  color: var(--color-text-secondary);
  font-variant-numeric: tabular-nums;
}
</style>
