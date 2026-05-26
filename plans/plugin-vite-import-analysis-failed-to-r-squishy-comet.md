# Fluent 2 迁移：清除 Material 残留 + 引入 Naive UI + @vicons/fluent

## Context

`refactor/frontend-fluent2` 分支与远端 `main` 合并后，`npm run dev` 立刻在 `frontend/src/main.ts:15` 报：

```
[plugin:vite:import-analysis] Failed to resolve import "material-symbols/rounded.css"
```

但根因不是依赖缺失（`frontend/node_modules/material-symbols/rounded.css` 实际存在），而是项目残留了 **Material Symbols 字体图标方案**——这违反 `DESIGN.md` 唯一指定的 Fluent 2 设计系统，且 `DESIGN.md §9 "与生态包的关系"` 根本没把 `material-symbols` 列为合规依赖。

借此机会按用户指示一次性完成 Fluent 2 收口：

1. 彻底清除 `material-symbols` 字体方案与所有 "M3 / Material" 痕迹（依赖、import、CSS 类名、文档注释、虚构章节引用）。
2. 引入 **Naive UI** 作为统一组件库，砍掉 `design-system/F*` 28 个自研薄壳。
3. 图标统一走 **@vicons/fluent**（社区封装的 Fluent UI System Icons Vue 组件），与 Naive UI 的 `<NIcon>` 配合。
4. 在 Naive UI 与 `@fluentui/tokens` 之间架一层 `themeOverrides` 适配层，让 Naive 组件的颜色/字号/圆角与 Fluent 2 token 同源。

迁移完成后：`frontend/src/design-system/` 由"自研组件目录"变成"主题适配层目录"；业务页面统一用 `<n-button>`、`<n-card>`、`<n-icon>` 等 Naive 组件；Fluent 2 token 仍是颜色/排版/间距的真源。

---

## 目标与决策摘要

| 决策点                           | 选择                                                                 |
| -------------------------------- | -------------------------------------------------------------------- |
| Material Symbols 字体方案        | 删除（依赖 + import + CSS 类 + 注释）                                |
| 图标库                           | `@vicons/fluent`（Vue 组件形态，封装 `@fluentui/svg-icons`）         |
| 组件库                           | `naive-ui` 2.44+                                                     |
| 自研 F* 组件                     | 全部砍掉，业务页面直接用 `N*`                                        |
| Fluent → Naive 主题对接          | 构建 `themeOverrides` 适配层，源头仍是 `@fluentui/tokens`            |
| `tokens.css`                     | 保留——作为非主题维度（间距/圆角/字号/动效）的 CSS 变量来源；与 Naive `themeOverrides` 同源对齐 |
| `frontend/scripts/migrate-m3-tokens.mjs` | 删除（一次性脚本已完成使命，无 npm script 引用）                |
| 虚构 DESIGN.md 章节引用          | 全部映射到真实章节（§9 IC1→§9+§7、§12.x→§2+§4、§14.4→§6.4 等）       |
| 本次 PR 范围                     | 完整迁移：清 material + 装 NUI + 替组件 + 修注释，**一气呵成**       |

---

## 依赖变更（frontend/package.json）

**删除**：
- `material-symbols`（dependency）

**新增**：
- `naive-ui@^2.44.1`（dependency）
- `@vicons/fluent@^0.13.0`（dependency）

`@fluentui/tokens` 保留（仍为 token 真源）。`package-lock.json` 由 `npm install` 重新生成。

```powershell
npm --prefix frontend uninstall material-symbols
npm --prefix frontend install naive-ui @vicons/fluent
```

---

## 关键改造

### 1. 主题适配层（新增）

新建 `frontend/src/design-system/theme/naive-overrides.ts`：

