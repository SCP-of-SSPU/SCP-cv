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
  <span class="f-skeleton" :class="[`f-skeleton--${shape}`, pulse && 'f-skeleton--pulse']" :style="style"
    aria-hidden="true" />
</template>

<style scoped>
/*
 * 骨架基色用 `--color-background-subtle`，pulse 模式下叠加从左到右的高光带 shimmer 效果。
 * 高光带颜色经 `--gradient-skeleton` 统一管理，深色 / 浅色主题下都能自然适配。
 */
.f-skeleton {
  display: inline-block;
  position: relative;
  overflow: hidden;
  background: var(--color-background-subtle);
  border-radius: var(--radius-medium);
  /* 默认 0.85 透明度模拟"半透明态"，避免与正式内容混淆。 */
  opacity: 0.92;
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

.f-skeleton--pulse::after {
  content: '';
  position: absolute;
  inset: 0;
  background: var(--gradient-skeleton);
  transform: translateX(-100%);
  animation: f-shimmer 1500ms var(--motion-curve-linear) infinite;
}
</style>
