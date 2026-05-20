/*
 * 显示控制路由参数与窗口映射的统一定义。
 * 路由片段（big-left/big-right/tv-left/tv-right）与窗口 1/2/3/4 一一对应。
 */
import { t } from '@/locales';

export interface DisplayTargetMeta {
  windowId: number;
  param: string;
  /** 桌面侧边栏 / 移动 SegmentedControl 显示标题。 */
  title: string;
  /** 副标题：双屏时大屏左/右展开。 */
  subtitle?: string;
  /** 仅双屏可访问。 */
  doubleScreenOnly?: boolean;
}

export const DISPLAY_TARGETS: DisplayTargetMeta[] = [
  { windowId: 1, param: 'big-left', title: t('display.bigTitle'), subtitle: t('display.bigSubtitle') },
  { windowId: 2, param: 'big-right', title: t('display.bigRightTitle'), subtitle: t('display.bigRightSubtitle'), doubleScreenOnly: true },
  { windowId: 3, param: 'tv-left', title: t('display.tvLeftTitle') },
  { windowId: 4, param: 'tv-right', title: t('display.tvRightTitle') },
];

/**
 * 通过路由 param 查找窗口 id 与元信息。
 * @param param 路由 :target 片段
 * @return DisplayTargetMeta 或 undefined
 */
export function resolveDisplayTarget(param: string): DisplayTargetMeta | undefined {
  return DISPLAY_TARGETS.find((target) => target.param === param);
}

/**
 * 通过窗口 id 反查路由 param。
 * 未匹配时回退到大屏左（windowId=1），保证导航链路始终可用。
 * @param windowId 窗口 id（1–4）
 * @return 对应的路由 :target 片段
 */
export function windowIdToSlug(windowId: number): string {
  return DISPLAY_TARGETS.find((target) => target.windowId === windowId)?.param ?? 'big-left';
}