- 输入：`webLightTheme` / `webDarkTheme`（`@fluentui/tokens`）。
- 输出：两个 Naive `GlobalThemeOverrides` 对象（`fluentLightOverrides` / `fluentDarkOverrides`）。
- 映射要点（不穷举，按 NUI overrides shape 组装）：
  - `common.primaryColor` ← `colorBrandBackground`
  - `common.primaryColorHover` ← `colorBrandBackgroundHover`
  - `common.primaryColorPressed` ← `colorBrandBackgroundPressed`
  - `common.textColorBase` ← `colorNeutralForeground1`；`textColor2/3` ← `colorNeutralForeground2/3`
  - `common.bodyColor` ← `colorNeutralBackground1`；`cardColor` ← `colorNeutralBackground1`；`modalColor` ← `colorNeutralBackground1`
  - `common.borderColor` ← `colorNeutralStroke1`；`dividerColor` ← `colorNeutralStrokeDivider`
  - `common.errorColor / warningColor / successColor` ← `colorStatusDangerForeground1 / WarningForeground1 / SuccessForeground1`
  - `common.borderRadius` ← `--borderRadiusMedium`（4px）；`heightMedium` ← 32px；`heightSmall` ← 24px；`heightLarge` ← 40px
  - 字体族：`fontFamily` ← `fontFamilyBase`；`fontSize` 系列 ← `fontSizeBase200/300/400/500`
  - 阴影：`Card.boxShadow / Modal.boxShadow / Popover.boxShadow` ← `shadow4 / shadow28 / shadow16`

> NUI 的 `themeOverrides` 是 JS 对象、不是 CSS 变量；这是它与 Fluent 2 的接口阻抗。该适配层是唯一桥梁。

### 2. 应用顶层注入

修改 `frontend/src/App.vue`：

- 在最外层包一层 `<n-config-provider :theme :theme-overrides :locale="zhCN" :date-locale="dateZhCN">`，包住 `<RouterView>` 与现有的 `FDialogHost` / `FToastHost` 替代者（见 §3）。
- `:theme` 由 `useTheme()` 派生：`resolved === 'dark' ? darkTheme : null`。
- `:theme-overrides` 由 `useTheme()` 派生：暗/亮分别取自适配层导出的对象。
- 再加 `<n-message-provider>` / `<n-dialog-provider>` / `<n-notification-provider>` / `<n-loading-bar-provider>`，注册 Naive 的全局宿主（替换原 `FDialogHost` / `FToastHost`）。

修改 `frontend/src/main.ts`：

- **删除**：`import 'material-symbols/rounded.css';` 与上一行的注释。
- 不需要为 Naive UI 额外 import；2.x 起 NUI 自带 CSS-in-JS，零样式 import。

### 3. FIcon 重写策略

`frontend/src/design-system/FIcon.vue` 与 `icons.ts` **整体重写**：

- `icons.ts` 改造为 token 名 → `@vicons/fluent` Vue 组件 的静态映射表（取代原 `SYMBOL_MAP`）。`FluentIconName` 联合类型从 `ICON_MAP` 的键派生（`keyof typeof ICON_MAP`），对外类型契约不变。
- 映射示例：
  ```ts
  import { Home24Regular, Play24Filled, Settings24Regular, /* ... */ } from '@vicons/fluent';
  export const ICON_MAP = {
    home_24_regular: Home24Regular,
    play_24_filled: Play24Filled,
    settings_24_regular: Settings24Regular,
    /* 沿用现有 ~70 个名 token，PascalCase 化即可 */
  } as const;
  ```
- `FIcon.vue` 模板改为：
  ```vue
  <n-icon :size="size" :color="color">
    <component :is="ICON_MAP[name] ?? FallbackIcon" />
  </n-icon>
  ```
- 删除 `material-symbols-rounded` 类、`font-variation-settings`、字体连字渲染等所有字体方案残留。
- `decorative` / `ariaLabel` 行为通过 `<n-icon>` 的 `aria-*` 直接转发保持。

### 4. F* → N* 映射与业务页面改写

