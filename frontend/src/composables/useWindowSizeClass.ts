/*
 * 窗口尺寸类 composable（DESIGN.md §2 设计原则: Scale 适配）。
 * 按视口宽度分类（非设备嗅探，RR1）：
 *   compact 0–599 / medium 600–839 / expanded 840–1199 /
 *   large 1200–1599 / extraLarge ≥ 1600。
 * 用原生 matchMedia 监听（与项目既有 useBreakpoint 一致，不引入新依赖）。
 */
import { computed, onMounted, onUnmounted, ref, type ComputedRef, type Ref } from 'vue';

export type WindowSizeClass =
  | 'compact'
  | 'medium'
  | 'expanded'
  | 'large'
  | 'extraLarge';

const BREAKPOINTS = {
  medium: 600,
  expanded: 840,
  large: 1200,
  extraLarge: 1600,
} as const;

/**
 * 由宽度解析窗口尺寸类。
 * @param width 视口宽度（px）
 * @return WindowSizeClass
 */
function resolve(width: number): WindowSizeClass {
  if (width >= BREAKPOINTS.extraLarge) return 'extraLarge';
  if (width >= BREAKPOINTS.large) return 'large';
  if (width >= BREAKPOINTS.expanded) return 'expanded';
  if (width >= BREAKPOINTS.medium) return 'medium';
  return 'compact';
}

interface WindowSizeClassApi {
  /** 当前尺寸类（响应式）。 */
  sizeClass: Ref<WindowSizeClass>;
  /** Compact（手机 / 窄窗口）。 */
  isCompact: ComputedRef<boolean>;
  /** Medium 及以上（≥ 600，导航采用轨道/抽屉）。 */
  isMediumUp: ComputedRef<boolean>;
  /** Expanded 及以上（≥ 840，可并排 list-detail）。 */
  isExpandedUp: ComputedRef<boolean>;
  /** Large 及以上（≥ 1200，使用持久导航抽屉）。 */
  isLargeUp: ComputedRef<boolean>;
}

/**
 * 监听视口宽度，输出 Fluent 2 自适应窗口尺寸类与常用布尔派生量。
 * 浏览器环境下在 mount 时建立 resize 监听，卸载时清理。
 * @return WindowSizeClassApi
 */
export function useWindowSizeClass(): WindowSizeClassApi {
  const initialWidth = typeof window === 'undefined' ? 1280 : window.innerWidth;
  const sizeClass = ref<WindowSizeClass>(resolve(initialWidth));

  function sync(): void {
    sizeClass.value = resolve(window.innerWidth);
  }

  onMounted(() => {
    sync();
    window.addEventListener('resize', sync, { passive: true });
    window.addEventListener('orientationchange', sync);
  });

  onUnmounted(() => {
    window.removeEventListener('resize', sync);
    window.removeEventListener('orientationchange', sync);
  });

  const isCompact = computed(() => sizeClass.value === 'compact');
  const isMediumUp = computed(() => sizeClass.value !== 'compact');
  const isExpandedUp = computed(
    () => sizeClass.value === 'expanded' || sizeClass.value === 'large' || sizeClass.value === 'extraLarge',
  );
  const isLargeUp = computed(
    () => sizeClass.value === 'large' || sizeClass.value === 'extraLarge',
  );

  return { sizeClass, isCompact, isMediumUp, isExpandedUp, isLargeUp };
}
