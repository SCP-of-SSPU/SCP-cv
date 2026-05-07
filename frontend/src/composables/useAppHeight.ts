/*
 * 为 iOS Safari 等浏览器的 100vh 问题写入 --app-height JS 变量。
 * 设计稿 §8 与 §7.2：底部 TabBar 不能被刘海/Home 横条遮挡。
 * 在 main.ts 入口或 layouts 顶层 onMounted 调用一次即可。
 */
const ROOT_VAR_NAME = '--app-height';

function applyHeight(): void {
  if (typeof document === 'undefined') return;
  // dvh 仍未在所有 webview 中支持，故同时写一份 px 兜底。
  const fallbackPx = `${window.innerHeight}px`;
  document.documentElement.style.setProperty(ROOT_VAR_NAME, fallbackPx);
}

/**
 * 注册 resize / orientationchange 监听器，确保 --app-height 跟随视口刷新。
 * @return Disposer 调用以解绑事件
 */
export function bindAppHeight(): () => void {
  if (typeof window === 'undefined') return () => undefined;
  applyHeight();
  window.addEventListener('resize', applyHeight, { passive: true });
  window.addEventListener('orientationchange', applyHeight);
  return () => {
    window.removeEventListener('resize', applyHeight);
    window.removeEventListener('orientationchange', applyHeight);
  };
}