| 自研 F*               | NUI 对应                                       | props 翻译要点                                                                 |
| --------------------- | ----------------------------------------------- | ------------------------------------------------------------------------------ |
| `FButton`             | `n-button`                                      | `appearance="primary"`→`type="primary"`；`secondary`→默认；`outline`→`secondary` + `ghost`；`subtle`→`tertiary`；`transparent`→`quaternary`；`danger`→`type="error"`；`ghost`→`quaternary`；`compact`→`size="small"` |
| `FCard`               | `n-card`                                        | `--shadow4` 默认；hover 升 `--shadow8` 通过 `:hoverable`                       |
| `FIcon`               | `n-icon` + `<component :is>`                    | 见 §3                                                                          |
| `FInput`              | `n-input`                                       | 直接对应                                                                       |
| `FTextarea`           | `n-input type="textarea"`                       | -                                                                              |
| `FField`              | `n-form-item`                                   | label/required/help/error 全有对应                                             |
| `FSwitch`             | `n-switch`                                      | -                                                                              |
| `FSlider`             | `n-slider`                                      | -                                                                              |
| `FSegmented`          | `n-tabs type="segment"` 或 `n-radio-group` + `n-radio-button` | 看用法；多数为单选场景→ radio-group                     |
| `FTag`                | `n-tag`                                         | tone→`type`                                                                    |
| `FSpinner`            | `n-spin`                                        | -                                                                              |
| `FSkeleton`           | `n-skeleton`                                    | -                                                                              |
| `FProgress`           | `n-progress`                                    | -                                                                              |
| `FDialog`             | `n-modal` 或 `useDialog().create`               | 顶层声明用 `n-modal`，命令式用 provider                                        |
| `FDialogHost`         | `n-dialog-provider`（顶层注入）                 | 删除自研宿主，组件内用 `useDialog()`                                           |
| `FDrawer`             | `n-drawer` + `n-drawer-content`                 | -                                                                              |
| `FMessageBar`         | `n-alert`                                       | tone→`type`                                                                    |
| `FToastHost`          | `n-message-provider`（顶层注入）                | 删除自研宿主，组件内用 `useMessage()`                                          |
| `FEmpty`              | `n-empty`                                       | -                                                                              |
| `FTabs`               | `n-tabs`                                        | -                                                                              |
| `FCombobox`           | `n-select :filterable`                          | -                                                                              |
| `FMenu`               | `n-dropdown` 或 `n-menu`                        | 看场景：上下文菜单→`n-dropdown`；侧栏导航→`n-menu`                              |
| `FTooltip`            | `n-tooltip`                                     | -                                                                              |
| `FDivider`            | `n-divider`                                     | -                                                                              |
| `FCheckbox`           | `n-checkbox`                                    | -                                                                              |
| `FRadio` / `FRadioGroup` | `n-radio` / `n-radio-group`                  | -                                                                              |

业务页面改写：

- 26 个文件、35 处 `from '@/design-system'` 全部改为 `from 'naive-ui'`（或干脆删除——如 `useDialog/useMessage` 走 composable）。
- 64 处 `appearance="…"` 按上表批量翻译。
- 模板内 `<FXxx>` 全部改为 `<n-xxx>` 标签名。
- 代表性受影响文件（按已知调用面）：
  - `layouts/`: AppShell.vue, AppNavigation.vue, AppTopBar.vue, EmergencyMenu.vue, MoreSheet.vue, ThemeToggle.vue
  - `features/dashboard/DashboardView.vue`
  - `features/display/`: DisplayControlView.vue, PlaybackControl.vue, SourcePicker.vue
  - `features/sources/`: SourcesView.vue, AddSourceDrawer.vue, EditSourceDrawer.vue, SourceThumbnail.vue
  - `features/scenarios/`: ScenariosView.vue, ScenarioEditDrawer.vue, ScenarioPreviewDrawer.vue
  - `features/settings/`: SettingsView.vue 与 tabs/ 下 4 个 tab
  - `features/pptFocus/`: PptFocusView.vue, PptSlideRail.vue

### 5. 删除清单

| 路径                                            | 原因                                                                 |
| ----------------------------------------------- | -------------------------------------------------------------------- |
| `frontend/src/design-system/F*.vue` × 28        | 自研组件由 NUI 完整取代                                              |
| `frontend/src/design-system/utils.ts`           | 仅服务于自研组件；若有公用工具迁入 `design-system/theme/`           |
| `frontend/src/design-system/types.ts`           | F* 的 props 类型不再需要；保留必要的 `FluentIconName` 已迁入 icons.ts |
| `frontend/scripts/migrate-m3-tokens.mjs`        | 一次性 M3→Fluent 迁移已完成；tokens.css 已是生成产物                 |

`design-system/index.ts` **重写为**：只导出 `FIcon`、`FluentIconName` 类型、`fluentLightOverrides` / `fluentDarkOverrides`，以及（如保留）兼容的小型工具。

### 6. 注释与虚构章节清理（全文替换）

