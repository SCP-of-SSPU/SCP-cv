/*
 * 主题切换 composable（DESIGN.md §4.3 + §14.2）。
 *   - 三态：system（跟随系统 prefers-color-scheme）/ light / dark；
 *   - 通过 <html data-theme> 属性驱动 tokens.css 的 M3 暗色覆盖；
 *   - 用户选择持久化到 localStorage，刷新后保留；
 *   - system 时移除 data-theme，交还给媒体查询，使暗色成为一等公民（C3）。
 */
import { ref, watchEffect, type Ref } from 'vue';

export type ThemeMode = 'system' | 'light' | 'dark';

const STORAGE_KEY = 'scp-cv-theme';

function readInitialMode(): ThemeMode {
  if (typeof localStorage === 'undefined') return 'system';
  const stored = localStorage.getItem(STORAGE_KEY);
  return stored === 'light' || stored === 'dark' || stored === 'system' ? stored : 'system';
}

// 模块级单例，确保设置页与外壳共享同一份主题状态。
const mode = ref<ThemeMode>(readInitialMode());

/**
 * 返回主题状态与切换方法；首次调用会建立 data-theme 同步副作用。
 * @return mode 当前主题模式（响应式，可写）
 */
export function useTheme(): { mode: Ref<ThemeMode> } {
  watchEffect(() => {
    if (typeof document === 'undefined') return;
    const root = document.documentElement;
    if (mode.value === 'system') {
      root.removeAttribute('data-theme');
    } else {
      root.setAttribute('data-theme', mode.value);
    }
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem(STORAGE_KEY, mode.value);
    }
  });
  return { mode };
}
