<script setup lang="ts">
/**
 * Fluent 2 Tooltip：替代原生 title 属性，提供可控延迟、键盘可达、acrylic 浮层。
 *
 * 使用：
 *   <FTooltip content="导出当前页">
 *     <FButton icon-only icon-start="arrow_download_24_regular" aria-label="导出当前页" />
 *   </FTooltip>
 *
 * 设计约束（DESIGN.md §12.16 / Fluent 2 v9 Tooltip）：
 *   - 仅承载短提示（≤ 一行）；长内容用 Popover / Drawer；
 *   - 不替代可见 label；ariaLabel/visible label 仍为主要可访问名称；
 *   - hover 300 ms 后显示；离开立即隐藏；
 *   - 焦点驱动：键盘聚焦触发元素时立即显示，Esc 关闭；
 *   - Teleport 到 body，避开父级 overflow:hidden；
 *   - 视口边缘自动 flip（top ↔ bottom / left ↔ right）。
 */
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue';

interface FTooltipProps {
  /** 提示文本。空字符串时不渲染任何附加 DOM，保持调用方简洁。 */
  content: string;
  /** 触发后到显示的 hover 延迟；过短易误触，过长无法及时反馈。默认 300 ms。 */
  delay?: number;
  /** 期望浮层位置；窗口边缘空间不足时会自动翻到对侧。 */
  placement?: 'top' | 'right' | 'bottom' | 'left';
  /** 整个 Tooltip 禁用，触发元素正常工作但不显示提示。 */
  disabled?: boolean;
}

const props = withDefaults(defineProps<FTooltipProps>(), {
  delay: 300,
  placement: 'top',
  disabled: false,
});

/*
 * triggerEl 通过包裹 span 的 ref 获取首子节点；不直接侵入 slot 默认插槽布局，
 * 也不要求调用方在子组件上声明 ref。
 */
const wrapperEl = ref<HTMLElement | null>(null);
const tooltipEl = ref<HTMLElement | null>(null);
const visible = ref(false);
const finalPlacement = ref<FTooltipProps['placement']>(props.placement);
const tooltipStyle = ref<Record<string, string>>({});
let showTimer: number | null = null;

function clearShowTimer(): void {
  if (showTimer !== null) {
    window.clearTimeout(showTimer);
    showTimer = null;
  }
}

function scheduleShow(): void {
  if (props.disabled || !props.content) return;
  clearShowTimer();
  showTimer = window.setTimeout(() => {
    visible.value = true;
    void nextTick(updatePosition);
  }, props.delay);
}

function hide(): void {
  clearShowTimer();
  visible.value = false;
}

function onFocus(): void {
  if (props.disabled || !props.content) return;
  // 键盘焦点立即显示，不等 hover delay。
  visible.value = true;
  void nextTick(updatePosition);
}

function onKey(event: KeyboardEvent): void {
  if (event.key === 'Escape' && visible.value) {
    event.stopPropagation();
    hide();
  }
}

/*
 * 位置计算：
 *   1. 获取触发元素 rect 与浮层 rect；
 *   2. 按期望 placement 算出初始 top/left；
 *   3. 检查是否超出视口；超出则翻到对侧。
 * 不引入 Floating UI 之类的依赖，控制 bundle 体积。
 */
function updatePosition(): void {
  if (!wrapperEl.value || !tooltipEl.value) return;
  const triggerRect = wrapperEl.value.getBoundingClientRect();
  const tipRect = tooltipEl.value.getBoundingClientRect();
  const gap = 8;
  const margin = 8;
  let placement = props.placement;

  // 边缘可用空间：用于决定是否翻面。
  if (placement === 'top' && triggerRect.top - tipRect.height - gap < margin) placement = 'bottom';
  else if (placement === 'bottom' && triggerRect.bottom + tipRect.height + gap > window.innerHeight - margin) placement = 'top';
  else if (placement === 'left' && triggerRect.left - tipRect.width - gap < margin) placement = 'right';
  else if (placement === 'right' && triggerRect.right + tipRect.width + gap > window.innerWidth - margin) placement = 'left';

  finalPlacement.value = placement;

  let top = 0;
  let left = 0;
  switch (placement) {
    case 'top':
      top = triggerRect.top - tipRect.height - gap;
      left = triggerRect.left + (triggerRect.width - tipRect.width) / 2;
      break;
    case 'bottom':
      top = triggerRect.bottom + gap;
      left = triggerRect.left + (triggerRect.width - tipRect.width) / 2;
      break;
    case 'left':
      top = triggerRect.top + (triggerRect.height - tipRect.height) / 2;
      left = triggerRect.left - tipRect.width - gap;
      break;
    case 'right':
      top = triggerRect.top + (triggerRect.height - tipRect.height) / 2;
      left = triggerRect.right + gap;
      break;
  }

  // 防止溢出左右边缘：钳制到视口边界。
  left = Math.max(margin, Math.min(left, window.innerWidth - tipRect.width - margin));
  top = Math.max(margin, Math.min(top, window.innerHeight - tipRect.height - margin));

  tooltipStyle.value = {
    top: `${Math.round(top)}px`,
    left: `${Math.round(left)}px`,
  };
}

