/*
 * vue-i18n 实例（DESIGN.md O8）。
 *  - Composition 模式（legacy: false），组件内用 useI18n() 取 t；
 *  - 单语种 zh-CN，作为默认与回退；
 *  - 导出 `t` 供非组件模块（router / navItems / store 等）直接调用。
 */
import { createI18n } from 'vue-i18n';

import zhCN from './zh-CN';

export const i18n = createI18n({
  legacy: false,
  locale: 'zh-CN',
  fallbackLocale: 'zh-CN',
  messages: { 'zh-CN': zhCN },
});

/** 非组件模块用的翻译函数（与组件内 useI18n().t 等价）。 */
export const t = i18n.global.t;
