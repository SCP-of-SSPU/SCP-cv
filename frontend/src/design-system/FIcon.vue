<script setup lang="ts">
/**
 * 通用 Fluent SVG 图标组件。
 * 使用 v-html 注入纯 SVG 字符串，并通过外部容器控制颜色（currentColor）与大小。
 * 如果给定 name 不存在，会渲染兜底空 SVG，避免布局抖动。
 */
import { computed } from 'vue';

import { getIconSvg, type FluentIconName } from './icons';

interface FIconProps {
  /** 已登记的 Fluent 图标名称。 */
  name: FluentIconName | string;
  /** 设定显式像素尺寸；不传时由父元素的 font-size 决定。 */
  size?: number | string;
  /** 装饰性图标，跳过屏幕阅读器；非装饰必须传 ariaLabel。 */
  decorative?: boolean;
  /** 屏幕阅读器可读名称；与 decorative 互斥。 */
  ariaLabel?: string;
}

const props = withDefaults(defineProps<FIconProps>(), {
  size: undefined,
  decorative: true,
  ariaLabel: undefined,
});

const svg = computed(() => getIconSvg(props.name));
const inlineSize = computed(() => {
  if (props.size === undefined) return undefined;
  return typeof props.size === 'number' ? `${props.size}px` : props.size;
});
const role = computed(() => (props.decorative ? undefined : 'img'));
const ariaHidden = computed(() => (props.decorative ? 'true' : undefined));
</script>

<template>
  <span
    class="f-icon"
    :role="role"
    :aria-hidden="ariaHidden"
    :aria-label="ariaLabel"
    :style="inlineSize ? { width: inlineSize, height: inlineSize } : undefined"
    v-html="svg"
  />
</template>

<style scoped>
.f-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1em;
  height: 1em;
  flex-shrink: 0;
  color: inherit;
  line-height: 0;
}

.f-icon :deep(svg) {
  width: 100%;
  height: 100%;
  fill: currentColor;
}
</style>
