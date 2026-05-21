<script setup lang="ts">
/**
 * Material Symbols 图标组件（DESIGN.md §9 / §14.4）。
 * 渲染 `material-symbols-rounded` 字体连字；颜色继承 currentColor，
 * 尺寸用 font-size（图标本质是字体字形，可随文本缩放，IC2）。
 * 装饰性图标对 AT 隐藏（IC5）；非装饰用 role="img" + aria-label（IC4），
 * role=img 时屏幕阅读器忽略内部连字文本，仅念 aria-label。
 */
import { computed } from 'vue';

import { resolveSymbol, type FluentIconName } from './icons';

interface FIconProps {
  /** 图标名 token（自动翻译为 Material Symbols 连字）。 */
  name: FluentIconName | string;
  /** 显式像素尺寸；不传时随父元素 font-size。 */
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

const symbol = computed(() => resolveSymbol(props.name));
const fontSize = computed(() => {
  if (props.size === undefined) return undefined;
  return typeof props.size === 'number' ? `${props.size}px` : props.size;
});
const role = computed(() => (props.decorative ? undefined : 'img'));
const ariaHidden = computed(() => (props.decorative ? 'true' : undefined));
</script>

<template>
  <span
    class="f-icon material-symbols-rounded"
    :role="role"
    :aria-hidden="ariaHidden"
    :aria-label="ariaLabel"
    :style="fontSize ? { fontSize } : undefined"
    >{{ symbol }}</span>
</template>

<style scoped>
.f-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: inherit;
  /* 字体图标：尺寸即 font-size。默认 1.25em 随上下文文本缩放（IC2）。 */
  font-size: 1.25em;
  line-height: 1;
  font-weight: normal;
  font-style: normal;
  white-space: nowrap;
  /* Material Symbols 可变轴：圆角变体、常规字重、未填充。 */
  font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24;
  user-select: none;
}
</style>
