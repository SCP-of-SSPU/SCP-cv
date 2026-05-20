#!/usr/bin/env node
/*
 * 把项目历史上 Material 3 / 自定义命名的设计令牌一次性迁移到 Fluent 2。
 *
 * 仅作语义同义替换，不修改 HTML 结构、不调整组件布局；
 * 结构性的设计差异（如按钮形状从药丸改为 4px 圆角）由人工在
 * 关键组件中重写。脚本是幂等的：再跑一次也不会破坏已经迁移过的代码。
 *
 * 用法：
 *   node scripts/migrate-m3-tokens.mjs               # 全量迁移
 *   node scripts/migrate-m3-tokens.mjs --dry-run     # 只打印差异
 *   node scripts/migrate-m3-tokens.mjs src/foo.vue   # 仅迁移指定文件
 */
import { readFileSync, writeFileSync, statSync, readdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, extname, join, relative, resolve } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const projectRoot = resolve(here, '..');

const args = process.argv.slice(2);
const dryRun = args.includes('--dry-run');
const explicitTargets = args.filter((a) => !a.startsWith('--'));

const TARGET_EXTS = new Set(['.vue', '.css', '.ts', '.tsx', '.js']);

/**
 * 按先长后短排序的替换映射；每条 [pattern, replacement]。
 * 留意：键越长越优先匹配，避免被前缀更短的规则截胡。
 * @type {Array<[string, string]>}
 */
