/*
 * 应用 Shell 导航条目集合：与设计稿 §3.2 严格对齐。
 *  - 仪表盘 / 大屏控制 / 电视左 / 电视右 / 媒体源 / 预案 / 设置
 *  - 单屏模式仅显示「大屏」一项；双屏模式自动展开为大屏左 / 大屏右
 *  - 移动端底部 TabBar 5 项：首页 / 显控 / 媒体源 / 预案 / 更多
 */
import type { NavItemDef } from './types';

/** 桌面 NavPane 全量条目（按运行态再过滤）。 */
export const DESKTOP_PRIMARY_NAV: NavItemDef[] = [
  { path: '/dashboard', label: '仪表盘', icon: 'home_24_regular', iconSelected: 'home_24_filled' },
  { path: '/display/big-left', label: '大屏', icon: 'tv_24_regular', iconSelected: 'tv_24_filled' },
  { path: '/display/big-right', label: '大屏右', icon: 'tv_24_regular', iconSelected: 'tv_24_filled', doubleScreenOnly: true },
  { path: '/display/tv-left', label: '电视左', icon: 'desktop_mac_24_regular' },
  { path: '/display/tv-right', label: '电视右', icon: 'desktop_mac_24_regular' },
  { path: '/sources', label: '媒体源', icon: 'library_24_regular', iconSelected: 'library_24_filled' },
  { path: '/scenarios', label: '预案', icon: 'layer_24_regular', iconSelected: 'layer_24_filled' },
];

/** 桌面次级（设置）入口；视觉上独立分组。 */
export const DESKTOP_SECONDARY_NAV: NavItemDef[] = [
  { path: '/settings', label: '设置', icon: 'settings_24_regular', iconSelected: 'settings_24_filled' },
];

/** 移动端底部 TabBar 5 项；「显控」默认指向 big-left，由页面内 SegmentedControl 切窗口。 */
export const MOBILE_TAB_BAR: NavItemDef[] = [
  { path: '/dashboard', label: '首页', icon: 'home_24_regular', iconSelected: 'home_24_filled' },
  { path: '/display/big-left', label: '显控', icon: 'tv_24_regular', iconSelected: 'tv_24_filled' },
  { path: '/sources', label: '媒体源', icon: 'library_24_regular', iconSelected: 'library_24_filled' },
  { path: '/scenarios', label: '预案', icon: 'layer_24_regular', iconSelected: 'layer_24_filled' },
  { path: '/more', label: '更多', icon: 'more_horizontal_24_regular' },
];

/**
 * 名称化大屏路径标题：根据当前大屏模式显示「大屏 / 大屏左」。
 * @param path 路径
 * @param isDoubleScreen 是否双屏
 * @return 当前应显示的中文标题
 */
export function resolveDisplayLabel(path: string, isDoubleScreen: boolean): string {
  if (path === '/display/big-left') return isDoubleScreen ? '大屏左' : '大屏';
  if (path === '/display/big-right') return '大屏右';
  if (path === '/display/tv-left') return '电视左';
  if (path === '/display/tv-right') return '电视右';
  return '';
}
