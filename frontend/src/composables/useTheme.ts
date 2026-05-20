/*
 * 主题切换 composable（DESIGN.md §4.3 + §5）。
 *   - 三态：system（跟随 prefers-color-scheme）/ light / dark；
 *   - 通过 <html data-theme> 属性驱动 tokens.css 的 dark 覆盖块；
 *   - 用户选择持久化到 localStorage，刷新后保留；
 *   - system 时移除 data-theme，让 @media (prefers-color-scheme:dark) 接管；
 *   - 提供 override 通道供 PPT 专注页等场景临时锁定主题：
 *     override 期间 data-theme 由 override 决定，不写入 localStorage，
 *     pop 后立刻回到用户偏好。
 */
import { computed, ref, watchEffect, type ComputedRef, type Ref } from 'vue';

export type ThemeMode = 'system' | 'light' | 'dark';

const STORAGE_KEY = 'scp-cv-theme';

/**
 * 读取持久化的初始主题模式。
 * @return 用户上次选择的模式，未设置时回退到 system
 */
function readInitialMode(): ThemeMode {
  if (typeof localStorage === 'undefined') return 'system';
  const stored = localStorage.getItem(STORAGE_KEY);
  return stored === 'light' || stored === 'dark' || stored === 'system' ? stored : 'system';
}

// 模块级单例，确保所有调用者共享一份状态。
const mode = ref<ThemeMode>(readInitialMode());
const override = ref<ThemeMode | null>(null);
const effectiveMode = computed<ThemeMode>(() => override.value ?? mode.value);

// 仅初始化一次的全局副作用：data-theme 与 localStorage 同步。
let installed = false;
function installEffect(): void {
  if (installed || typeof document === 'undefined') return;
  installed = true;
  watchEffect(() => {
    const root = document.documentElement;
    if (effectiveMode.value === 'system') {
      root.removeAttribute('data-theme');
    } else {
      root.setAttribute('data-theme', effectiveMode.value);
    }
  });
  watchEffect(() => {
    // 仅用户偏好写入持久化，override 期间不污染存储。
    if (typeof localStorage === 'undefined') return;
    localStorage.setItem(STORAGE_KEY, mode.value);
  });
}

interface UseThemeApi {
  /** 用户主题偏好（响应式，可写）。 */
  mode: Ref<ThemeMode>;
  /** 当前实际生效的主题（mode 与 override 的合成）。 */
  effective: ComputedRef<ThemeMode>;
  /**
   * 临时锁定主题（如进入 PPT 专注页）。
   * 不写 localStorage，调用 popOverride 后立刻恢复用户偏好。
   * @param next 要临时生效的主题
   */
  pushOverride: (next: ThemeMode) => void;
  /** 解除临时主题锁定。 */
  popOverride: () => void;
}

/**
 * 返回主题状态与切换方法；首次调用安装 data-theme 与 localStorage 副作用。
 * @return UseThemeApi
 */
export function useTheme(): UseThemeApi {
  installEffect();
  function pushOverride(next: ThemeMode): void {
    override.value = next;
  }
  function popOverride(): void {
    override.value = null;
  }
  return { mode, effective: effectiveMode, pushOverride, popOverride };
}
