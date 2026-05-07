/*
 * 布局层共享类型：导航条目定义。
 */
import type { FluentIconName } from '@/design-system';

export interface NavItemDef {
  /** 路由路径，必须以 / 开头。 */
  path: string;
  /** 中文标题，TitleBar / NavPane / TabBar 共用。 */
  label: string;
  /** Fluent 图标名称。 */
  icon: FluentIconName | string;
  /** 选中时的图标（默认与 icon 相同）。 */
  iconSelected?: FluentIconName | string;
  /** 是否仅在双屏模式下展示。 */
  doubleScreenOnly?: boolean;
}
