<script setup lang="ts">
/**
 * Skeleton 占位骨架。
 * 用于 > 1 s 加载场景，保留布局稳定避免内容跳动。
 */
import { computed } from 'vue';

interface FSkeletonProps {
  /** 视觉形状：text 行（默认）、box 矩形、circle 圆形。 */
  shape?: 'text' | 'box' | 'circle';
  /** 显式宽度，单位 px 或 100%；不传时自动撑满父级。 */
  width?: string | number;
  /** 显式高度，常用于 box / circle。 */
  height?: string | number;
  /** 是否启用脉冲动画（reduce-motion 自动收敛）。 */
  pulse?: boolean;
}

const props = withDefaults(defineProps<FSkeletonProps>(), {
  shape: 'text',
  width: undefined,
  height: undefined,
  pulse: true,
});

const dim = (val?: string | number): string | undefined => {
  if (val === undefined) return undefined;
  return typeof val === 'number' ? `${val}px` : val;
};

const style = computed(() => ({
  width: dim(props.width),
  height: dim(props.height),
}));
</script>

<template>
  <span
    class="f-skeleton"
    :class="[`f-skeleton--${shape}`, pulse && 'f-skeleton--pulse']"
    :style="style"
    aria-hidden="true"
  />
</template>

<style scoped>
.f-skeleton {
  display: inline-block;
  background: var(--color-background-subtle);
  border-radius: var(--radius-medium);
}

.f-skeleton--text {
  width: 100%;
  height: var(--type-body1-line);
}

.f-skeleton--box {
  width: 100%;
  height: 80px;
  border-radius: var(--radius-large);
}

.f-skeleton--circle {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-circular);
}

.f-skeleton--pulse {
  animation: f-skeleton-pulse 1500ms ease-in-out infinite;
}

@keyframes f-skeleton-pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.55;
  }
}
</style>
