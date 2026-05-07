/*
 * 监听用户系统偏好「减少动效」并暴露响应式标志，便于业务在 JS 中关掉
 * 那些 CSS 媒体查询无法管理的过渡（例如 setTimeout / requestAnimationFrame）。
 */
import { onMounted, onUnmounted, ref, type Ref } from 'vue';

/**
 * @return reduced 当前是否启用「减少动效」
 */
export function useReducedMotion(): { reduced: Ref<boolean> } {
  const reduced = ref<boolean>(false);
  let mediaQuery: MediaQueryList | null = null;

  function sync(): void {
    if (mediaQuery) reduced.value = mediaQuery.matches;
  }

  onMounted(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return;
    mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    sync();
    mediaQuery.addEventListener?.('change', sync);
  });

  onUnmounted(() => {
    mediaQuery?.removeEventListener?.('change', sync);
    mediaQuery = null;
  });

  return { reduced };
}
