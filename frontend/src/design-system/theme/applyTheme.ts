/*
 * Fluent 2 主题运行时注入工具（DESIGN.md §4.3）。
 *
 * 将 `@fluentui/tokens` 的 Theme 对象写入指定根元素的 CSS 自定义属性。
 * 默认情况下 tokens.css 已经把 Light/Dark 两套值静态写入根元素，本函数
 * 仅在以下场景被调用：
 *   - 运行时换品牌色（multi-tenant / OEM 主题）；
 *   - 单元测试需要临时切换主题对象；
 *   - 后续接入高对比度主题。
 *
 * 业务代码不应直接调用该函数——主题切换由 useTheme() 通过 data-theme 属性
 * 驱动 tokens.css 中已经定义好的 [data-theme='dark'] 覆盖块。
 */
import type { Theme } from '@fluentui/tokens';

/**
 * 把 Fluent 主题对象写入目标元素的 CSS 自定义属性。
 * @param theme  Fluent 主题对象（webLightTheme / webDarkTheme / 自定义）
 * @param target 目标元素，默认 :root
 * @return void
 */
export function applyFluentTheme(
  theme: Theme,
  target: HTMLElement | null = typeof document === 'undefined' ? null : document.documentElement,
): void {
  if (!target) return;
  for (const [name, value] of Object.entries(theme)) {
    target.style.setProperty(`--${name}`, String(value));
  }
}