watch(visible, (value) => {
  if (value) {
    // 滚动 / 缩放期间动态重排，避免浮层"脱离"触发器。
    window.addEventListener('scroll', updatePosition, { passive: true, capture: true });
    window.addEventListener('resize', updatePosition);
  } else {
    window.removeEventListener('scroll', updatePosition, { capture: true } as EventListenerOptions);
    window.removeEventListener('resize', updatePosition);
  }
});

onBeforeUnmount(() => {
  clearShowTimer();
  window.removeEventListener('scroll', updatePosition, { capture: true } as EventListenerOptions);
  window.removeEventListener('resize', updatePosition);
});

const tooltipId = computed(() => `f-tooltip-${(Math.random() * 1e9) | 0}`);
</script>

<template>
  <span ref="wrapperEl" class="f-tooltip-wrap" @mouseenter="scheduleShow" @mouseleave="hide" @focusin="onFocus"
    @focusout="hide" @keydown="onKey" :aria-describedby="visible ? tooltipId : undefined">
    <slot />
    <Teleport to="body">
      <Transition name="f-tooltip">
        <span v-if="visible && content && !disabled" :id="tooltipId" ref="tooltipEl" class="f-tooltip" role="tooltip"
          :data-placement="finalPlacement" :style="tooltipStyle">
          {{ content }}
        </span>
      </Transition>
    </Teleport>
  </span>
</template>

<style scoped>
.f-tooltip-wrap {
  /* 透明包裹元素：不破坏 inline-flex / inline-block 布局，仅承载事件。 */
  display: contents;
}

.f-tooltip {
  position: fixed;
  z-index: var(--z-popover);
  max-width: 280px;
  padding: var(--spacing-xs) var(--spacing-snudge);
  border-radius: var(--radius-medium);
  /* Acrylic 浮层：与 FMenu / FToast 一致，避免视觉风格分裂。 */
  background: var(--color-background-glass-strong);
  color: var(--color-text-primary);
  border: var(--stroke-width-thin) solid color-mix(in srgb, var(--color-border-subtle) 70%, transparent);
  box-shadow: var(--shadow-flyout);
  font-size: var(--type-caption1-size);
  line-height: var(--type-caption1-line);
  font-weight: var(--font-weight-medium);
  white-space: normal;
  word-break: break-word;
  pointer-events: none;
  -webkit-backdrop-filter: blur(20px) saturate(1.15);
  backdrop-filter: blur(20px) saturate(1.15);
}

@supports not (backdrop-filter: blur(20px)) {
  .f-tooltip {
    background: var(--color-background-card);
  }
}

/*
 * 入场：根据最终 placement 决定 4 px 位移方向，让"从触发器伸出"的感觉更明确。
 * 离场用 ultra-fast，避免鼠标快速离开时 tooltip 残留遮挡内容。
 */
.f-tooltip-enter-active {
  transition: opacity var(--motion-duration-fast) var(--motion-curve-ease),
    transform var(--motion-duration-medium) var(--motion-curve-decelerate);
}

.f-tooltip-leave-active {
  transition: opacity var(--motion-duration-ultra-fast) var(--motion-curve-ease);
}

.f-tooltip-enter-from,
.f-tooltip-leave-to {
  opacity: 0;
}

.f-tooltip-enter-from[data-placement='top'] {
  transform: translateY(4px);
}

.f-tooltip-enter-from[data-placement='bottom'] {
  transform: translateY(-4px);
}

.f-tooltip-enter-from[data-placement='left'] {
  transform: translateX(4px);
}

.f-tooltip-enter-from[data-placement='right'] {
  transform: translateX(-4px);
}
</style>
