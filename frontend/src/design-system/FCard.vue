<script setup lang="ts">
/**
 * 通用卡片容器：默认带轻量阴影；hover / focus-within 会提升层级。
 *
 * 设计稿 §5.6：
 *   - 容器层级：canvas → card → 嵌套 subtle；
 *   - 卡片整体可点击时（如预案卡），内部不再放独立点击目标，附属操作收到 ActionSheet。
 *
 * Slot：
 *   - eyebrow：可选，渲染为 12 px caption + uppercase tracking
 *   - title：可选，渲染为 type.title3
 *   - actions：可选，标题右侧操作区
 *   - default：卡片正文
 */
import { computed } from 'vue';

import { cls } from './utils';

type CardAccent = 'none' | 'brand' | 'success' | 'warning' | 'danger';

interface FCardProps {
  /** 是否在 hover 时浮起一档；常用于「整张可点击」的预案卡。 */
  interactive?: boolean;
  /** 提供 padding 预设；compact 适用于嵌套卡片或紧凑列表项。 */
  padding?: 'none' | 'compact' | 'normal' | 'cozy';
  /** 直接选中态（如预案预览中的当前选中卡片）。 */
  selected?: boolean;
  /** 视觉变体：default 卡片层；subtle 嵌套层；glass 半透明顶栏卡。 */
  variant?: 'default' | 'subtle' | 'glass';
  /**
   * 左侧 4 px 状态指示条，用于强调卡片语义。
   * 例如：brand=置顶 / success=正常运行 / warning=待恢复 / danger=异常。
   */
  accent?: CardAccent;
}

const props = withDefaults(defineProps<FCardProps>(), {
  interactive: false,
  padding: 'normal',
  selected: false,
  variant: 'default',
  accent: 'none',
});

const rootClass = computed(() =>
  cls(
    'f-card',
    `f-card--${props.variant}`,
    `f-card--pad-${props.padding}`,
    props.accent !== 'none' && `f-card--accent-${props.accent}`,
    props.interactive && 'f-card--interactive',
    props.selected && 'f-card--selected',
  ),
);
</script>

<template>
  <article :class="rootClass">
    <header v-if="$slots.eyebrow || $slots.title || $slots.actions" class="f-card__header">
      <div class="f-card__heading">
        <p v-if="$slots.eyebrow" class="f-card__eyebrow">
          <slot name="eyebrow" />
        </p>
        <h3 v-if="$slots.title" class="f-card__title">
          <slot name="title" />
        </h3>
      </div>
      <div v-if="$slots.actions" class="f-card__actions">
        <slot name="actions" />
      </div>
    </header>
    <div class="f-card__body">
      <slot />
    </div>
    <footer v-if="$slots.footer" class="f-card__footer">
      <slot name="footer" />
    </footer>
  </article>
</template>

<style scoped>
/*
 * Fluent 2 卡片（DESIGN.md §6.3）。
 *   表面    --colorNeutralBackground1
 *   圆角    --borderRadiusLarge（6 px）
 *   内边距  --spacingHorizontalL（16 px）
 *   阴影    默认 --shadow4，hover 升至 --shadow8
 *   过渡    --durationFast + --curveEasyEase
 */
.f-card {
  position: relative;
  display: flex;
  flex-direction: column;
  background: var(--colorNeutralBackground1);
  border: var(--strokeWidthThin) solid var(--colorNeutralStroke2);
  border-radius: var(--borderRadiusLarge);
  color: var(--colorNeutralForeground1);
  box-shadow: var(--shadow4);
  overflow: clip;
  animation: f-rise var(--durationFast) var(--curveDecelerateMid) both;
  transition:
    border-color var(--durationFaster) var(--curveEasyEase),
    background-color var(--durationFaster) var(--curveEasyEase),
    box-shadow var(--durationFast) var(--curveEasyEase),
    transform var(--durationFast) var(--curveEasyEase);
}

.f-card:hover,
.f-card:focus-within {
  border-color: var(--colorNeutralStroke1);
  box-shadow: var(--shadow8);
}

.f-card--subtle {
  background: var(--colorNeutralBackground2);
  box-shadow: var(--shadow2);
}

.f-card--glass {
  background: var(--colorNeutralBackgroundAlpha);
  -webkit-backdrop-filter: blur(18px);
  backdrop-filter: blur(18px);
  border-color: var(--colorNeutralStrokeSubtle);
  box-shadow: var(--shadow4);
}

.f-card--pad-none {
  padding: 0;
}

.f-card--pad-compact {
  padding: var(--spacingHorizontalM);
  gap: var(--spacingHorizontalM);
}

.f-card--pad-normal {
  padding: var(--spacingHorizontalL);
  gap: var(--spacingHorizontalM);
}

.f-card--pad-cozy {
  padding: var(--spacingHorizontalXXL);
  gap: var(--spacingHorizontalL);
}

.f-card--interactive {
  cursor: pointer;
}

.f-card--interactive:hover {
  box-shadow: var(--shadow8);
}

.f-card--interactive:active {
  box-shadow: var(--shadow2);
  transition-duration: var(--durationUltraFast);
}

.f-card--interactive:focus-visible {
  outline: var(--strokeWidthThick) solid var(--colorBrandStroke1);
  outline-offset: 1px;
  border-color: var(--colorBrandStroke1);
}

@media (hover: none) {
  .f-card:hover {
    border-color: var(--colorNeutralStroke2);
    box-shadow: var(--shadow4);
  }
}

.f-card--selected {
  border-color: var(--colorBrandStroke1);
  box-shadow:
    var(--shadow4),
    0 0 0 var(--strokeWidthThin) var(--colorBrandStroke1);
}

/* 左侧 accent 指示条：3 px 圆头条，按语义着色。 */
.f-card[class*='f-card--accent-']::before {
  content: '';
  position: absolute;
  inset: var(--spacingVerticalM) auto var(--spacingVerticalM) 0;
  width: 3px;
  border-radius: var(--borderRadiusCircular);
  background: currentColor;
  opacity: 0.9;
}

.f-card--accent-brand::before {
  background: var(--colorBrandBackground);
}

.f-card--accent-success::before {
  background: var(--colorStatusSuccessBorder1);
}

.f-card--accent-warning::before {
  background: var(--colorStatusWarningBorder1);
}

.f-card--accent-danger::before {
  background: var(--colorStatusDangerBorder1);
}

.f-card__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--spacingHorizontalM);
}

.f-card__heading {
  display: flex;
  flex-direction: column;
  gap: var(--spacingVerticalXS);
  min-width: 0;
}

.f-card__eyebrow {
  margin: 0;
  font-size: var(--fontSizeBase200);
  line-height: var(--lineHeightBase200);
  font-weight: var(--fontWeightSemibold);
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--colorNeutralForeground2);
}

.f-card__title {
  margin: 0;
  font-size: var(--fontSizeBase400);
  line-height: var(--lineHeightBase400);
  font-weight: var(--fontWeightSemibold);
  color: var(--colorNeutralForeground1);
}

.f-card__actions {
  display: inline-flex;
  align-items: center;
  gap: var(--spacingHorizontalS);
  flex-shrink: 0;
}

.f-card__body {
  display: flex;
  flex-direction: column;
  gap: var(--spacingVerticalM);
  min-width: 0;
}

.f-card__footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--spacingHorizontalS);
  margin-top: var(--spacingVerticalS);
  padding-top: var(--spacingVerticalM);
  border-top: var(--strokeWidthThin) solid var(--colorNeutralStroke2);
}
</style>
