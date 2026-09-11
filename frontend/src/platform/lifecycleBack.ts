const DISMISSIBLE_LAYER_SELECTOR = '[role="dialog"], .n-drawer--show, .n-modal';
const CLOSE_CONTROL_SELECTOR = 'button[aria-label="close"]';

export type DismissibleLayerRoot = Pick<ParentNode, 'querySelectorAll'>;

/**
 * 关闭最上层可关闭交互。原生返回键不能依赖合成 Escape 事件，因为组件库只会
 * 接受浏览器生成的受信任键盘事件；显式调用关闭控件才能复用页面自身的关闭逻辑。
 */
export function dismissTopLayer(root: DismissibleLayerRoot = document): boolean {
  const layers = Array.from(root.querySelectorAll<HTMLElement>(DISMISSIBLE_LAYER_SELECTOR));
  const layer = layers.at(-1);
  if (!layer) return false;

  layer.querySelector<HTMLElement>(CLOSE_CONTROL_SELECTOR)?.click();
  return true;
}
