/*

 * 简体中文文案聚合入口（DESIGN.md O8：所有用户可见文案集中于 locales/）。

 * 领域文案拆分到 zh-CN/ 下，避免单文件继续膨胀。

 */

import core from './zh-CN/core';

import display from './zh-CN/display';

import dashboard from './zh-CN/dashboard';

import scenarios from './zh-CN/scenarios';

import sources from './zh-CN/sources';

import settings from './zh-CN/settings';

import designSystem from './zh-CN/design-system';



export default {

  ...core,

  ...display,

  ...dashboard,

  ...scenarios,

  ...sources,

  ...settings,

  ...designSystem,

} as const;
