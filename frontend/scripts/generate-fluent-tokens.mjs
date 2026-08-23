#!/usr/bin/env node
/*
 * Fluent 2 令牌静态化生成器（DESIGN.md §4.7.4 推荐的"方式二"）。
 *
 * 从 `@fluentui/tokens` 的 `webLightTheme` / `webDarkTheme` 读取全部 459 个键，
 * 输出 `frontend/src/styles/tokens.css`：
 *   - :root              写入全部 light 键（既包含主题相关也包含主题无关）；
 *   - :root[data-theme='dark']    仅覆盖在两套主题间值不同的颜色/阴影键；
 *   - @media (prefers-color-scheme: dark) :root:not([data-theme='light'])
 *     在用户未显式选 light 时跟随系统暗色偏好。
 *
 * 重新同步 Fluent 升级时只需 `pnpm run gen:fluent-tokens` 重跑一次。
 */
import pkg from '@fluentui/tokens';
const { webLightTheme, webDarkTheme } = pkg;
import { writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

/**
 * 把单个令牌 (键, 值) 渲染成 CSS 自定义属性行。
 * @param {string} key Fluent 令牌名（camelCase）
 * @param {string} value Fluent 令牌值（已是 CSS 字面量）
 * @return {string}
 */
function toCssDecl(key, value) {
  return `  --${key}: ${value};`;
}

const here = dirname(fileURLToPath(import.meta.url));
const outFile = resolve(here, '../src/styles/tokens.css');

const lightKeys = Object.keys(webLightTheme).sort();
const diffKeys = lightKeys.filter((k) => webLightTheme[k] !== webDarkTheme[k]);

const lightLines = lightKeys.map((k) => toCssDecl(k, webLightTheme[k]));
const darkLines = diffKeys.map((k) => toCssDecl(k, webDarkTheme[k]));

const header = `/*
 * Fluent 2 设计令牌（CSS 自定义属性）。
 *
 * 由 scripts/generate-fluent-tokens.mjs 从 @fluentui/tokens 自动生成，
 * 请勿手工编辑本文件——若要调整令牌值，升级 @fluentui/tokens 后重跑：
 *   pnpm run gen:fluent-tokens
 *
 * 组件样式只允许 var(--<token>) 引用本文件中的令牌，
 * 禁止裸色值 / 裸 px / 裸 font-size（DESIGN.md §8）。
 */
`;

const body = `${header}
:root {
  color-scheme: light;
${lightLines.join('\n')}
}

/* 用户显式选择暗色主题。 */
:root[data-theme='dark'] {
  color-scheme: dark;
${darkLines.join('\n')}
}

/* 未显式选择主题时跟随系统暗色偏好。 */
@media (prefers-color-scheme: dark) {
  :root:not([data-theme='light']) {
    color-scheme: dark;
${darkLines.map((line) => `  ${line}`).join('\n')}
  }
}
`;

writeFileSync(outFile, body, { encoding: 'utf8' });
const lf2crlf = body.replace(/\r?\n/g, '\r\n');
writeFileSync(outFile, lf2crlf, { encoding: 'utf8' });
console.log(`[fluent-tokens] wrote ${lightKeys.length} light keys + ${diffKeys.length} dark overrides → ${outFile}`);