const MAPPINGS = [
  // ── 颜色：on-* container ────────────────────────────────────────────────
  ['--md-sys-color-on-primary-container', '--colorBrandForeground1'],
  ['--md-sys-color-on-secondary-container', '--colorNeutralForeground1'],
  ['--md-sys-color-on-tertiary-container', '--colorBrandForeground1'],
  ['--md-sys-color-on-error-container', '--colorStatusDangerForeground1'],
  ['--md-sys-color-on-success-container', '--colorStatusSuccessForeground1'],
  ['--md-sys-color-on-warning-container', '--colorStatusWarningForeground1'],
  // 容器色
  ['--md-sys-color-primary-container', '--colorBrandBackground2'],
  ['--md-sys-color-secondary-container', '--colorNeutralBackground3'],
  ['--md-sys-color-tertiary-container', '--colorBrandBackground2'],
  ['--md-sys-color-error-container', '--colorStatusDangerBackground1'],
  ['--md-sys-color-success-container', '--colorStatusSuccessBackground1'],
  ['--md-sys-color-warning-container', '--colorStatusWarningBackground1'],
  // on-* 单色
  ['--md-sys-color-on-primary', '--colorNeutralForegroundOnBrand'],
  ['--md-sys-color-on-secondary', '--colorNeutralForegroundOnBrand'],
  ['--md-sys-color-on-tertiary', '--colorNeutralForegroundOnBrand'],
  ['--md-sys-color-on-error', '--colorNeutralForegroundOnBrand'],
  ['--md-sys-color-on-success', '--colorNeutralForegroundOnBrand'],
  ['--md-sys-color-on-warning', '--colorNeutralForegroundOnBrand'],
  ['--md-sys-color-on-surface-variant', '--colorNeutralForeground2'],
  ['--md-sys-color-on-surface', '--colorNeutralForeground1'],
  // surface 系列
  ['--md-sys-color-surface-container-lowest', '--colorNeutralBackground1'],
  ['--md-sys-color-surface-container-highest', '--colorNeutralBackground5'],
  ['--md-sys-color-surface-container-high', '--colorNeutralBackground4'],
  ['--md-sys-color-surface-container-low', '--colorNeutralBackground2'],
  ['--md-sys-color-surface-container', '--colorNeutralBackground3'],
  ['--md-sys-color-surface-variant', '--colorNeutralBackground2'],
  ['--md-sys-color-surface-bright', '--colorNeutralBackground1'],
  ['--md-sys-color-surface-dim', '--colorNeutralBackground3'],
  ['--md-sys-color-surface-tint', '--colorBrandBackground'],
  ['--md-sys-color-surface', '--colorNeutralBackground1'],
  // outline & inverse
  ['--md-sys-color-outline-variant', '--colorNeutralStroke2'],
  ['--md-sys-color-outline', '--colorNeutralStroke1'],
  ['--md-sys-color-inverse-on-surface', '--colorNeutralForegroundInverted'],
  ['--md-sys-color-inverse-surface', '--colorNeutralBackgroundInverted'],
  ['--md-sys-color-inverse-primary', '--colorBrandForegroundInverted'],
  // 单色：primary / secondary / tertiary / error / success / warning
  ['--md-sys-color-primary', '--colorBrandBackground'],
  ['--md-sys-color-secondary', '--colorNeutralForeground2'],
  ['--md-sys-color-tertiary', '--colorBrandForeground2'],
  ['--md-sys-color-error', '--colorStatusDangerForeground1'],
  ['--md-sys-color-success', '--colorStatusSuccessForeground1'],
  ['--md-sys-color-warning', '--colorStatusWarningForeground1'],
  ['--md-sys-color-scrim', '--colorBackgroundOverlay'],
  ['--md-sys-color-shadow', '--colorBackgroundOverlay'],

  // ── 字阶（先匹配带后缀 -size/-line-height/-weight，再处理裸键） ──────────
  // display
  ['--md-sys-typescale-display-large-line-height', '--lineHeightHero1000'],
  ['--md-sys-typescale-display-medium-line-height', '--lineHeightHero900'],
  ['--md-sys-typescale-display-small-line-height', '--lineHeightHero800'],
  ['--md-sys-typescale-display-large-size', '--fontSizeHero1000'],
  ['--md-sys-typescale-display-medium-size', '--fontSizeHero900'],
  ['--md-sys-typescale-display-small-size', '--fontSizeHero800'],
  ['--md-sys-typescale-display-large-weight', '--fontWeightSemibold'],
  ['--md-sys-typescale-display-medium-weight', '--fontWeightSemibold'],
  ['--md-sys-typescale-display-small-weight', '--fontWeightSemibold'],
  // headline
  ['--md-sys-typescale-headline-large-line-height', '--lineHeightHero800'],
  ['--md-sys-typescale-headline-medium-line-height', '--lineHeightHero700'],
  ['--md-sys-typescale-headline-small-line-height', '--lineHeightBase600'],
  ['--md-sys-typescale-headline-large-size', '--fontSizeHero800'],
  ['--md-sys-typescale-headline-medium-size', '--fontSizeHero700'],
  ['--md-sys-typescale-headline-small-size', '--fontSizeBase600'],
  ['--md-sys-typescale-headline-large-weight', '--fontWeightSemibold'],
  ['--md-sys-typescale-headline-medium-weight', '--fontWeightSemibold'],
  ['--md-sys-typescale-headline-small-weight', '--fontWeightSemibold'],
  // title
  ['--md-sys-typescale-title-large-line-height', '--lineHeightBase500'],
  ['--md-sys-typescale-title-medium-line-height', '--lineHeightBase400'],
  ['--md-sys-typescale-title-small-line-height', '--lineHeightBase300'],
  ['--md-sys-typescale-title-large-size', '--fontSizeBase500'],
  ['--md-sys-typescale-title-medium-size', '--fontSizeBase400'],
  ['--md-sys-typescale-title-small-size', '--fontSizeBase300'],
  ['--md-sys-typescale-title-large-weight', '--fontWeightSemibold'],
  ['--md-sys-typescale-title-medium-weight', '--fontWeightSemibold'],
  ['--md-sys-typescale-title-small-weight', '--fontWeightSemibold'],
  // body
  ['--md-sys-typescale-body-large-line-height', '--lineHeightBase400'],
  ['--md-sys-typescale-body-medium-line-height', '--lineHeightBase300'],
  ['--md-sys-typescale-body-small-line-height', '--lineHeightBase200'],
  ['--md-sys-typescale-body-large-size', '--fontSizeBase400'],
  ['--md-sys-typescale-body-medium-size', '--fontSizeBase300'],
  ['--md-sys-typescale-body-small-size', '--fontSizeBase200'],
  ['--md-sys-typescale-body-large-weight', '--fontWeightRegular'],
  ['--md-sys-typescale-body-medium-weight', '--fontWeightRegular'],
  ['--md-sys-typescale-body-small-weight', '--fontWeightRegular'],
  // label
  ['--md-sys-typescale-label-large-line-height', '--lineHeightBase300'],
  ['--md-sys-typescale-label-medium-line-height', '--lineHeightBase200'],
  ['--md-sys-typescale-label-small-line-height', '--lineHeightBase100'],
  ['--md-sys-typescale-label-large-size', '--fontSizeBase300'],
  ['--md-sys-typescale-label-medium-size', '--fontSizeBase200'],
  ['--md-sys-typescale-label-small-size', '--fontSizeBase100'],
  ['--md-sys-typescale-label-large-weight', '--fontWeightSemibold'],
  ['--md-sys-typescale-label-medium-weight', '--fontWeightSemibold'],
  ['--md-sys-typescale-label-small-weight', '--fontWeightSemibold'],
  // font family
  ['--md-sys-typescale-font-mono', '--fontFamilyMonospace'],
  ['--md-sys-typescale-font', '--fontFamilyBase'],

  // ── 形状 ───────────────────────────────────────────────────────────────
  ['--md-sys-shape-corner-extra-small', '--borderRadiusMedium'],
  ['--md-sys-shape-corner-extra-large', '--borderRadius4XLarge'],
  ['--md-sys-shape-corner-small', '--borderRadiusXLarge'],
  ['--md-sys-shape-corner-medium', '--borderRadius2XLarge'],
  ['--md-sys-shape-corner-large', '--borderRadius3XLarge'],
  ['--md-sys-shape-corner-full', '--borderRadiusCircular'],
  ['--md-sys-shape-corner-none', '--borderRadiusNone'],

  // ── 阴影 ───────────────────────────────────────────────────────────────
  ['--md-sys-elevation-0', '--shadow2'], // 兜底，避免出现裸 none
  ['--md-sys-elevation-1', '--shadow2'],
  ['--md-sys-elevation-2', '--shadow4'],
  ['--md-sys-elevation-3', '--shadow8'],
  ['--md-sys-elevation-4', '--shadow16'],
  ['--md-sys-elevation-5', '--shadow28'],

  // ── 动效 ───────────────────────────────────────────────────────────────
  ['--md-sys-motion-easing-emphasized-decelerate', '--curveDecelerateMid'],
  ['--md-sys-motion-easing-emphasized-accelerate', '--curveAccelerateMid'],
  ['--md-sys-motion-easing-emphasized', '--curveEasyEase'],
  ['--md-sys-motion-easing-standard-decelerate', '--curveDecelerateMid'],
  ['--md-sys-motion-easing-standard-accelerate', '--curveAccelerateMid'],
  ['--md-sys-motion-easing-standard', '--curveEasyEase'],
  ['--md-sys-motion-duration-extra-long', '--durationUltraSlow'],
  ['--md-sys-motion-duration-short1', '--durationUltraFast'],
  ['--md-sys-motion-duration-short2', '--durationFaster'],
  ['--md-sys-motion-duration-medium1', '--durationNormal'],
  ['--md-sys-motion-duration-short', '--durationFast'],
  ['--md-sys-motion-duration-medium', '--durationSlow'],
  ['--md-sys-motion-duration-long', '--durationSlower'],

  // ── 状态层（保持为不透明度数值供 color-mix 使用，统一改名） ─────────────
  ['--md-sys-state-hover-opacity', '--f-state-hover-opacity'],
  ['--md-sys-state-focus-opacity', '--f-state-focus-opacity'],
  ['--md-sys-state-pressed-opacity', '--f-state-pressed-opacity'],
  ['--md-sys-state-dragged-opacity', '--f-state-dragged-opacity'],

  // ── 项目自定义旧别名 ───────────────────────────────────────────────────
  ['--color-background-canvas', '--colorNeutralBackgroundCanvas'],
  ['--color-background-elevated', '--colorNeutralBackground1'],
  ['--color-background-elevated-2', '--colorNeutralBackground2'],
  ['--color-background-elevated-3', '--colorNeutralBackground3'],
  ['--color-background-subtle', '--colorNeutralBackground2'],
  ['--color-background-brand-selected', '--colorBrandBackgroundSelected'],
  ['--color-background-brand-hover', '--colorBrandBackgroundHover'],
  ['--color-background-brand', '--colorBrandBackground'],
  ['--color-background-inverted', '--colorNeutralBackgroundInverted'],
  ['--color-background-overlay', '--colorBackgroundOverlay'],
  ['--color-text-primary', '--colorNeutralForeground1'],
  ['--color-text-secondary', '--colorNeutralForeground2'],
  ['--color-text-tertiary', '--colorNeutralForeground3'],
  ['--color-text-disabled', '--colorNeutralForegroundDisabled'],
  ['--color-text-on-brand', '--colorNeutralForegroundOnBrand'],
  ['--color-text-on-inverted', '--colorNeutralForegroundInverted'],
  ['--color-text-brand', '--colorBrandForeground1'],
  ['--color-text-brand-hover', '--colorBrandForeground2Hover'],
  ['--color-text-success', '--colorStatusSuccessForeground1'],
  ['--color-text-danger', '--colorStatusDangerForeground1'],
  ['--color-text-warning', '--colorStatusWarningForeground1'],
  ['--color-border-default', '--colorNeutralStroke1'],
  ['--color-border-strong', '--colorNeutralStroke1Hover'],
  ['--color-border-subtle', '--colorNeutralStroke2'],
  ['--color-border-focus', '--colorBrandStroke1'],
  ['--color-border-brand', '--colorBrandStroke1'],
  ['--color-border-danger', '--colorStatusDangerBorder1'],
  ['--color-state-success-bg', '--colorStatusSuccessBackground1'],
  ['--color-state-success-fg', '--colorStatusSuccessForeground1'],
  ['--color-state-warning-bg', '--colorStatusWarningBackground1'],
  ['--color-state-warning-fg', '--colorStatusWarningForeground1'],
  ['--color-state-danger-bg', '--colorStatusDangerBackground1'],
  ['--color-state-danger-fg', '--colorStatusDangerForeground1'],

  // type-* 排版别名
  ['--type-body1-strong-weight', '--fontWeightSemibold'],
  ['--type-caption1-strong-weight', '--fontWeightSemibold'],
  ['--type-body1-size', '--fontSizeBase300'],
  ['--type-body1-line', '--lineHeightBase300'],
  ['--type-body2-size', '--fontSizeBase400'],
  ['--type-body2-line', '--lineHeightBase400'],
  ['--type-caption1-size', '--fontSizeBase200'],
  ['--type-caption1-line', '--lineHeightBase200'],
  ['--type-caption2-size', '--fontSizeBase100'],
  ['--type-caption2-line', '--lineHeightBase100'],
  ['--type-subtitle2-size', '--fontSizeBase400'],
  ['--type-subtitle2-line', '--lineHeightBase400'],
  ['--type-subtitle1-size', '--fontSizeBase500'],
  ['--type-subtitle1-line', '--lineHeightBase500'],
  ['--type-title3-size', '--fontSizeBase600'],
  ['--type-title3-line', '--lineHeightBase600'],
  ['--type-title2-size', '--fontSizeHero700'],
  ['--type-title2-line', '--lineHeightHero700'],
  ['--type-title1-size', '--fontSizeHero800'],
  ['--type-title1-line', '--lineHeightHero800'],
  ['--type-largetitle-size', '--fontSizeHero900'],
  ['--type-largetitle-line', '--lineHeightHero900'],

  // 间距别名（注意 Fluent 4px=XS / 8px=S / 12px=M / 16px=L / 20px=XL / 24px=XXL / 32px=XXXL）
  ['--space-xs', '--spacingHorizontalXS'],
  ['--space-sm', '--spacingHorizontalS'],
  ['--space-md', '--spacingHorizontalL'],
  ['--space-lg', '--spacingHorizontalXXL'],
  ['--space-xl', '--spacingHorizontalXXXL'],
  ['--space-xxl', '--f-spacing-xxxxl'], // 48 px：fluent 无别名，下面会兜底定义

  // 圆角短别名
  ['--radius-small', '--borderRadiusSmall'],
  ['--radius-medium', '--borderRadiusMedium'],
  ['--radius-large', '--borderRadiusLarge'],
  ['--radius-xlarge', '--borderRadiusXLarge'],
  ['--radius-circular', '--borderRadiusCircular'],

  // 阴影短别名
  ['--shadow-level1', '--shadow2'],
  ['--shadow-level2', '--shadow4'],
  ['--shadow-level3', '--shadow8'],
  ['--shadow-overlay', '--shadow28'],
  ['--shadow-raised', '--shadow4'],

  // 字重短别名
  ['--font-weight-regular', '--fontWeightRegular'],
  ['--font-weight-medium', '--fontWeightMedium'],
  ['--font-weight-semibold', '--fontWeightSemibold'],
  ['--font-weight-bold', '--fontWeightBold'],
  ['--font-family-base', '--fontFamilyBase'],
  ['--font-family-mono', '--fontFamilyMonospace'],

  // z-index：原 token 没在 Fluent 中，保留为自定义 layer
  ['--z-toast', '--f-z-toast'],
  ['--z-overlay', '--f-z-overlay'],
  ['--z-dialog', '--f-z-dialog'],
  ['--z-drawer', '--f-z-drawer'],
];

