/*
 * 响应式断点 composable。
 * 严格对齐 STYLE.md 响应式规范与 DESIGN.md §17.1：xs/sm/md/lg/xl/2xl。
 * 使用 matchMedia 监听，避免 resize 反复采样；销毁时自动清理监听。
 */
import { onMounted, onUnmounted, ref, computed } from 'vue';

import type { Ref } from 'vue';

/** 断点名称：与 DESIGN.md 一致的 6 档。 */
export type BreakpointName = 'xs' | 'sm' | 'md' | 'lg' | 'xl' | '2xl';

/** 断点上界（最小宽度阈值），单位 px。 */
const BREAKPOINT_MIN_WIDTH: Record<Exclude<BreakpointName, 'xs'>, number> = {
  sm: 480,
  md: 768,
  lg: 1024,
  xl: 1440,
  '2xl': 1920,
};

interface BreakpointApi {
  /** 当前断点名称（响应式）。 */
  current: Ref<BreakpointName>;
  /** 是否处于「移动端竖屏主形态」（xs / sm）。 */
  isMobile: Ref<boolean>;
  /** 是否处于「平板/小窗口」（md）。 */
  isTablet: Ref<boolean>;
  /** 是否处于桌面（≥ md）。 */
  isDesktop: Ref<boolean>;
  /** 是否处于桌面 lg 及以上（≥ 1024）。 */
  isWide: Ref<boolean>;
  /** 是否处于横屏。 */
  isLandscape: Ref<boolean>;
  /** PPT 专注模式可用性：≥ lg 且横屏。 */
  canUseFocusMode: Ref<boolean>;
}

/**
 * 计算给定窗口宽度对应的断点名称。
 * @param width 视口宽度，单位 px
 * @return BreakpointName
 */
function resolveBreakpoint(width: number): BreakpointName {
  if (width >= BREAKPOINT_MIN_WIDTH['2xl']) return '2xl';
  if (width >= BREAKPOINT_MIN_WIDTH.xl) return 'xl';
  if (width >= BREAKPOINT_MIN_WIDTH.lg) return 'lg';
  if (width >= BREAKPOINT_MIN_WIDTH.md) return 'md';
  if (width >= BREAKPOINT_MIN_WIDTH.sm) return 'sm';
  return 'xs';
}

/**
 * 监听视口宽度与方向，输出当前断点信息。
 * 该 composable 只在浏览器环境运行；SSR/单元测试可跳过 onMounted 分支。
 * @return BreakpointApi 一组只读响应式 ref
 */
export function useBreakpoint(): BreakpointApi {
  // 服务器渲染兜底：默认按桌面 lg 处理。
  const initialWidth = typeof window === 'undefined' ? 1440 : window.innerWidth;
  const current = ref<BreakpointName>(resolveBreakpoint(initialWidth));
  const isLandscape = ref<boolean>(
    typeof window === 'undefined' ? true : window.innerWidth >= window.innerHeight,
  );

  function syncFromWindow(): void {
    current.value = resolveBreakpoint(window.innerWidth);
    isLandscape.value = window.innerWidth >= window.innerHeight;
  }

  onMounted(() => {
    syncFromWindow();
    window.addEventListener('resize', syncFromWindow, { passive: true });
    window.addEventListener('orientationchange', syncFromWindow);
  });

  onUnmounted(() => {
    window.removeEventListener('resize', syncFromWindow);
    window.removeEventListener('orientationchange', syncFromWindow);
  });

  const isMobile = computed(() => current.value === 'xs' || current.value === 'sm');
  const isTablet = computed(() => current.value === 'md');
  const isDesktop = computed(() => !isMobile.value);
  const isWide = computed(() => current.value === 'lg' || current.value === 'xl' || current.value === '2xl');
  const canUseFocusMode = computed(() => isWide.value && isLandscape.value);

  return { current, isMobile, isTablet, isDesktop, isWide, isLandscape, canUseFocusMode };
}
