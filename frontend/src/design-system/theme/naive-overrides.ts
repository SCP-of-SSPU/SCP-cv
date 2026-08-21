/*
 * Fluent 2 → Naive UI 主题适配层（DESIGN.md §4.3 / §5）。
 *
 * Naive UI 的主题系统是 JS 对象（GlobalThemeOverrides），与 Fluent 2 通过 CSS
 * 自定义属性 (`var(--colorBrandBackground)` 等) 暴露 token 的方式存在阻抗。
 * 本文件是两者唯一的桥梁：从 `@fluentui/tokens` 的官方 Theme 对象派生出
 * Naive 的 overrides 对象，保证两套样式体系颜色、字号、圆角、阴影同源。
 *
 * 约束：
 *   - 不在此处手抄色值；颜色 / 字号 / 圆角全部从 webLightTheme / webDarkTheme 读取。
 *   - 仅在 Fluent token 与 NUI 概念无法 1:1 对齐时（如 NUI 的 hoverColor
 *     vs Fluent 的多层 hover 状态）做最小化的语义映射。
 *   - 不修改 NUI 的尺寸默认值；尺寸（heightMedium=34 等）保持 NUI 默认以避免
 *     全站布局回归，Fluent 的 32/24/40 三段在 Button overrides 中再细化。
 */
import type { GlobalThemeOverrides } from 'naive-ui';
import type { Theme } from '@fluentui/tokens';
import { webDarkTheme, webLightTheme } from '@fluentui/tokens';

/** Qingyuan 品牌色：青雾点睛，浅色主题 */
const QINGYUAN_BRAND_LIGHT = {
  primary: '#478384',
  primaryHover: '#5c9a9b',
  primaryPressed: '#356263',
};

/** Qingyuan 品牌色：青雾点睛，暗色主题 */
const QINGYUAN_BRAND_DARK = {
  primary: '#5c9a9b',
  primaryHover: '#7fb0b1',
  primaryPressed: '#478384',
};

/**
 * 从 Fluent Theme 派生 Naive GlobalThemeOverrides，并叠加 Qingyuan 品牌色。
 * @param t Fluent 主题对象（webLightTheme / webDarkTheme / 自定义品牌主题）
 * @param brand Qingyuan 品牌色覆盖
 * @return Naive UI 全局主题覆盖配置
 */