/**
 * 是否需要迁移的文件。
 * @param {string} filePath
 * @return {boolean}
 */
function shouldProcess(filePath) {
  return TARGET_EXTS.has(extname(filePath));
}

/**
 * 递归收集需迁移的文件路径。
 * @param {string} root
 * @return {string[]}
 */
function* walk(root) {
  for (const entry of readdirSync(root, { withFileTypes: true })) {
    if (entry.name.startsWith('.') || entry.name === 'node_modules' || entry.name === 'dist') continue;
    const full = join(root, entry.name);
    if (entry.isDirectory()) yield* walk(full);
    else if (shouldProcess(full)) yield full;
  }
}

/**
 * 对一段文本逐条应用映射。
 * @param {string} text
 * @return {{ next: string, hits: number }}
 */
function migrateText(text) {
  let next = text;
  let hits = 0;
  for (const [from, to] of MAPPINGS) {
    if (!next.includes(from)) continue;
    const re = new RegExp(from.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g');
    next = next.replace(re, () => { hits += 1; return to; });
  }
  return { next, hits };
}

const fileList = explicitTargets.length
  ? explicitTargets.map((f) => resolve(projectRoot, f))
  : [...walk(resolve(projectRoot, 'src'))];

let totalHits = 0;
let touched = 0;
for (const file of fileList) {
  if (!statSync(file).isFile()) continue;
  const text = readFileSync(file, 'utf8');
  const { next, hits } = migrateText(text);
  if (hits === 0) continue;
  totalHits += hits;
  touched += 1;
  const rel = relative(projectRoot, file);
  if (dryRun) {
    console.log(`[dry] ${rel}: ${hits} replacements`);
  } else {
    // 保持 CRLF
    const out = next.includes('\r\n') ? next : next.replace(/\n/g, '\r\n');
    writeFileSync(file, out, { encoding: 'utf8' });
    console.log(`[ok]  ${rel}: ${hits} replacements`);
  }
}

console.log(`\nDone. ${touched} files touched, ${totalHits} replacements total${dryRun ? ' (dry run)' : ''}.`);
