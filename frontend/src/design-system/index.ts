/*
 * 设计系统出口：仅暴露项目级薄包装与主题适配层。
 * 业务页面直接 import 'naive-ui' 使用 Naive UI 组件，不再从本模块取通用控件。
 */
export { default as FIcon } from './FIcon.vue';
export { default as FDialogHost } from './FDialogHost.vue';
export { default as FToastHost } from './FToastHost.vue';

export type { FluentIconName } from './icons';
export { ICON_MAP, resolveIcon, loadedIconCount } from './icons';

export { fluentLightOverrides, fluentDarkOverrides } from './theme/naive-overrides';
export { applyFluentTheme } from './theme/applyTheme';