function buildOverrides(t: Theme, brand: { primary: string; primaryHover: string; primaryPressed: string }): GlobalThemeOverrides {
  return {
    common: {
      // 品牌色：Qingyuan 青雾点睛
      primaryColor: brand.primary,
      primaryColorHover: brand.primaryHover,
      primaryColorPressed: brand.primaryPressed,
      primaryColorSuppl: brand.primaryHover,

      // 状态色：信息色沿用品牌青；其余保持 Fluent 语义色
      infoColor: brand.primary,
      infoColorHover: brand.primaryHover,
      infoColorPressed: brand.primaryPressed,
      successColor: t.colorStatusSuccessForeground1,
      successColorHover: t.colorStatusSuccessForeground1,
      successColorPressed: t.colorStatusSuccessForeground1,
      warningColor: t.colorStatusWarningForeground1,
      warningColorHover: t.colorStatusWarningForeground1,
      warningColorPressed: t.colorStatusWarningForeground1,
      errorColor: t.colorStatusDangerForeground1,
      errorColorHover: t.colorStatusDangerForeground1,
      errorColorPressed: t.colorStatusDangerForeground1,

      // 中性背景：页面 / 卡片 / 弹窗
      bodyColor: t.colorNeutralBackground1,
      cardColor: t.colorNeutralBackground1,
      modalColor: t.colorNeutralBackground1,
      popoverColor: t.colorNeutralBackground1,
      tableColor: t.colorNeutralBackground1,
      inputColor: t.colorNeutralBackground1,
      tagColor: t.colorNeutralBackground3,
      actionColor: t.colorNeutralBackground2,
      tableHeaderColor: t.colorNeutralBackground2,
      hoverColor: t.colorNeutralBackground1Hover ?? t.colorNeutralBackground2,
      pressedColor: t.colorNeutralBackground1Pressed ?? t.colorNeutralBackground3,
      clearColor: t.colorTransparentBackground,

      // 中性前景：文本三档 + 禁用
      baseColor: t.colorNeutralBackground1,
      textColorBase: t.colorNeutralForeground1,
      textColor1: t.colorNeutralForeground1,
      textColor2: t.colorNeutralForeground2,
      textColor3: t.colorNeutralForeground3,
      textColorDisabled: t.colorNeutralForegroundDisabled,
      placeholderColor: t.colorNeutralForeground3,
      placeholderColorDisabled: t.colorNeutralForegroundDisabled,
      iconColor: t.colorNeutralForeground2,
      iconColorHover: t.colorNeutralForeground1,
      iconColorPressed: t.colorNeutralForeground1,
      iconColorDisabled: t.colorNeutralForegroundDisabled,

      // 描边 / 分割线
      borderColor: t.colorNeutralStroke1,
      dividerColor: t.colorNeutralStroke2,
      closeIconColor: t.colorNeutralForeground2,
      closeIconColorHover: t.colorNeutralForeground1,
      closeIconColorPressed: t.colorNeutralForeground1,
      closeColorHover: t.colorNeutralBackground2,
      closeColorPressed: t.colorNeutralBackground3,

      // 圆角：NUI 只有一个全局 borderRadius，取 Fluent 的 Medium=4px
      borderRadius: t.borderRadiusMedium,
      borderRadiusSmall: t.borderRadiusSmall,

      // 字体：Fluent Segoe UI 栈
      fontFamily: t.fontFamilyBase,
      fontFamilyMono: t.fontFamilyMonospace,
      fontWeight: String(t.fontWeightRegular),
      fontWeightStrong: String(t.fontWeightSemibold),
      fontSize: t.fontSizeBase300,
      fontSizeMini: t.fontSizeBase100,
      fontSizeTiny: t.fontSizeBase200,
      fontSizeSmall: t.fontSizeBase200,
      fontSizeMedium: t.fontSizeBase300,
      fontSizeLarge: t.fontSizeBase400,
      fontSizeHuge: t.fontSizeBase500,
      lineHeight: '1.5',

      // 阴影：Fluent 6 段映射到 NUI 弹层场景
      boxShadow1: t.shadow2,
      boxShadow2: t.shadow8,
      boxShadow3: t.shadow16,
    },
    Card: {
      borderRadius: t.borderRadiusLarge,
      paddingMedium: t.spacingHorizontalL,
      paddingLarge: t.spacingHorizontalXL,
      titleFontSizeMedium: t.fontSizeBase400,
      colorEmbedded: t.colorNeutralBackground2,
    },
    Button: {
      borderRadiusTiny: t.borderRadiusSmall,
      borderRadiusSmall: t.borderRadiusMedium,
      borderRadiusMedium: t.borderRadiusMedium,
      borderRadiusLarge: t.borderRadiusMedium,
      fontWeight: String(t.fontWeightSemibold),
      heightSmall: '24px',
      heightMedium: '32px',
      heightLarge: '40px',
      paddingSmall: `0 ${t.spacingHorizontalS}`,
      paddingMedium: `0 ${t.spacingHorizontalM}`,
      paddingLarge: `0 ${t.spacingHorizontalL}`,
    },
    Tag: {
      borderRadius: t.borderRadiusSmall,
      fontWeightStrong: String(t.fontWeightSemibold),
    },
    Input: {
      borderRadius: t.borderRadiusMedium,
      heightMedium: '32px',
      heightLarge: '40px',
      heightSmall: '24px',
    },
    Dialog: {
      borderRadius: t.borderRadiusXLarge,
      padding: t.spacingHorizontalXL,
    },
    Modal: {
      color: t.colorNeutralBackground1,
    },
    Drawer: {
      color: t.colorNeutralBackground1,
      headerPadding: t.spacingHorizontalL,
      bodyPadding: t.spacingHorizontalL,
      footerPadding: t.spacingHorizontalL,
    },
    Menu: {
      borderRadius: t.borderRadiusMedium,
      itemHeight: '36px',
      itemColorActive: t.colorBrandBackground2,
      itemTextColorActive: t.colorBrandForeground1,
      itemTextColorActiveHover: t.colorBrandForeground1,
      itemIconColorActive: t.colorBrandForeground1,
    },
    Tabs: {
      tabFontWeightActive: String(t.fontWeightSemibold),
      tabTextColorActiveLine: brand.primary,
      barColor: brand.primary,
    },
    Alert: {
      borderRadius: t.borderRadiusMedium,
      padding: t.spacingHorizontalM,
    },
    Message: {
      borderRadius: t.borderRadiusMedium,
    },
    Notification: {
      borderRadius: t.borderRadiusLarge,
    },
    Switch: {
      railColor: t.colorNeutralStroke1,
      railColorActive: brand.primary,
    },
    Checkbox: {
      borderRadius: t.borderRadiusSmall,
      colorChecked: brand.primary,
    },
    Radio: {
      buttonColorActive: brand.primary,
      buttonTextColorActive: t.colorNeutralBackground1,
    },
    Slider: {
      fillColor: brand.primary,
      fillColorHover: brand.primaryHover,
      handleColor: brand.primary,
    },
    Tooltip: {
      borderRadius: t.borderRadiusMedium,
      color: t.colorNeutralForeground1,
      textColor: t.colorNeutralBackground1,
    },
    Progress: {
      fillColor: brand.primary,
      railColor: t.colorNeutralStroke2,
    },
    Empty: {
      iconColor: t.colorNeutralForeground3,
      textColor: t.colorNeutralForeground2,
    },
    Divider: {
      color: t.colorNeutralStroke2,
    },
    Skeleton: {
      color: t.colorNeutralBackground3,
      colorEnd: t.colorNeutralBackground2,
    },
    Form: {
      labelTextColor: t.colorNeutralForeground1,
      labelFontWeight: String(t.fontWeightSemibold),
    },
  };
}

/** Light 主题下的 Naive UI 覆盖（叠加 Qingyuan 青色品牌色）。 */
export const fluentLightOverrides: GlobalThemeOverrides = buildOverrides(webLightTheme, QINGYUAN_BRAND_LIGHT);

/** Dark 主题下的 Naive UI 覆盖（叠加 Qingyuan 青色品牌色）。 */
export const fluentDarkOverrides: GlobalThemeOverrides = buildOverrides(webDarkTheme, QINGYUAN_BRAND_DARK);
