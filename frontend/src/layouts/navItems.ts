/*
 * 应用 Shell 导航条目集合：与设计稿 §3.2 严格对齐。
 *  - 仪表盘 / 大屏控制 / 电视左 / 电视右 / 媒体源 / 预案 / 设置
 *  - 单屏模式仅显示「大屏」一项；双屏模式自动展开为大屏左 / 大屏右
 *  - 移动端底部 TabBar 5 项：首页 / 显控 / 媒体源 / 预案 / 更多
 */
import { t } from '@/locales';

import type { NavItemDef } from './types';

/** 桌面 NavPane 全量条目（按运行态再过滤）。 */
export const DESKTOP_PRIMARY_NAV: NavItemDef[] = [
  { path: '/dashboard', label: t('nav.dashboard'), icon: 'home_24_regular', iconSelected: 'home_24_filled' },
  { path: '/display/big-left', label: t('nav.bigScreen'), icon: 'tv_24_regular', iconSelected: 'tv_24_filled' },
  { path: '/display/big-right', label: t('nav.bigScreenRight'), icon: 'tv_24_regular', iconSelected: 'tv_24_filled', doubleScreenOnly: true },
  { path: '/display/tv-left', label: t('nav.tvLeft'), icon: 'desktop_mac_24_regular' },
  { path: '/display/tv-right', label: t('nav.tvRight'), icon: 'desktop_mac_24_regular' },
  { path: '/sources', label: t('nav.sources'), icon: 'library_24_regular', iconSelected: 'library_24_filled' },
  { path: '/scenarios', label: t('nav.scenarios'), icon: 'layer_24_regular', iconSelected: 'layer_24_filled' },
];

/** 桌面次级（设置）入口；视觉上独立分组。 */
export const DESKTOP_SECONDARY_NAV: NavItemDef[] = [
  { path: '/settings', label: t('nav.settings'), icon: 'settings_24_regular', iconSelected: 'settings_24_filled' },
];

/** 移动端底部 TabBar 5 项；「显控」默认指向 big-left，由页面内 SegmentedControl 切窗口。 */
export const MOBILE_TAB_BAR: NavItemDef[] = [
  { path: '/dashboard', label: t('nav.home'), icon: 'home_24_regular', iconSelected: 'home_24_filled' },
  { path: '/display/big-left', label: t('nav.display'), icon: 'tv_24_regular', iconSelected: 'tv_24_filled' },
  { path: '/sources', label: t('nav.sources'), icon: 'library_24_regular', iconSelected: 'library_24_filled' },
  { path: '/scenarios', label: t('nav.scenarios'), icon: 'layer_24_regular', iconSelected: 'layer_24_filled' },
  { path: '/more', label: t('nav.more'), icon: 'more_horizontal_24_regular' },
];

/**
 * 名称化大屏路径标题：根据当前大屏模式显示「大屏 / 大屏左」。
 * @param path 路径
 * @param isDoubleScreen 是否双屏
 * @return 当前应显示的中文标题
 */
export function resolveDisplayLabel(path: string, isDoubleScreen: boolean): string {
  if (path === '/display/big-left') return isDoubleScreen ? t('nav.bigScreenLeft') : t('nav.bigScreen');
  if (path === '/display/big-right') return t('nav.bigScreenRight');
  if (path === '/display/tv-left') return t('nav.tvLeft');
  if (path === '/display/tv-right') return t('nav.tvRight');
  return '';
}
