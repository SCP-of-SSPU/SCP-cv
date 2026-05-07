/*
 * 显示控制路由参数与窗口映射的统一定义。
 * 路由片段（big-left/big-right/tv-left/tv-right）与窗口 1/2/3/4 一一对应。
 */
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
  { windowId: 1, param: 'big-left', title: '大屏', subtitle: '单屏模式下的大屏主输出' },
  { windowId: 2, param: 'big-right', title: '大屏右', subtitle: '仅在双屏模式下可控', doubleScreenOnly: true },
  { windowId: 3, param: 'tv-left', title: '电视左' },
  { windowId: 4, param: 'tv-right', title: '电视右' },
];

/**
 * 通过路由 param 查找窗口 id 与元信息。
 * @param param 路由 :target 片段
 * @return DisplayTargetMeta 或 undefined
 */
export function resolveDisplayTarget(param: string): DisplayTargetMeta | undefined {
  return DISPLAY_TARGETS.find((target) => target.param === param);
}