按下表批量替换（涉及 `AppShell.vue`、`AppShell.css`、`App.vue`、`useWindowSizeClass.ts`、`FButton.vue`、`FIcon.vue`、`icons.ts` 等剩余文件，以及任何 grep 命中处）：

| 现有措辞                                  | 改为                                                                   |
| ----------------------------------------- | ---------------------------------------------------------------------- |
| `M3 自适应`                               | `Fluent 2 自适应`                                                      |
| `M3 navigation rail`                      | `Fluent 2 导航轨道`                                                    |
| `M3 用 secondary-container 药丸承托`      | `Fluent 2 选中态：品牌色描边 + 中性背景`                               |
| `替代 M3 的药丸`                          | `Fluent 2 borderRadiusMedium 4px`                                      |
| `Material Symbols 字体连字`               | `Fluent UI System Icons (SVG via @vicons/fluent)`                      |
| `material-symbols-rounded` 类名引用       | 全部删除                                                               |
| `DESIGN.md §9 IC1` / `§14.4`              | `DESIGN.md §9 与生态包的关系` / `DESIGN.md §6.4 通用组件清单`          |
| `DESIGN.md §12.1` / `§12.3`               | `DESIGN.md §2 设计原则（Scale 适配）` / `DESIGN.md §4 Vue 3 架构实现` |
| 注释中 `M3 窗口尺寸类`                    | `Fluent 2 自适应窗口尺寸类（基于 §2 Scale 原则）`                      |

> `tools/third_party/mediamtx/mediamtx.yml` 中的 `stream.m3u8` 是 HLS 协议扩展名，**不动**。

---

## 验证步骤（必须跑过）

```powershell
# 1. 依赖装好、锁文件刷新
npm --prefix frontend install

# 2. 类型检查必须 0 报错（最关键，能扫出所有 props 翻译漏网）
npm --prefix frontend run typecheck

# 3. dev server 不再报 material-symbols；浏览器打开 http://localhost:5173 跑一遍：
uv run python manage.py runall --skip-mediamtx --skip-player
#   - Dashboard：按钮/标签/图标显示正常，dark/light 切换颜色对得上 Fluent token
#   - Sources：FCombobox→n-select 的 filterable 行为还在
#   - Scenarios：FDrawer→n-drawer 的进出动效正常
#   - Settings：四个 tab 切换正常
#   - PPT Focus：FIcon 渲染为 SVG（不是字体连字）
#   - 弹窗/Toast：useDialog/useMessage 触发正常

# 4. 生产构建
npm --prefix frontend run build

# 5. 后端测试不应受影响，但保险跑一遍
uv run pytest tests/ -v
```

浏览器侧手动核对清单：
- 主题切换：Fluent 品牌色 `#0f6cbd` 在亮/暗主题下的 hover/pressed 都正确。
- 图标：DevTools 看 `<n-icon>` 内是 `<svg>` 而非 `<span class="material-symbols-rounded">`。
- network 面板：不应再请求 `material-symbols-rounded.woff2`。

---

## 风险与回归点

1. **NUI props 翻译漏译**：`appearance` 64 处批量改写时，`outline` 与 `subtle` 容易混；建议 typecheck 后再做一次 `grep -n 'appearance='` 自查。
2. **`useDialog` / `useMessage` 必须在 provider 子树内调用**：原 F* 是模块级单例，业务可能在 `<script setup>` 顶层直接调用；改造后必须在 setup 顶层 `const dialog = useDialog()` 然后再用。
3. **NUI 全局样式**：NUI 2.x 默认通过 `<n-config-provider>` 注入 CSS-in-JS，但仍建议显式 import `'naive-ui/es/styles/common-style.css'` 之类样式（若发现 reset 缺失再加）。
4. **暗色对比度**：Fluent dark 与 NUI dark 的 token 不完全对齐，适配层必须把 `webDarkTheme` 的 `colorNeutralBackground1 = #292929` 等显式覆盖到 NUI `common.bodyColor` 上，不能让 NUI 用自己的默认深色（容易翻车）。
5. **`tokens.css` 与 themeOverrides 双源真理**：必须保证两者从 `@fluentui/tokens` 同一份对象派生；建议把派生逻辑放在 `design-system/theme/` 下，generate-fluent-tokens.mjs 和 naive-overrides.ts 都消费它，避免漂移。
